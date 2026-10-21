from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, inspect, or_
from app import models as m
from app import schemas as s
from app.core.database import db_session
from app.core.security import current_user, optional_user, editor, administrator, roles
from app.api.auth import me
from app.services.gratuity import gratuity

router = APIRouter()
CONTENT = {
    "videos": m.Video,
    "publications": m.Publication,
    "articles": m.Article,
    "updates": m.RegulatoryUpdate,
    "webinars": m.Webinar,
}
ADMIN = {
    **CONTENT,
    "categories": m.SubjectCategory,
    "chapters": m.PublicationChapter,
    "notifications": m.Notification,
}


def serialize(row):
    result = {
        column.key: getattr(row, column.key) for column in inspect(type(row)).columns
    }
    if isinstance(row, (m.Company, m.CompanyPerson, m.CompanyDocument)):
        from app.professional.privacy import reveal

        for field in ["profile_data", "details"]:
            if field in result:
                result[field] = reveal(result[field])
        if isinstance(row, m.Company):
            result["trn"] = result["profile_data"].pop("_legacy_trn", result.get("trn"))
    return result


def paginate(db, model, conditions=(), page=1, page_size=20):
    query = select(model).where(*conditions)
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(model.created_at.desc(), model.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [serialize(x) for x in items],
        "total": count,
        "page": page,
        "page_size": page_size,
    }


def owned(db, company_id, user):
    company = db.scalar(
        select(m.Company).where(
            m.Company.id == company_id, m.Company.owner_id == user.id
        )
    )
    if not company:
        raise HTTPException(404, "Company not found")
    return company


def audit(db, user, action, resource):
    db.add(m.AuditLog(actor_id=user.id, action=action, resource_id=resource))


@router.get("/users/me")
def profile(user=Depends(current_user), db=Depends(db_session)):
    return me(user, db)


@router.patch("/users/me")
def edit_profile(
    data: s.CategoryInput, user=Depends(current_user), db=Depends(db_session)
):
    row = db.scalar(select(m.UserProfile).where(m.UserProfile.user_id == user.id))
    row.name = data.name
    return {"name": row.name}


@router.get("/users/me/preferences")
@router.get("/notifications/preferences")
def preferences(user=Depends(current_user), db=Depends(db_session)):
    row = db.scalar(
        select(m.NotificationPreference).where(
            m.NotificationPreference.user_id == user.id
        )
    )
    return {
        "categories": row.categories if row else [],
        "in_app": row.in_app if row else True,
    }


@router.put("/users/me/preferences")
@router.put("/notifications/preferences")
def save_preferences(
    data: s.Preferences, user=Depends(current_user), db=Depends(db_session)
):
    row = db.scalar(
        select(m.NotificationPreference).where(
            m.NotificationPreference.user_id == user.id
        )
    )
    if not row:
        row = m.NotificationPreference(user_id=user.id)
        db.add(row)
    row.categories, row.in_app = data.categories, data.in_app
    return data


