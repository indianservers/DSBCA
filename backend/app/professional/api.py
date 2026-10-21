from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import calendar, hashlib, io, json, secrets, uuid, csv
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    Form,
    Request,
)
from fastapi.responses import Response
from sqlalchemy import select, func, or_
from app import models as m
from app.core.database import db_session
from app.core.security import (
    current_user,
    optional_user,
    sensitive,
    editor,
    administrator,
    roles,
)
from app.api.resources import owned, audit, serialize, paginate, CONTENT
from app.professional import models as p, schemas as s
from app.professional.privacy import protect, reveal
from app.calculators.engine import calculate, period, dt
from app.calculators.catalogue import CATALOGUE
from app.professional.notifications import (
    schedule_document,
    schedule_obligation,
    plan,
    cancel_future,
    tick,
)
from app.core.config import settings

router = APIRouter()


def clean(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    return value


def row(value):
    result = clean(serialize(value))
    if isinstance(value, p.ComplianceHistory):
        result["snapshot"] = reveal(result["snapshot"])
    return result


def published(db, kind, id, user=None):
    model = CONTENT.get(kind) if kind != "chapters" else m.PublicationChapter
    if model is None:
        raise HTTPException(422, "Unsupported resource kind")
    record = db.get(model, id)
    if not record:
        raise HTTPException(404)
    parent = (
        db.get(m.Publication, record.publication_id) if kind == "chapters" else record
    )
    if (
        parent.status != "published"
        or (parent.visibility == "authenticated" and not user)
        or (
            parent.publish_at
            and parent.publish_at.replace(tzinfo=timezone.utc) > m.now()
        )
    ):
        raise HTTPException(404)
    return record


def source_valid(source):
    from urllib.parse import urlparse

    url = source.get("url", "")
    host = urlparse(url).hostname
    if not url.startswith("https://") or host not in [
        "tax.gov.ae",
        "www.tax.gov.ae",
        "mof.gov.ae",
        "www.mof.gov.ae",
        "u.ae",
        "www.u.ae",
        "oecd.org",
        "www.oecd.org",
        "ifrs.org",
        "www.ifrs.org",
        "uaelegislation.gov.ae",
        "www.uaelegislation.gov.ae",
    ]:
        raise HTTPException(
            422, "Rule source must be an approved official primary-source domain"
        )
    if not source.get("title") or not source.get("verified_on"):
        raise HTTPException(422, "Source title and verification date required")
    try:
        verified = date.fromisoformat(source["verified_on"])
    except Exception:
        raise HTTPException(422, "Verification date must use YYYY-MM-DD")
    if verified > m.now().date():
        raise HTTPException(422, "Verification date cannot be in the future")


def rule_snapshot(rule):
    return {
        key: row(rule)[key]
        for key in [
            "id",
            "code",
            "version",
            "valid_from",
            "valid_to",
            "parameters",
            "sources",
            "validated_at",
        ]
    }


def run_calculator(db, code, data, user=None):
    if code not in CATALOGUE:
        raise HTTPException(404, "Calculator not found")
    if len(json.dumps(data.inputs)) > 120000:
        raise HTTPException(413, "Calculation input too large")
    rule = None
    if CATALOGUE[code].get("rule_required"):
        start, end = (
            period(data.inputs)
            if code != "gratuity"
            else (dt(data.inputs, "employment_end"), dt(data.inputs, "employment_end"))
        )
        query = select(p.RuleVersion).where(
            p.RuleVersion.code == code,
            p.RuleVersion.category == "calculator",
            p.RuleVersion.status == "published",
            p.RuleVersion.valid_from <= start,
            or_(p.RuleVersion.valid_to.is_(None), p.RuleVersion.valid_to >= end),
        )
        if data.rule_id:
            query = query.where(p.RuleVersion.id == data.rule_id)
        candidates = list(db.scalars(query))
        if len(candidates) != 1:
            return {
                "status": "restricted",
                "results": {},
                "warnings": [
                    "No single reviewed and published rule covers the requested period. Ask an administrator to validate an applicable rule version."
                ],
                "calculator": code,
                "inputs": data.inputs,
                "rule": None,
            }
        rule = candidates[0]
    try:
        result = clean(calculate(code, data.inputs, rule.parameters if rule else None))
    except (ValueError, KeyError, ArithmeticError) as e:
        raise HTTPException(
            422,
            (
                str(e)
                if isinstance(e, ValueError)
                else "Invalid inputs or incomplete rule parameters"
            ),
        )
    result.update(
        {
            "calculator": code,
            "inputs": data.inputs,
            "rule": (
                rule_snapshot(rule)
                if rule
                else {"version": "financial-math-3.0.0", "sources": []}
            ),
        }
    )
    if data.save:
        if not user:
            raise HTTPException(401)
        saved = p.CalculatorRun(
            owner_id=user.id,
            calculator=code,
            title=data.title,
            inputs=data.inputs,
            result=result,
            rule_snapshot=result["rule"],
        )
        db.add(saved)
        db.flush()
        result["run_id"] = saved.id
        audit(db, user, "save_calculation", saved.id)
    return result


@router.get("/professional/calculators")
def catalogue(db=Depends(db_session)):
    rules = list(
        db.scalars(
            select(p.RuleVersion).where(
                p.RuleVersion.category == "calculator",
                p.RuleVersion.status == "published",
            )
        )
    )
    return {
        "items": [
            {
                "code": code,
                **definition,
                "rules": [rule_snapshot(r) for r in rules if r.code == code],
            }
            for code, definition in CATALOGUE.items()
        ]
    }


@router.post(
    "/professional/calculators/{code}/calculate", dependencies=[Depends(sensitive)]
)
def compute(
    code: str,
    data: s.CalculationInput,
    user=Depends(optional_user),
    db=Depends(db_session),
):
    try:
        return run_calculator(db, code, data, user)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/professional/calculations")
def calculations(
    page: int = Query(1, ge=1), user=Depends(current_user), db=Depends(db_session)
):
    return paginate(
        db, p.CalculatorRun, [p.CalculatorRun.owner_id == user.id], page, 20
    )


@router.get("/professional/calculations/{id}")
def saved_calculation(id: str, user=Depends(current_user), db=Depends(db_session)):
    record = db.scalar(
        select(p.CalculatorRun).where(
            p.CalculatorRun.id == id, p.CalculatorRun.owner_id == user.id
        )
    )
    if not record:
        raise HTTPException(404)
    return row(record)


@router.get("/professional/calculations/{id}/export")
def export_calculation(id: str, user=Depends(current_user), db=Depends(db_session)):
    saved = saved_calculation(id, user, db)
    # CSV formula injection protection; JSON is lossless and includes inputs and rule snapshot.
    return Response(
        json.dumps(saved, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="calculation.json"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/admin/professional/rules")
def rules(
    user=Depends(administrator),
    db=Depends(db_session),
    page: int = Query(1, ge=1),
    q: str = "",
    category: str | None = None,
):
    conditions = (
        [or_(p.RuleVersion.code.ilike(f"%{q}%"), p.RuleVersion.version.ilike(f"%{q}%"))]
        if q
        else []
    )
    if category:
        conditions.append(p.RuleVersion.category == category)
    return paginate(db, p.RuleVersion, conditions, page=page)


@router.post("/admin/professional/rules", status_code=201)
def create_rule(data: s.RuleInput, user=Depends(administrator), db=Depends(db_session)):
    if data.valid_to and data.valid_to < data.valid_from:
        raise HTTPException(422, "Rule dates reversed")
    if data.code not in CATALOGUE and data.code not in ["ct_filing", "vat_filing"]:
        raise HTTPException(422, "No implementation for this rule code")
    if (data.category == "compliance") != (data.code in ["ct_filing", "vat_filing"]):
        raise HTTPException(422, "Rule category does not match its implemented engine")
    for source in data.sources:
        source_valid(source)
    record = p.RuleVersion(**data.model_dump(), author_id=user.id)
    db.add(record)
    db.flush()
    audit(db, user, "create_rule_version", record.id)
    return row(record)


def validate_rule(record):
    if not record.validation_cases:
        raise HTTPException(422, "Validation cases required")
    if record.category == "calculator":
        for case in record.validation_cases:
            if not case.get("expected"):
                raise HTTPException(422, "Reference cases need expected result fields")
            try:
                actual = clean(
                    calculate(record.code, case["inputs"], record.parameters)
                )["results"]
            except Exception:
                raise HTTPException(422, "Rule reference case failed to calculate")
            if any(str(actual.get(k)) != str(v) for k, v in case["expected"].items()):
                raise HTTPException(422, "Rule reference case result mismatch")
    else:
        if record.code == "ct_filing" and record.parameters != {"months_after": 9}:
            raise HTTPException(
                422, "Only the reviewed nine-month CT filing basis is implemented"
            )
        if record.code == "vat_filing" and record.parameters != {"days_after": 28}:
            raise HTTPException(
                422, "Only the reviewed 28-day VAT filing basis is implemented"
            )
    for source in record.sources:
        source_valid(source)


@router.post("/admin/professional/rules/{id}/{action}")
def rule_action(
    id: str, action: str, user=Depends(administrator), db=Depends(db_session)
):
    record = db.scalar(
        select(p.RuleVersion).where(p.RuleVersion.id == id).with_for_update()
    )
    if not record:
        raise HTTPException(404)
    if action in {"validate", "publish"} and record.status != "draft":
        raise HTTPException(
            409, "Reviewed or superseded versions are immutable; create a new version"
        )
    if action == "supersede" and record.status != "published":
        raise HTTPException(409, "Only a published rule can be superseded")
    if action == "validate":
        validate_rule(record)
        record.validated_at = m.now()
    elif action == "publish":
        if not record.validated_at:
            raise HTTPException(409, "Validate reference cases first")
        if record.author_id == user.id:
            raise HTTPException(
                403, "A different administrator must review and publish this rule"
            )
        validate_rule(record)
        overlap = db.scalar(
            select(p.RuleVersion.id).where(
                p.RuleVersion.code == record.code,
                p.RuleVersion.status == "published",
                p.RuleVersion.id != id,
                p.RuleVersion.valid_from <= (record.valid_to or date.max),
                or_(
                    p.RuleVersion.valid_to.is_(None),
                    p.RuleVersion.valid_to >= record.valid_from,
                ),
            )
        )
        if overlap:
            raise HTTPException(
                409,
                "Published applicability windows overlap; supersede the previous rule first",
            )
        record.status = "published"
        record.approved_by = user.id
    elif action == "supersede":
        record.status = "superseded"
    else:
        raise HTTPException(404)
    audit(db, user, "rule_" + action, id)
    return row(record)


@router.get("/professional/learning/{kind}/{id}/state")
def learning_state(
    kind: str, id: str, user=Depends(current_user), db=Depends(db_session)
):
    published(db, kind, id, user)
    progress = db.scalar(
        select(p.LearningProgress).where(
            p.LearningProgress.user_id == user.id,
            p.LearningProgress.kind == kind,
            p.LearningProgress.resource_id == id,
        )
    )
    bookmark = db.scalar(
        select(p.ContentBookmark.id).where(
            p.ContentBookmark.user_id == user.id,
            p.ContentBookmark.kind == kind,
            p.ContentBookmark.resource_id == id,
        )
    )
    return {
        "progress": row(progress) if progress else {"position": 0, "completed": False},
        "bookmarked": bool(bookmark),
    }


@router.put("/professional/learning/{kind}/{id}/progress")
def progress(
    kind: str,
    id: str,
    data: s.ProgressInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    target = published(db, kind, id, user)
    record = db.scalar(
        select(p.LearningProgress).where(
            p.LearningProgress.user_id == user.id,
            p.LearningProgress.kind == kind,
            p.LearningProgress.resource_id == id,
        )
    )
    if not record:
        record = p.LearningProgress(user_id=user.id, kind=kind, resource_id=id)
        db.add(record)
    if (
        kind == "videos"
        and target.duration_seconds
        and data.position > target.duration_seconds + 5
    ):
        raise HTTPException(422, "Progress exceeds video duration")
    record.position, record.completed = data.position, data.completed
    db.flush()
    return row(record)


@router.put("/professional/learning/{kind}/{id}/bookmark")
def learning_bookmark(
    kind: str,
    id: str,
    data: s.BookmarkInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    published(db, kind, id, user)
    record = db.scalar(
        select(p.ContentBookmark).where(
            p.ContentBookmark.user_id == user.id,
            p.ContentBookmark.kind == kind,
            p.ContentBookmark.resource_id == id,
        )
    )
    if data.saved and not record:
        db.add(p.ContentBookmark(user_id=user.id, kind=kind, resource_id=id))
    if not data.saved and record:
        db.delete(record)
    return {"saved": data.saved}


@router.get("/professional/learning/library")
def library(view: str = "saved", user=Depends(current_user), db=Depends(db_session)):
    model = p.ContentBookmark if view == "saved" else p.LearningProgress
    records = list(
        db.scalars(
            select(model)
            .where(model.user_id == user.id)
            .order_by(model.updated_at.desc())
            .limit(100)
        )
    )
    result = []
    for record in records:
        try:
            item = published(db, record.kind, record.resource_id, user)
        except HTTPException:
            continue
        result.append(
            {
                **row(record),
                "title": item.title,
                "path": f"/content/{record.kind}/{record.resource_id}",
            }
        )
    return {"items": result, "total": len(result)}


@router.get("/professional/learning/paths")
def paths(user=Depends(current_user), db=Depends(db_session)):
    result = []
    for path in db.scalars(
        select(p.LearningPath).where(p.LearningPath.status == "published")
    ):
        items = list(
            db.scalars(
                select(p.LearningPathItem)
                .where(p.LearningPathItem.path_id == path.id)
                .order_by(p.LearningPathItem.position)
            )
        )
        completed = 0
        visible = []
        for item in items:
            try:
                resource = published(db, item.kind, item.resource_id, user)
            except HTTPException:
                continue
            state = learning_state(item.kind, item.resource_id, user, db)
            completed += int(state["progress"]["completed"])
            visible.append(
                {
                    **row(item),
                    "title": resource.title,
                    "completed": state["progress"]["completed"],
                }
            )
        enrolled = bool(
            db.scalar(
                select(p.LearningEnrollment.id).where(
                    p.LearningEnrollment.path_id == path.id,
                    p.LearningEnrollment.user_id == user.id,
                )
            )
        )
        result.append(
            {
                **row(path),
                "items": visible,
                "enrolled": enrolled,
                "progress_percent": (
                    round(completed / len(visible) * 100) if visible else 0
                ),
            }
        )
    return {"items": result, "total": len(result)}


@router.post("/professional/learning/paths/{id}/enroll")
def enroll(id: str, user=Depends(current_user), db=Depends(db_session)):
    path = db.get(p.LearningPath, id)
    if not path or path.status != "published":
        raise HTTPException(404)
    if not db.scalar(
        select(p.LearningEnrollment.id).where(
            p.LearningEnrollment.path_id == id, p.LearningEnrollment.user_id == user.id
        )
    ):
        db.add(p.LearningEnrollment(path_id=id, user_id=user.id))
    return {"enrolled": True}


@router.get("/admin/professional/learning-paths")
def admin_paths(
    user=Depends(editor),
    db=Depends(db_session),
    page: int = Query(1, ge=1),
    q: str = "",
):
    result = paginate(
        db,
        p.LearningPath,
        [p.LearningPath.title.ilike(f"%{q}%")] if q else [],
        page=page,
    )
    for item in result["items"]:
        item["items"] = [
            row(x)
            for x in db.scalars(
                select(p.LearningPathItem)
                .where(p.LearningPathItem.path_id == item["id"])
                .order_by(p.LearningPathItem.position)
            )
        ]
    return result


@router.post("/admin/professional/learning-paths", status_code=201)
def create_path(data: s.PathInput, user=Depends(editor), db=Depends(db_session)):
    path = p.LearningPath(**data.model_dump(exclude={"items"}))
    db.add(path)
    db.flush()
    for i, item in enumerate(data.items):
        published(db, item.get("kind"), item.get("resource_id"), user)
        db.add(
            p.LearningPathItem(
                path_id=path.id,
                kind=item["kind"],
                resource_id=item["resource_id"],
                position=i + 1,
            )
        )
    audit(db, user, "create_learning_path", path.id)
    return row(path)


def validate_company_asset(db, details, company_id):
    aid = details.get("asset_id")
    if aid:
        asset = db.get(p.MediaAsset, aid)
        if not asset or asset.company_id != company_id:
            raise HTTPException(422, "Attachment must belong to this company")


@router.put("/professional/companies/{id}/documents/{document_id}")
def update_document(
    id: str,
    document_id: str,
    data: s.DocumentChange,
    user=Depends(current_user),
    db=Depends(db_session),
):
    owned(db, id, user)
    document = db.scalar(
        select(m.CompanyDocument)
        .where(m.CompanyDocument.id == document_id, m.CompanyDocument.company_id == id)
        .with_for_update()
    )
    if not document:
        raise HTTPException(404)
    if data.person_id:
        person = db.get(m.CompanyPerson, data.person_id)
        if not person or person.company_id != id:
            raise HTTPException(422, "Person belongs to another company")
    db.add(
        p.ComplianceHistory(
            company_id=id,
            resource_id=document_id,
            actor_id=user.id,
            action="renew" if document.expires_on != data.expires_on else "edit",
            snapshot=protect(row(document)),
        )
    )
    validate_company_asset(db, data.details, id)
    values = data.model_dump()
    values["details"] = protect(values["details"])
    for key, value in values.items():
        setattr(document, key, value)
    db.flush()
    schedule_document(db, document, user)
    audit(db, user, "update_company_document", document_id)
    return row(document)


@router.get("/professional/companies/{id}/compliance")
def compliance(
    id: str,
    user=Depends(current_user),
    db=Depends(db_session),
    category: str | None = None,
    person_id: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
):
    company = owned(db, id, user)
    if from_date and to_date and from_date > to_date:
        raise HTTPException(422, "Expiry date range is reversed")
    today = m.now().date()
    documents = []
    for doc in db.scalars(
        select(m.CompanyDocument).where(m.CompanyDocument.company_id == id)
    ):
        if category and doc.category != category:
            continue
        if person_id and doc.person_id != person_id:
            continue
        if from_date and doc.expires_on < from_date:
            continue
        if to_date and doc.expires_on > to_date:
            continue
        remaining = (doc.expires_on - today).days
        state = (
            doc.status
            if doc.status in ["archived", "not_applicable", "needs_review", "renewed"]
            else (
                "expired"
                if remaining < 0
                else "due_soon" if remaining <= 30 else "upcoming"
            )
        )
        documents.append(
            {**row(doc), "expiry_status": state, "days_remaining": remaining}
        )
    return {
        "company": row(company),
        "documents": documents,
        "obligations": [
            row(o)
            for o in db.scalars(
                select(p.ComplianceObligation).where(
                    p.ComplianceObligation.company_id == id
                )
            )
        ],
        "history": [
            row(h)
            for h in db.scalars(
                select(p.ComplianceHistory)
                .where(p.ComplianceHistory.company_id == id)
                .order_by(p.ComplianceHistory.created_at.desc())
                .limit(50)
            )
        ],
    }


@router.get("/professional/reminder-settings")
def reminder_settings(user=Depends(current_user), db=Depends(db_session)):
    pref = db.scalar(
        select(m.ReminderPreference).where(m.ReminderPreference.user_id == user.id)
    )
    return {
        "days": pref.schedule if pref else [30, 7, 0],
        "channels": pref.channels if pref else ["in_app"],
        "enabled": pref.enabled if pref else True,
    }


@router.put("/professional/reminder-settings")
def put_reminder_settings(
    data: s.ReminderSettings, user=Depends(current_user), db=Depends(db_session)
):
    pref = db.scalar(
        select(m.ReminderPreference).where(m.ReminderPreference.user_id == user.id)
    )
    if not pref:
        pref = m.ReminderPreference(user_id=user.id)
        db.add(pref)
    pref.schedule, pref.channels, pref.enabled = data.days, data.channels, data.enabled
    db.flush()
    for document in db.scalars(
        select(m.CompanyDocument).join(m.Company).where(m.Company.owner_id == user.id)
    ):
        schedule_document(db, document, user)
    for obligation in db.scalars(
        select(p.ComplianceObligation)
        .join(m.Company)
        .where(m.Company.owner_id == user.id)
    ):
        schedule_obligation(db, obligation, user)
    return data.model_dump()


@router.post("/professional/companies/{id}/obligations", status_code=201)
def create_obligation(
    id: str, data: s.ObligationInput, user=Depends(current_user), db=Depends(db_session)
):
    company = owned(db, id, user)
    due = data.due_on
    origin = "manual"
    status = "pending" if due else "awaiting_confirmation"
    basis = {}
    rule = None
    if data.rule_id:
        rule = db.get(p.RuleVersion, data.rule_id)
        if not rule or rule.category != "compliance" or rule.status != "published":
            raise HTTPException(422, "Select a published compliance rule")
        origin = "rule_derived"
        basis = {"rule": rule_snapshot(rule), "facts": data.facts}
        if (
            not data.facts_confirmed
            or not data.period_end
            or not data.period_start
            or not data.facts.get("registered")
            or data.facts.get("exceptions") is not False
        ):
            due = None
            status = "awaiting_confirmation"
        else:
            if (
                data.period_start > data.period_end
                or data.period_start < rule.valid_from
                or (rule.valid_to and data.period_end > rule.valid_to)
            ):
                raise HTTPException(422, "No applicable period coverage")
            if rule.code == "ct_filing":
                month = data.period_end.month + 9
                year = data.period_end.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                due = date(
                    year,
                    month,
                    min(data.period_end.day, calendar.monthrange(year, month)[1]),
                )
                # Tax periods ending on month-end retain the end-of-month filing basis.
                if (
                    data.period_end.day
                    == calendar.monthrange(data.period_end.year, data.period_end.month)[
                        1
                    ]
                ):
                    due = date(year, month, calendar.monthrange(year, month)[1])
            elif rule.code == "vat_filing":
                due = data.period_end + timedelta(days=28)
            else:
                raise HTTPException(422, "Unsupported deadline formula")
            status = "pending"
            if (
                due.weekday() >= 5
                and data.facts.get("calendar_exception_verified") is not True
            ):
                basis["nominal_due_on"] = due.isoformat()
                due = None
                status = "awaiting_confirmation"
            basis["calculation"] = (
                "period end + "
                + ("9 calendar months" if rule.code == "ct_filing" else "28 days")
                + "; weekends/holidays/extensions require confirmation"
            )
    record = p.ComplianceObligation(
        company_id=id,
        title=data.title,
        period_start=data.period_start,
        period_end=data.period_end,
        due_on=due,
        origin=origin,
        status=status,
        rule_id=rule.id if rule else None,
        basis=basis,
        confirmed_at=m.now() if data.facts_confirmed else None,
    )
    db.add(record)
    db.flush()
    audit(db, user, "create_obligation", record.id)
    if due:
        schedule_obligation(db, record, user)
    return row(record)


@router.patch("/professional/companies/{id}/obligations/{obligation_id}")
def obligation_state(
    id: str,
    obligation_id: str,
    data: s.StateInput,
    user=Depends(current_user),
    db=Depends(db_session),
):
    owned(db, id, user)
    record = db.get(p.ComplianceObligation, obligation_id)
    if not record or record.company_id != id:
        raise HTTPException(404)
    db.add(
        p.ComplianceHistory(
            company_id=id,
            resource_id=record.id,
            actor_id=user.id,
            action=data.status,
            snapshot=protect(row(record)),
        )
    )
    record.status = data.status
    if data.status != "pending":
        cancel_future(db, "obligation", record.id)
    if data.status == "pending":
        schedule_obligation(db, record, user)
    return row(record)


@router.get("/professional/notifications/settings")
def delivery_settings(user=Depends(current_user), db=Depends(db_session)):
    pref = db.scalar(
        select(m.NotificationPreference).where(
            m.NotificationPreference.user_id == user.id
        )
    )
    cfg = settings()
    return {
        "in_app": pref.in_app if pref else True,
        "email": pref.email if pref else False,
        "push": pref.push if pref else False,
        "email_configured": bool(cfg.resend_api_key),
        "push_configured": bool(cfg.fcm_project_id and cfg.fcm_service_account_file),
        "device_delivery_verified": False,
    }


@router.put("/professional/notifications/settings")
def set_delivery_settings(
    data: s.ChannelSettings, user=Depends(current_user), db=Depends(db_session)
):
    pref = db.scalar(
        select(m.NotificationPreference).where(
            m.NotificationPreference.user_id == user.id
        )
    )
    if not pref:
        pref = m.NotificationPreference(user_id=user.id)
        db.add(pref)
    for key, value in data.model_dump().items():
        setattr(pref, key, value)
    return data.model_dump()


@router.post("/professional/notifications/devices")
def register_device(
    data: s.TokenInput, user=Depends(current_user), db=Depends(db_session)
):
    existing = db.scalar(select(p.DeviceToken).where(p.DeviceToken.token == data.token))
    if existing and existing.user_id != user.id:
        raise HTTPException(
            409, "Token belongs to a different signed-in account; remove it there first"
        )
    if not existing:
        existing = p.DeviceToken(user_id=user.id, **data.model_dump())
        db.add(existing)
    existing.active = True
    db.flush()
    return {"id": existing.id, "active": True}


@router.delete("/professional/notifications/devices/{id}", status_code=204)
def remove_device(id: str, user=Depends(current_user), db=Depends(db_session)):
    record = db.get(p.DeviceToken, id)
    if not record or record.user_id != user.id:
        raise HTTPException(404)
    record.active = False


@router.get("/professional/notifications/jobs")
def user_jobs(
    user=Depends(current_user), db=Depends(db_session), page: int = Query(1, ge=1)
):
    return paginate(db, p.NotificationJob, [p.NotificationJob.user_id == user.id], page)


@router.get("/admin/professional/notifications")
def admin_jobs(
    user=Depends(administrator), db=Depends(db_session), page: int = Query(1, ge=1)
):
    result = paginate(db, p.NotificationJob, page=page)
    # General administrators see delivery health, never private reminder bodies or device tokens.
    result["items"] = [
        {
            k: v
            for k, v in record.items()
            if k not in ["payload", "user_id", "source_id", "dedupe_key", "lease_token"]
        }
        for record in result["items"]
    ]
    return result


@router.post("/admin/professional/notifications/{id}/retry")
def retry_notification(id: str, user=Depends(administrator), db=Depends(db_session)):
    record = db.get(p.NotificationJob, id)
    if not record:
        raise HTTPException(404)
    if record.status not in ["failed", "blocked"] or record.attempts >= 5:
        raise HTTPException(
            409,
            "Only known failures or blocked jobs can retry; uncertain delivery requires provider reconciliation",
        )
    record.status = "retry"
    record.due_at = m.now()
    audit(db, user, "retry_notification", id)
    return {"status": record.status}


@router.get("/internal/professional/notifications/tick")
async def notification_tick(request: Request, db=Depends(db_session)):
    configured = [
        v for v in [settings().indexing_worker_secret, settings().cron_secret] if v
    ]
    if not any(
        secrets.compare_digest(request.headers.get("authorization", ""), "Bearer " + v)
        for v in configured
    ):
        raise HTTPException(401)
    return await tick(db)


@router.get("/professional/updates/subscriptions")
def subscriptions(user=Depends(current_user), db=Depends(db_session)):
    return {
        "subjects": list(
            db.scalars(
                select(p.UpdateSubscription.subject).where(
                    p.UpdateSubscription.user_id == user.id
                )
            )
        )
    }


@router.put("/professional/updates/subscriptions")
def subscribe(
    data: s.SubscriptionInput, user=Depends(current_user), db=Depends(db_session)
):
    for record in db.scalars(
        select(p.UpdateSubscription).where(p.UpdateSubscription.user_id == user.id)
    ):
        db.delete(record)
    db.flush()
    for subject in set(data.subjects):
        db.add(p.UpdateSubscription(user_id=user.id, subject=subject))
    return data.model_dump()


@router.post("/admin/professional/updates/{id}/workflow")
def update_workflow(
    id: str, data: s.ReviewInput, user=Depends(administrator), db=Depends(db_session)
):
    record = db.scalar(
        select(m.RegulatoryUpdate).where(m.RegulatoryUpdate.id == id).with_for_update()
    )
    if not record:
        raise HTTPException(404)
    meta = dict(record.metadata_extra)
    if data.action == "review":
        if record.status != "draft" or not record.source_url:
            raise HTTPException(409, "Draft and source URL required")
        source_valid(
            {
                "title": record.title,
                "url": record.source_url,
                "verified_on": m.now().date().isoformat(),
            }
        )
        record.status = "review"
        meta["review_requested_by"] = user.id
    elif data.action == "approve":
        if record.status != "review":
            raise HTTPException(409, "Send draft for review first")
        if meta.get("review_requested_by") == user.id:
            raise HTTPException(403, "Different reviewer required")
        record.status = "approved"
        meta.update({"verified_on": m.now().date().isoformat(), "approved_by": user.id})
    elif data.action == "publish":
        if record.status != "approved" or not meta.get("verified_on"):
            raise HTTPException(409, "Approval required")
        record.status = "published"
        subject = meta.get("subject", "Corporate Tax")
        for uid in db.scalars(
            select(p.UpdateSubscription.user_id).where(
                p.UpdateSubscription.subject == subject
            )
        ):
            plan(
                db,
                uid,
                "update",
                id,
                m.now(),
                {
                    "title": record.title,
                    "body": "A reviewed regulatory update is available.",
                    "deep_link": f"/content/updates/{id}",
                },
                key="publish",
            )
    elif data.action in ["supersede", "archive"]:
        record.status = "superseded" if data.action == "supersede" else "archived"
    elif data.action == "flag_sources":
        from app.ai.models import DocumentVersion
        from app.ai.access import accessible_document

        for vid in data.knowledge_version_ids:
            version = db.get(DocumentVersion, vid)
            if not version:
                raise HTTPException(422, "Unknown knowledge version")
            accessible_document(db, version.document_id, user)
            if version.processing_status not in ["ready", "superseded"]:
                raise HTTPException(409, "Only processed sources can be flagged")
            version.processing_status = "superseded"
        meta["affected_knowledge_versions"] = data.knowledge_version_ids
        meta["learning_review_ids"] = data.learning_resource_ids
        meta["effective_on"] = str(data.effective_on) if data.effective_on else None
    record.metadata_extra = meta
    db.add(
        p.UpdateVersion(
            update_id=id, actor_id=user.id, action=data.action, snapshot=row(record)
        )
    )
    audit(db, user, "update_" + data.action, id)
    return row(record)


@router.post("/professional/webinars/{id}/register")
def webinar_register(id: str, user=Depends(current_user), db=Depends(db_session)):
    record = db.scalar(select(m.Webinar).where(m.Webinar.id == id).with_for_update())
    if not record or record.status != "published":
        raise HTTPException(404)
    meta = record.metadata_extra
    if (
        meta.get("registration_open", True) is not True
        or not record.starts_at
        or record.starts_at.replace(tzinfo=timezone.utc) <= m.now()
    ):
        raise HTTPException(409, "Registration closed")
    prior = db.scalar(
        select(p.WebinarRegistration).where(
            p.WebinarRegistration.webinar_id == id,
            p.WebinarRegistration.user_id == user.id,
        )
    )
    if prior and prior.status == "registered":
        return row(prior)
    active = db.scalar(
        select(func.count())
        .select_from(p.WebinarRegistration)
        .where(
            p.WebinarRegistration.webinar_id == id,
            p.WebinarRegistration.status == "registered",
        )
    )
    capacity = meta.get("capacity", 0)
    if capacity and active >= int(capacity):
        raise HTTPException(409, "Webinar capacity reached")
    if not prior:
        prior = p.WebinarRegistration(webinar_id=id, user_id=user.id)
        db.add(prior)
    prior.status = "registered"
    db.flush()
    when = record.starts_at.replace(tzinfo=timezone.utc) - timedelta(hours=1)
    if when > m.now():
        plan(
            db,
            user.id,
            "webinar",
            id,
            when,
            {
                "title": "Webinar reminder",
                "body": record.title,
                "deep_link": f"/content/webinars/{id}",
            },
        )
    audit(db, user, "webinar_register", id)
    return row(prior)


@router.get("/professional/webinars/{id}/registration")
def webinar_registration(id: str, user=Depends(current_user), db=Depends(db_session)):
    published(db, "webinars", id, user)
    record = db.scalar(
        select(p.WebinarRegistration).where(
            p.WebinarRegistration.webinar_id == id,
            p.WebinarRegistration.user_id == user.id,
        )
    )
    return row(record) if record else {"status": "not_registered"}


@router.delete("/professional/webinars/{id}/register", status_code=204)
def webinar_cancel(id: str, user=Depends(current_user), db=Depends(db_session)):
    record = db.scalar(
        select(p.WebinarRegistration).where(
            p.WebinarRegistration.webinar_id == id,
            p.WebinarRegistration.user_id == user.id,
        )
    )
    if record:
        record.status = "cancelled"
    for job in db.scalars(
        select(p.NotificationJob).where(
            p.NotificationJob.source_kind == "webinar",
            p.NotificationJob.source_id == id,
            p.NotificationJob.user_id == user.id,
            p.NotificationJob.status.in_(["planned", "blocked", "retry"]),
        )
    ):
        job.status = "cancelled"


@router.get("/professional/webinars/{id}/join")
def webinar_join(id: str, user=Depends(current_user), db=Depends(db_session)):
    webinar = published(db, "webinars", id, user)
    reg = webinar_registration(id, user, db)
    if reg["status"] != "registered":
        raise HTTPException(403, "Active registration required")
    return {
        "join_url": webinar.join_url,
        "recording_url": webinar.metadata_extra.get("recording_url"),
        "starts_at": webinar.starts_at,
        "timezone": webinar.metadata_extra.get("timezone", "Asia/Dubai"),
    }


@router.get("/professional/webinars/{id}/calendar")
def calendar_export(id: str, user=Depends(current_user), db=Depends(db_session)):
    event = published(db, "webinars", id, user)
    if not event.starts_at:
        raise HTTPException(409, "Event time unavailable")

    def escape(v):
        return (
            str(v)
            .replace("\\", "\\\\")
            .replace("\r", "")
            .replace("\n", "\\n")
            .replace(";", "\\;")
            .replace(",", "\\,")
        )

    start = event.starts_at.astimezone(timezone.utc)
    end = start + timedelta(
        minutes=int(event.metadata_extra.get("duration_minutes", 60))
    )
    text = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//DSBCA//Events//EN",
            "BEGIN:VEVENT",
            "UID:" + id + "@dsbca",
            "DTSTAMP:" + m.now().strftime("%Y%m%dT%H%M%SZ"),
            "DTSTART:" + start.strftime("%Y%m%dT%H%M%SZ"),
            "DTEND:" + end.strftime("%Y%m%dT%H%M%SZ"),
            "SUMMARY:" + escape(event.title),
            "DESCRIPTION:Sign in to DSBCA for authorized joining information.",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
    return Response(
        text,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="webinar.ics"'},
    )


@router.get("/admin/professional/webinars/{id}/registrations")
def attendees(id: str, user=Depends(administrator), db=Depends(db_session)):
    return paginate(db, p.WebinarRegistration, [p.WebinarRegistration.webinar_id == id])


@router.get("/admin/professional/webinars/{id}/attendees.csv")
def attendee_export(id: str, user=Depends(administrator), db=Depends(db_session)):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Registration ID", "Email", "Status", "Attended"])
    for registration, email in db.execute(
        select(p.WebinarRegistration, m.User.email)
        .join(m.User)
        .where(p.WebinarRegistration.webinar_id == id)
    ):
        writer.writerow(
            [
                registration.id,
                "'" + email if email[:1] in ["=", "+", "-", "@"] else email,
                registration.status,
                registration.attended,
            ]
        )
    audit(db, user, "export_webinar_attendees", id)
    return Response(
        out.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="attendees.csv"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/admin/professional/metrics")
def metrics(user=Depends(administrator), db=Depends(db_session)):
    return {
        "calculator_runs": db.scalar(select(func.count()).select_from(p.CalculatorRun)),
        "learning_progress_records": db.scalar(
            select(func.count()).select_from(p.LearningProgress)
        ),
        "upcoming_obligations": db.scalar(
            select(func.count())
            .select_from(p.ComplianceObligation)
            .where(p.ComplianceObligation.status == "pending")
        ),
        "notification_failures": db.scalar(
            select(func.count())
            .select_from(p.NotificationJob)
            .where(p.NotificationJob.status.in_(["failed", "blocked", "uncertain"]))
        ),
        "webinar_registrations": db.scalar(
            select(func.count())
            .select_from(p.WebinarRegistration)
            .where(p.WebinarRegistration.status == "registered")
        ),
    }


@router.post("/professional/ai/tools/execute")
def execute_tool(data: s.ToolInput, user=Depends(current_user), db=Depends(db_session)):
    from app.professional.tools import execute

    try:
        return execute(db, user, data.name, data.arguments, data.request_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/professional/ai/tools")
def tool_catalogue(user=Depends(current_user)):
    from app.professional.tools import CALCULATORS, SEARCH

    return {
        "read_only": list(CALCULATORS)
        + list(SEARCH)
        + ["get_authorized_company", "get_company_reminders", "get_user_deadlines"],
        "writes_enabled": False,
        "write_policy": "Open a populated application form and explicitly confirm changes; no model write tool is exposed.",
    }


@router.post("/professional/media", status_code=201, dependencies=[Depends(sensitive)])
async def upload_media(
    file: UploadFile = File(...),
    title: str = Form(...),
    company_id: str | None = Form(None),
    user=Depends(current_user),
    db=Depends(db_session),
):
    from app.ai.storage import storage
    from app.ai.ingestion import validate_pdf

    if company_id:
        owned(db, company_id, user)
    elif not set(roles(db, user.id)) & {"admin", "super_admin", "content_editor"}:
        raise HTTPException(403, "Learning uploads require editor access")
    data = await file.read(3000001)
    await file.close()
    if len(data) > 3000000:
        raise HTTPException(
            413, "Private attachment upload is limited to 3 MB on this endpoint"
        )
    mime = file.content_type
    extensions = {
        "application/pdf": {".pdf"},
        "image/png": {".png"},
        "image/jpeg": {".jpg", ".jpeg"},
        "image/webp": {".webp"},
    }
    from pathlib import Path

    if (
        mime in extensions
        and Path(file.filename or "").suffix.lower() not in extensions[mime]
    ):
        raise HTTPException(415, "Filename extension and content type must agree")
    if mime == "application/pdf":
        try:
            validate_pdf(data)
        except Exception:
            raise HTTPException(422, "Invalid PDF")
    elif mime in ["image/png", "image/jpeg", "image/webp"]:
        from PIL import Image

        try:
            with Image.open(io.BytesIO(data)) as image:
                if (
                    image.format
                    != {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}[
                        mime
                    ]
                ):
                    raise ValueError()
                if image.width * image.height > 20000000:
                    raise ValueError()
                image.verify()
        except Exception:
            raise HTTPException(422, "Invalid or oversized image")
    else:
        raise HTTPException(
            415, "Only PDF, PNG, JPEG or WebP attachments are supported"
        )
    key = f"professional/{uuid.uuid4()}/{hashlib.sha256(data).hexdigest()}"
    storage().put(key, data, mime)
    asset = p.MediaAsset(
        owner_id=user.id,
        company_id=company_id,
        storage_key=key,
        sha256=hashlib.sha256(data).hexdigest(),
        mime=mime,
        size=len(data),
        title=title[:240],
    )
    db.add(asset)
    db.flush()
    audit(db, user, "upload_private_asset", asset.id)
    return {"asset_id": asset.id, "sha256": asset.sha256}


@router.get("/professional/media/{id}/download")
def media_download(id: str, user=Depends(current_user), db=Depends(db_session)):
    from app.ai.storage import storage, S3PrivateStorage

    asset = db.get(p.MediaAsset, id)
    if not asset:
        raise HTTPException(404)
    if asset.company_id:
        owned(db, asset.company_id, user)
    elif asset.owner_id != user.id and not set(roles(db, user.id)) & {
        "admin",
        "super_admin",
        "content_editor",
    }:
        allowed = False
        for model in [m.Publication, m.Video, m.Article]:
            for content in db.scalars(select(model).where(model.status == "published")):
                if content.metadata_extra.get("asset_id") == id and (
                    not content.publish_at
                    or content.publish_at.replace(tzinfo=timezone.utc) <= m.now()
                ):
                    allowed = True
        for chapter in db.scalars(
            select(m.PublicationChapter).where(m.PublicationChapter.asset_id == id)
        ):
            parent = db.get(m.Publication, chapter.publication_id)
            if (
                parent
                and parent.status == "published"
                and (
                    not parent.publish_at
                    or parent.publish_at.replace(tzinfo=timezone.utc) <= m.now()
                )
            ):
                allowed = True
        if not allowed:
            raise HTTPException(404)
    store = storage()
    if isinstance(store, S3PrivateStorage):
        return {
            "url": store.download_url(asset.storage_key, asset.mime),
            "expires_in": 60,
        }
    # Authenticated bounded local download; production uses direct private object delivery.
    data = store.get(asset.storage_key, 3000000)
    if hashlib.sha256(data).hexdigest() != asset.sha256:
        raise HTTPException(409, "Asset hash mismatch")
    return Response(
        data,
        media_type=asset.mime,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/admin/professional/rule-templates")
def rule_templates(user=Depends(administrator)):
    from app.calculators.reference_rules import TEMPLATES

    return {
        "items": TEMPLATES,
        "publication": "Draft templates only; verify applicability, reference cases and second-review approval before use.",
    }


@router.post("/professional/companies/{id}/documents", status_code=201)
def new_company_document(
    id: str, data: s.DocumentChange, user=Depends(current_user), db=Depends(db_session)
):
    owned(db, id, user)
    if data.person_id:
        person = db.get(m.CompanyPerson, data.person_id)
        if not person or person.company_id != id:
            raise HTTPException(422, "Person belongs to another company")
    validate_company_asset(db, data.details, id)
    values = data.model_dump()
    values["details"] = protect(values["details"])
    record = m.CompanyDocument(company_id=id, **values)
    db.add(record)
    db.flush()
    schedule_document(db, record, user)
    audit(db, user, "create_document", record.id)
    return row(record)


@router.get("/professional/compliance-rules")
def available_compliance_rules(user=Depends(current_user), db=Depends(db_session)):
    records = list(
        db.scalars(
            select(p.RuleVersion).where(
                p.RuleVersion.category == "compliance",
                p.RuleVersion.status == "published",
            )
        )
    )
    return {"items": [rule_snapshot(r) for r in records]}


@router.post("/admin/professional/notifications/campaigns", status_code=201)
def campaign(
    data: s.CampaignInput, user=Depends(administrator), db=Depends(db_session)
):
    if not data.confirmed:
        raise HTTPException(409, "Explicit campaign confirmation required")
    if data.scheduled_at.tzinfo is None:
        raise HTTPException(422, "Schedule requires timezone offset")
    campaign_id = str(uuid.uuid4())
    count = 0
    for uid in db.scalars(
        select(p.UpdateSubscription.user_id).where(
            p.UpdateSubscription.subject == data.subject
        )
    ):
        plan(
            db,
            uid,
            "campaign",
            campaign_id,
            data.scheduled_at,
            {"title": data.title, "body": data.body, "deep_link": "/notifications"},
            key=campaign_id,
        )
        count += 1
    audit(db, user, "queue_campaign", campaign_id)
    return {
        "campaign_id": campaign_id,
        "planned_in_app_recipients": count,
        "delivery": "queued, not delivered",
    }


@router.put("/admin/professional/learning-paths/{id}")
def edit_path(id: str, data: s.PathInput, user=Depends(editor), db=Depends(db_session)):
    path = db.get(p.LearningPath, id)
    if not path:
        raise HTTPException(404)
    for key, value in data.model_dump(exclude={"items"}).items():
        setattr(path, key, value)
    for item in db.scalars(
        select(p.LearningPathItem).where(p.LearningPathItem.path_id == id)
    ):
        db.delete(item)
    db.flush()
    for i, item in enumerate(data.items):
        published(db, item.get("kind"), item.get("resource_id"), user)
        db.add(
            p.LearningPathItem(
                path_id=id,
                kind=item["kind"],
                resource_id=item["resource_id"],
                position=i + 1,
            )
        )
    audit(db, user, "edit_learning_path", id)
    return row(path)


@router.delete("/admin/professional/learning-paths/{id}", status_code=204)
def archive_path(id: str, user=Depends(editor), db=Depends(db_session)):
    path = db.get(p.LearningPath, id)
    if not path:
        raise HTTPException(404)
    path.status = "archived"
    audit(db, user, "archive_learning_path", id)


@router.put("/admin/professional/publications/{id}/chapter-order")
def reorder_chapters(
    id: str, data: s.ReorderInput, user=Depends(editor), db=Depends(db_session)
):
    if not db.get(m.Publication, id):
        raise HTTPException(404)
    chapters = list(
        db.scalars(
            select(m.PublicationChapter)
            .where(m.PublicationChapter.publication_id == id)
            .with_for_update()
        )
    )
    if len(set(data.chapter_ids)) != len(data.chapter_ids) or set(data.chapter_ids) != {
        c.id for c in chapters
    }:
        raise HTTPException(422, "Provide every chapter exactly once")
    by_id = {c.id: c for c in chapters}
    for i, chapter in enumerate(chapters):
        chapter.position = 100000 + i
    db.flush()
    for i, cid in enumerate(data.chapter_ids):
        by_id[cid].position = i + 1
    audit(db, user, "reorder_chapters", id)
    return {"chapter_ids": data.chapter_ids}


@router.get("/video-categories")
def video_categories(subject_id: str | None = None, db=Depends(db_session)):
    return paginate(
        db,
        m.VideoCategory,
        [m.VideoCategory.subject_id == subject_id] if subject_id else [],
        page_size=100,
    )


@router.get("/admin/professional/video-categories")
def admin_video_categories(user=Depends(editor), db=Depends(db_session)):
    return paginate(db, m.VideoCategory, page_size=100)


@router.post("/admin/professional/video-categories", status_code=201)
def create_video_category(
    data: s.VideoCategoryInput, user=Depends(editor), db=Depends(db_session)
):
    if not db.get(m.SubjectCategory, data.subject_id):
        raise HTTPException(422, "Subject category not found")
    record = m.VideoCategory(**data.model_dump())
    db.add(record)
    db.flush()
    audit(db, user, "create_video_category", record.id)
    return row(record)


@router.put("/admin/professional/video-categories/{id}")
def edit_video_category(
    id: str, data: s.VideoCategoryInput, user=Depends(editor), db=Depends(db_session)
):
    record = db.get(m.VideoCategory, id)
    if not record:
        raise HTTPException(404)
    if not db.get(m.SubjectCategory, data.subject_id):
        raise HTTPException(422, "Subject category not found")
    record.name, record.subject_id = data.name, data.subject_id
    audit(db, user, "edit_video_category", id)
    return row(record)


@router.delete("/admin/professional/video-categories/{id}", status_code=204)
def delete_video_category(id: str, user=Depends(editor), db=Depends(db_session)):
    record = db.get(m.VideoCategory, id)
    if not record:
        raise HTTPException(404)
    if db.scalar(select(m.Video.id).where(m.Video.video_category_id == id)):
        raise HTTPException(409, "Reassign videos before removing this category")
    db.delete(record)
    audit(db, user, "delete_video_category", id)


@router.get("/chapters/{id}")
def chapter_resource(id: str, user=Depends(optional_user), db=Depends(db_session)):
    record = published(db, "chapters", id, user)
    parent = db.get(m.Publication, record.publication_id)
    return {**row(record), "demo": parent.demo, "metadata_extra": {}}