@router.get("/categories", response_model=s.Page[s.CategoryResponse])
def categories(
    db=Depends(db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return paginate(db, m.SubjectCategory, page=page, page_size=page_size)


def public_content(record, kind):
    value = dict(record)
    allowed = {
        "subject",
        "thumbnail_url",
        "presenter",
        "timezone",
        "capacity",
        "registration_open",
        "duration_minutes",
        "related_topics",
        "related_resources",
        "asset_id",
        "kind",
        "display_order",
        "issuer",
        "publication_date",
        "effective_date",
        "verified_on",
        "technical_explanation",
        "affected_topics",
    }
    value["metadata_extra"] = {
        k: v for k, v in (value.get("metadata_extra") or {}).items() if k in allowed
    }
    if kind == "webinars":
        value["metadata_extra"]["join_configured"] = bool(value.get("join_url"))
        value["metadata_extra"]["recording_configured"] = bool(
            (record.get("metadata_extra") or {}).get("recording_url")
        )
        value["join_url"] = None
    return value


def add_content_routes(kind, model):
    def listing(
        q: str = Query("", max_length=120),
        category_id: str | None = None,
        video_category_id: str | None = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        user=Depends(optional_user),
        db=Depends(db_session),
    ):
        filters = [
            model.status == "published",
            or_(model.publish_at.is_(None), model.publish_at <= m.now()),
        ]
        if not user:
            filters.append(model.visibility == "public")
        if q:
            filters.append(
                model.title.ilike("%" + q.replace("%", "").replace("_", "") + "%")
            )
        if category_id:
            filters.append(model.category_id == category_id)
        if kind == "videos" and video_category_id:
            filters.append(model.video_category_id == video_category_id)
        result = paginate(db, model, filters, page, page_size)
        result["items"] = [public_content(record, kind) for record in result["items"]]
        if kind == "updates" and user:
            read = {
                r.update_id: r.read_at
                for r in db.scalars(
                    select(m.RegulatoryUpdateRead).where(
                        m.RegulatoryUpdateRead.user_id == user.id
                    )
                )
            }
            for row in result["items"]:
                row["read_at"] = read.get(row["id"])
        return result

    def detail(id: str, user=Depends(optional_user), db=Depends(db_session)):
        row = db.scalar(
            select(model).where(model.id == id, model.status == "published")
        )
        if not row:
            raise HTTPException(404, "Published resource not found")
        if (row.visibility == "authenticated" and not user) or (
            row.publish_at
            and row.publish_at.replace(tzinfo=__import__("datetime").timezone.utc)
            > m.now()
        ):
            raise HTTPException(404)
        return public_content(serialize(row), kind)

    router.add_api_route(
        "/" + kind,
        listing,
        methods=["GET"],
        response_model=s.Page[s.ContentResponse],
        name="list_" + kind,
    )
    router.add_api_route(
        "/" + kind + "/{id}",
        detail,
        methods=["GET"],
        response_model=s.ContentResponse,
        name="get_" + kind,
    )


for kind, model in CONTENT.items():
    add_content_routes(kind, model)


@router.patch("/updates/{id}/read")
def mark_update_read(id: str, user=Depends(current_user), db=Depends(db_session)):
    update = db.get(m.RegulatoryUpdate, id)
    if not update or update.status != "published":
        raise HTTPException(404)
    row = db.scalar(
        select(m.RegulatoryUpdateRead).where(
            m.RegulatoryUpdateRead.user_id == user.id,
            m.RegulatoryUpdateRead.update_id == id,
        )
    )
    if row is None:
        db.add(m.RegulatoryUpdateRead(user_id=user.id, update_id=id))
    return {"read": True}


@router.get("/publications/{id}/chapters", response_model=s.Page)
def chapters(
    id: str,
    user=Depends(optional_user),
    db=Depends(db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
):
    publication = db.get(m.Publication, id)
    if (
        not publication
        or publication.status != "published"
        or (publication.visibility == "authenticated" and not user)
        or (
            publication.publish_at
            and publication.publish_at.replace(
                tzinfo=__import__("datetime").timezone.utc
            )
            > m.now()
        )
    ):
        raise HTTPException(404)
    result = paginate(
        db,
        m.PublicationChapter,
        [m.PublicationChapter.publication_id == id],
        page,
        page_size,
    )
    result["items"].sort(key=lambda x: x["position"])
    return result


@router.get("/articles/{id}/bookmark")
def bookmark_status(id: str, user=Depends(current_user), db=Depends(db_session)):
    return {
        "bookmarked": db.scalar(
            select(m.ArticleBookmark).where(
                m.ArticleBookmark.user_id == user.id, m.ArticleBookmark.article_id == id
            )
        )
        is not None
    }


@router.put("/articles/{id}/bookmark")
def bookmark(id: str, user=Depends(current_user), db=Depends(db_session)):
    article = db.get(m.Article, id)
    if not article or article.status != "published":
        raise HTTPException(404)
    row = db.scalar(
        select(m.ArticleBookmark).where(
            m.ArticleBookmark.user_id == user.id, m.ArticleBookmark.article_id == id
        )
    )
    if not row:
        db.add(m.ArticleBookmark(user_id=user.id, article_id=id))
    return {"bookmarked": True}


@router.delete("/articles/{id}/bookmark", status_code=204)
def unbookmark(id: str, user=Depends(current_user), db=Depends(db_session)):
    row = db.scalar(
        select(m.ArticleBookmark).where(
            m.ArticleBookmark.user_id == user.id, m.ArticleBookmark.article_id == id
        )
    )
    if row:
        db.delete(row)


@router.get("/companies", response_model=s.Page[s.CompanyResponse])
def companies(
    user=Depends(current_user),
    db=Depends(db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return paginate(db, m.Company, [m.Company.owner_id == user.id], page, page_size)


@router.post("/companies", status_code=201, response_model=s.CompanyResponse)
def create_company(
    data: s.CompanyInput, user=Depends(current_user), db=Depends(db_session)
):
    from app.professional.privacy import protect

    values = data.model_dump()
    profile = dict(values["profile_data"])
    if values.get("trn"):
        profile["_legacy_trn"] = values["trn"]
        values["trn"] = None
    values["profile_data"] = protect(profile)
    row = m.Company(owner_id=user.id, **values)
    db.add(row)
    db.flush()
    return serialize(row)


@router.get("/companies/{id}", response_model=s.CompanyResponse)
def get_company(id: str, user=Depends(current_user), db=Depends(db_session)):
    return serialize(owned(db, id, user))


@router.put("/companies/{id}")
def edit_company(
    id: str, data: s.CompanyInput, user=Depends(current_user), db=Depends(db_session)
):
    row = owned(db, id, user)
    from app.professional.privacy import protect

    values = data.model_dump()
    profile = dict(values["profile_data"])
    if values.get("trn"):
        profile["_legacy_trn"] = values["trn"]
        values["trn"] = None
    values["profile_data"] = protect(profile)
    for k, v in values.items():
        setattr(row, k, v)
    return serialize(row)


@router.delete("/companies/{id}", status_code=204)
def delete_company(id: str, user=Depends(current_user), db=Depends(db_session)):
    db.delete(owned(db, id, user))


def add_company_child(kind, model, schema):
    def listing(
        id: str,
        user=Depends(current_user),
        db=Depends(db_session),
        page: int = Query(1, ge=1),
        page_size: int = Query(100, ge=1, le=100),
    ):
        owned(db, id, user)
        return paginate(db, model, [model.company_id == id], page, page_size)

    def write(id: str, data, child_id=None, user=None, db=None):
        owned(db, id, user)
        values = data.model_dump()
        if "details" in values:
            from app.professional.privacy import protect

            values["details"] = protect(values["details"])
        for field, related in [
            ("person_id", m.CompanyPerson),
            ("document_id", m.CompanyDocument),
        ]:
            if values.get(field):
                target = db.get(related, values[field])
                if not target or target.company_id != id:
                    raise HTTPException(
                        422, "Related record belongs to another company"
                    )
        if child_id:
            row = db.scalar(
                select(model).where(model.id == child_id, model.company_id == id)
            )
            if not row:
                raise HTTPException(404)
            for k, v in values.items():
                setattr(row, k, v)
        else:
            row = model(company_id=id, **values)
            db.add(row)
        db.flush()
        if kind == "documents":
            from app.professional.notifications import schedule_document

            schedule_document(db, row, user)
        return serialize(row)

    def create(
        id: str, data: schema, user=Depends(current_user), db=Depends(db_session)
    ):
        return write(id, data, user=user, db=db)

    def edit(
        id: str,
        child_id: str,
        data: schema,
        user=Depends(current_user),
        db=Depends(db_session),
    ):
        return write(id, data, child_id, user, db)

    def delete(
        id: str, child_id: str, user=Depends(current_user), db=Depends(db_session)
    ):
        owned(db, id, user)
        row = db.scalar(
            select(model).where(model.id == child_id, model.company_id == id)
        )
        if not row:
            raise HTTPException(404)
        if kind == "documents":
            from app.professional.notifications import cancel_future

            cancel_future(db, "document", row.id)
        db.delete(row)

    path = "/companies/{id}/" + kind
    router.add_api_route(
        path, listing, methods=["GET"], response_model=s.Page, name="company_" + kind
    )
    router.add_api_route(
        path, create, methods=["POST"], status_code=201, name="create_" + kind
    )
    router.add_api_route(
        path + "/{child_id}", edit, methods=["PUT"], name="edit_" + kind
    )
    router.add_api_route(
        path + "/{child_id}",
        delete,
        methods=["DELETE"],
        status_code=204,
        name="delete_" + kind,
    )


add_company_child("people", m.CompanyPerson, s.PersonInput)
add_company_child("documents", m.CompanyDocument, s.DocumentInput)
add_company_child("reminders", m.CompanyReminder, s.ReminderInput)


@router.get("/dashboard")
def dashboard(user=Depends(current_user), db=Depends(db_session)):
    deadline = db.scalar(
        select(m.CompanyReminder)
        .join(m.Company)
        .where(m.Company.owner_id == user.id, m.CompanyReminder.completed.is_(False))
        .order_by(m.CompanyReminder.due_on)
        .limit(1)
    )
    from app.professional.models import ComplianceObligation

    candidates = [serialize(deadline)] if deadline else []
    for model, date_field, conditions in [
        (
            ComplianceObligation,
            ComplianceObligation.due_on,
            [ComplianceObligation.status == "pending"],
        ),
        (
            m.CompanyDocument,
            m.CompanyDocument.expires_on,
            [m.CompanyDocument.status == "active"],
        ),
    ]:
        item = db.scalar(
            select(model)
            .join(m.Company)
            .where(m.Company.owner_id == user.id, date_field.is_not(None), *conditions)
            .order_by(date_field)
            .limit(1)
        )
        if item:
            value = serialize(item)
            value["due_on"] = value.get("due_on") or value.get("expires_on")
            candidates.append(value)
    nearest = min(candidates, key=lambda x: str(x["due_on"])) if candidates else None
    return {
        "profile": me(user, db),
        "next_deadline": nearest,
        "updates": paginate(
            db,
            m.RegulatoryUpdate,
            [
                m.RegulatoryUpdate.status == "published",
                or_(
                    m.RegulatoryUpdate.publish_at.is_(None),
                    m.RegulatoryUpdate.publish_at <= m.now(),
                ),
            ],
            page_size=3,
        )["items"],
        "unread_count": db.scalar(
            select(func.count())
            .select_from(m.NotificationRecipient)
            .where(
                m.NotificationRecipient.user_id == user.id,
                m.NotificationRecipient.read_at.is_(None),
            )
        ),
    }


@router.get("/notifications", response_model=s.Page)
def notifications(
    user=Depends(current_user),
    db=Depends(db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = (
        select(m.Notification, m.NotificationRecipient)
        .join(m.NotificationRecipient)
        .where(
            m.NotificationRecipient.user_id == user.id,
            m.Notification.status == "published",
        )
    )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(
        query.order_by(m.Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [{**serialize(n), "read_at": r.read_at} for n, r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/notifications/{id}/read")
def read_notification(id: str, user=Depends(current_user), db=Depends(db_session)):
    row = db.scalar(
        select(m.NotificationRecipient).where(
            m.NotificationRecipient.user_id == user.id,
            m.NotificationRecipient.notification_id == id,
        )
    )
    if not row:
        raise HTTPException(404)
    row.read_at = m.now()
    return {"read": True}


@router.get("/toolkit/gratuity")
def calculate(
    monthly_basic: Decimal = Query(gt=0, le=100000000),
    years: Decimal = Query(ge=0, le=80),
):
    return gratuity(monthly_basic, years)


@router.get("/discuss/capabilities")
def capabilities():
    return {
        "mode": "demonstration",
        "inference_enabled": False,
        "message": "Custom GPT integration is reserved for Phase 2",
    }


@router.get("/admin/dashboard")
def admin_dashboard(user=Depends(editor), db=Depends(db_session)):
    models = {"users": m.User, **CONTENT}
    result = {
        key: db.scalar(select(func.count()).select_from(model))
        for key, model in models.items()
    }
    result["companies"] = db.scalar(select(func.count()).select_from(m.Company))
    result["recent_activity"] = paginate(db, m.AuditLog, page_size=10)["items"]
    return result


def publish_notification(db, row):
    # Fan-out is bounded here; large installations should replace this with an external job adapter.
    existing = select(m.NotificationRecipient.user_id).where(
        m.NotificationRecipient.notification_id == row.id
    )
    users = db.scalars(
        select(m.User.id)
        .where(m.User.status == "active", m.User.id.not_in(existing))
        .limit(1001)
    ).all()
    if len(users) > 1000:
        raise HTTPException(
            413,
            "This synchronous publication supports at most 1000 new recipients. Configure a durable batch delivery adapter for larger campaigns.",
        )
    preferences = {
        p.user_id: p
        for p in db.scalars(
            select(m.NotificationPreference).where(
                m.NotificationPreference.user_id.in_(users)
            )
        )
    }
    for uid in users:
        pref = preferences.get(uid)
        if pref and (
            not pref.in_app or (pref.categories and row.category not in pref.categories)
        ):
            continue
        db.add(m.NotificationRecipient(user_id=uid, notification_id=row.id))


def add_admin_routes(kind, model, schema):
    def listing(
        q: str = "",
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        user=Depends(editor),
        db=Depends(db_session),
    ):
        col = getattr(model, "title", getattr(model, "name", None))
        return paginate(
            db, model, [col.ilike("%" + q + "%")] if q else [], page, page_size
        )

    def write(data, user, db, id=None):
        values = data.model_dump()
        if kind == "updates" and values.get("status") == "published":
            raise HTTPException(
                409, "Use the regulatory review/approval workflow before publication"
            )
        if kind == "webinars":
            if values.get("starts_at") and values["starts_at"].tzinfo is None:
                raise HTTPException(422, "Webinar time requires timezone offset")
            meta = values.get("metadata_extra", {})
            if (
                int(meta.get("capacity", 0)) < 0
                or int(meta.get("capacity", 0)) > 100000
            ):
                raise HTTPException(422, "Invalid webinar capacity")
        asset_id = values.get("asset_id") or values.get("metadata_extra", {}).get(
            "asset_id"
        )
        if asset_id:
            from app.professional.models import MediaAsset

            asset = db.get(MediaAsset, asset_id)
            if not asset or asset.company_id:
                raise HTTPException(
                    422,
                    "Select a learning asset, not a company-confidential attachment",
                )
        if kind == "chapters" and not db.get(m.Publication, values["publication_id"]):
            raise HTTPException(422, "Publication not found")
        if values.get("video_category_id") and not db.get(
            m.VideoCategory, values["video_category_id"]
        ):
            raise HTTPException(422, "Video subcategory not found")
        if values.get("category_id") and not db.get(
            m.SubjectCategory, values["category_id"]
        ):
            raise HTTPException(422, "Category not found")
        values = {k: v for k, v in values.items() if k in inspect(model).columns}
        row = db.get(model, id) if id else model(**values)
        if row is None:
            raise HTTPException(404)
        if id:
            for k, v in values.items():
                setattr(row, k, v)
        else:
            db.add(row)
        db.flush()
        if kind == "notifications" and row.status == "published":
            publish_notification(db, row)
        audit(db, user, ("edit_" if id else "create_") + kind, row.id)
        return serialize(row)

    def create(data: schema, user=Depends(editor), db=Depends(db_session)):
        return write(data, user, db)

    def edit(id: str, data: schema, user=Depends(editor), db=Depends(db_session)):
        return write(data, user, db, id)

    def delete(id: str, user=Depends(editor), db=Depends(db_session)):
        row = db.get(model, id)
        if not row:
            raise HTTPException(404)
        if hasattr(row, "status"):
            row.status = "archived" if kind != "notifications" else "draft"
        else:
            db.delete(row)
        audit(db, user, "delete_" + kind, id)

    path = "/admin/content/" + kind
    if kind in {"updates", "notifications"}:
        path = "/admin/" + kind
    router.add_api_route(
        path, listing, methods=["GET"], response_model=s.Page, name="admin_list_" + kind
    )
    router.add_api_route(
        path, create, methods=["POST"], status_code=201, name="admin_create_" + kind
    )
    router.add_api_route(
        path + "/{id}", edit, methods=["PUT"], name="admin_edit_" + kind
    )
    router.add_api_route(
        path + "/{id}",
        delete,
        methods=["DELETE"],
        status_code=204,
        name="admin_delete_" + kind,
    )


for kind, model in ADMIN.items():
    schema = (
        s.CategoryInput
        if kind == "categories"
        else (
            s.ChapterInput
            if kind == "chapters"
            else s.NotificationInput if kind == "notifications" else s.ContentInput
        )
    )
    add_admin_routes(kind, model, schema)


@router.get("/admin/content")
def content_index(user=Depends(editor)):
    return {"resources": list(ADMIN)}


@router.get("/admin/users", response_model=s.Page)
def users(
    q: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(administrator),
    db=Depends(db_session),
):
    result = paginate(
        db, m.User, [m.User.email.ilike("%" + q + "%")] if q else [], page, page_size
    )
    for row in result["items"]:
        row.pop("password_hash")
        row["roles"] = roles(db, row["id"])
    return result


@router.put("/admin/users/{id}")
def update_user(
    id: str, data: s.AccountInput, user=Depends(administrator), db=Depends(db_session)
):
    if id == user.id:
        raise HTTPException(403, "Cannot alter own account here")
    target = db.get(m.User, id)
    if not target:
        raise HTTPException(404)
    existing_roles = roles(db, id)
    if "super_admin" not in roles(db, user.id) and set(data.roles) != set(
        existing_roles
    ):
        raise HTTPException(403, "Only super administrators may change roles")
    if "super_admin" in existing_roles and "super_admin" not in roles(db, user.id):
        raise HTTPException(403)
    target.status = data.status
    for row in db.scalars(select(m.UserRole).where(m.UserRole.user_id == id)):
        db.delete(row)
    db.flush()
    for name in set(data.roles):
        role = db.scalar(select(m.Role).where(m.Role.name == name))
        if role is None:
            role = m.Role(name=name)
            db.add(role)
            db.flush()
        db.add(m.UserRole(user_id=id, role_id=role.id))
    audit(db, user, "update_user", id)
    return {"id": id, "status": target.status, "roles": data.roles}


@router.get("/admin/settings", response_model=s.Page)
def app_settings(user=Depends(administrator), db=Depends(db_session)):
    return paginate(db, m.AppSetting)


@router.put("/admin/settings")
def save_setting(
    data: s.SettingInput, user=Depends(administrator), db=Depends(db_session)
):
    row = db.scalar(select(m.AppSetting).where(m.AppSetting.key == data.key))
    if not row:
        row = m.AppSetting(**data.model_dump())
        db.add(row)
    else:
        row.value = data.value
    db.flush()
    audit(db, user, "update_setting", row.id)
    return serialize(row)


@router.get("/admin/audit-logs", response_model=s.Page)
def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(administrator),
    db=Depends(db_session),
):
    return paginate(db, m.AuditLog, page=page, page_size=page_size)
