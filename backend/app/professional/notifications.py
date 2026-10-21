"""Persisted scheduling; in-app delivery is transactional, external acceptance is distinct."""

import uuid, secrets
from datetime import datetime, time, timedelta, timezone
from sqlalchemy import select, or_, and_
from app import models as m
from app.professional.models import NotificationJob, NotificationDelivery, DeviceToken
from app.core.config import settings


def plan(db, user_id, source_kind, source_id, due_at, payload, channels=None, key=""):
    for channel in channels or ["in_app"]:
        dedupe = (
            f"{source_kind}:{source_id}:{user_id}:{due_at.isoformat()}:{channel}:{key}"
        )
        prior = db.scalar(
            select(NotificationJob).where(NotificationJob.dedupe_key == dedupe)
        )
        if prior and prior.status == "cancelled":
            prior.status = "planned"
            prior.payload = payload
        if not prior:
            db.add(
                NotificationJob(
                    user_id=user_id,
                    source_kind=source_kind,
                    source_id=source_id,
                    channel=channel,
                    due_at=due_at,
                    payload=payload,
                    dedupe_key=dedupe,
                )
            )


def cancel_future(db, kind, source_id):
    for row in db.scalars(
        select(NotificationJob).where(
            NotificationJob.source_kind == kind,
            NotificationJob.source_id == source_id,
            NotificationJob.status.in_(["planned", "retry", "blocked"]),
        )
    ):
        row.status = "cancelled"


def schedule_document(db, document, user):
    cancel_future(db, "document", document.id)
    pref = db.scalar(
        select(m.ReminderPreference).where(m.ReminderPreference.user_id == user.id)
    )
    if document.status not in ["active", "needs_review"] or (pref and not pref.enabled):
        return
    days = pref.schedule if pref else [30, 7, 0]
    channels = pref.channels if pref else ["in_app"]
    template = db.scalar(
        select(m.AppSetting).where(m.AppSetting.key == "notification_template.renewal")
    )
    content = template.value if template and isinstance(template.value, dict) else {}
    title = (
        content.get("title")
        if isinstance(content.get("title"), str)
        else "Document renewal reminder"
    )
    body = (
        content.get("body")
        if isinstance(content.get("body"), str)
        else f"{document.title} expires on {document.expires_on.isoformat()}. Recorded expiry; no legal risk conclusion."
    )
    for day in days:
        # 09:00 Asia/Dubai = 05:00 UTC; persisted UTC timestamps, no client timer.
        due = datetime.combine(
            document.expires_on - timedelta(days=day), time(5), tzinfo=timezone.utc
        )
        if due < m.now() - timedelta(days=1):
            continue
        plan(
            db,
            user.id,
            "document",
            document.id,
            due,
            {
                "title": title[:180],
                "body": body[:2000],
                "deep_link": "/reminders",
                "company_id": document.company_id,
            },
            channels,
            key=str(document.expires_on),
        )


async def external(channel, job, db):
    import httpx

    cfg = settings()
    if channel == "email":
        if not cfg.resend_api_key or not cfg.notification_email_from:
            return "blocked", None, "EMAIL_NOT_CONFIGURED"
        user = db.get(m.User, job.user_id)
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": "Bearer " + cfg.resend_api_key,
                    "Idempotency-Key": job.id,
                },
                json={
                    "from": cfg.notification_email_from,
                    "to": [user.email],
                    "subject": "DSBCA notification",
                    "text": "You have a DSBCA notification. Sign in to view your private details.",
                },
            )
        if response.status_code in [200, 201]:
            return (
                "submitted",
                response.json().get("id"),
                "PROVIDER_ACCEPTED_NOT_DELIVERY_CONFIRMED",
            )
        if response.status_code == 429 or response.status_code >= 500:
            return "retry", None, "EMAIL_TRANSIENT"
        return "failed", None, "EMAIL_REJECTED"
    if channel == "push":
        tokens = list(
            db.scalars(
                select(DeviceToken).where(
                    DeviceToken.user_id == job.user_id, DeviceToken.active.is_(True)
                )
            )
        )
        if not cfg.fcm_service_account_file or not cfg.fcm_project_id:
            return "blocked", None, "PUSH_NOT_CONFIGURED"
        if not tokens:
            return "blocked", None, "NO_REGISTERED_DEVICE"
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        credentials = service_account.Credentials.from_service_account_file(
            cfg.fcm_service_account_file,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(Request())
        ids = []
        async with httpx.AsyncClient(timeout=15) as client:
            for token in tokens:
                response = await client.post(
                    f"https://fcm.googleapis.com/v1/projects/{cfg.fcm_project_id}/messages:send",
                    headers={"Authorization": "Bearer " + credentials.token},
                    json={
                        "message": {
                            "token": token.token,
                            "notification": {
                                "title": "DSBCA notification",
                                "body": "Sign in to view your reminder.",
                            },
                            "data": {
                                "job_id": job.id,
                                "route": job.payload.get("deep_link", "/notifications"),
                            },
                        }
                    },
                )
                if response.status_code == 200:
                    ids.append(response.json().get("name", "accepted"))
                elif "UNREGISTERED" in response.text:
                    token.active = False
                else:
                    return "uncertain", None, "PUSH_REVIEW_REQUIRED"
        return (
            ("submitted", ",".join(ids), "PROVIDER_ACCEPTED_NOT_DEVICE_VERIFIED")
            if ids
            else ("failed", None, "DEVICE_UNREGISTERED")
        )
    return "failed", None, "UNKNOWN_CHANNEL"


async def tick(db, adapter=None):
    row = db.scalar(
        select(NotificationJob)
        .where(
            or_(
                and_(
                    NotificationJob.status.in_(["planned", "retry"]),
                    NotificationJob.due_at <= m.now(),
                ),
                and_(
                    NotificationJob.status == "running",
                    NotificationJob.lease_until < m.now(),
                ),
            )
        )
        .order_by(NotificationJob.due_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not row:
        db.rollback()
        return {"status": "idle"}
    user = db.get(m.User, row.user_id)
    pref = db.scalar(
        select(m.NotificationPreference).where(
            m.NotificationPreference.user_id == row.user_id
        )
    )
    if (
        not user
        or user.status != "active"
        or (not pref and row.channel != "in_app")
        or (pref and not getattr(pref, row.channel, False))
    ):
        row.status = "skipped"
        db.commit()
        return {"status": "skipped"}
    if row.status == "running" and row.channel == "push":
        row.status = "uncertain"
        row.error_code = "LEASE_EXPIRED_REVIEW_PUSH"
        db.commit()
        return {"status": "uncertain"}
    if (
        row.status == "running"
        and row.channel == "email"
        and row.updated_at.replace(tzinfo=timezone.utc) < m.now() - timedelta(hours=1)
    ):
        row.status = "uncertain"
        row.error_code = "EMAIL_REPLAY_WINDOW_REVIEW"
        db.commit()
        return {"status": "uncertain"}
    if row.attempts >= 5:
        row.status = "failed"
        row.error_code = "RETRY_LIMIT"
        db.commit()
        return {"status": "failed"}
    if row.source_kind == "document":
        doc = db.get(m.CompanyDocument, row.source_id)
        company = db.get(m.Company, doc.company_id) if doc else None
        if (
            not doc
            or doc.status not in ["active", "needs_review"]
            or not company
            or company.owner_id != row.user_id
        ):
            row.status = "cancelled"
            db.commit()
            return {"status": "cancelled"}
    if row.source_kind == "obligation":
        from app.professional.models import ComplianceObligation

        obligation = db.get(ComplianceObligation, row.source_id)
        company = db.get(m.Company, obligation.company_id) if obligation else None
        if (
            not obligation
            or obligation.status != "pending"
            or not company
            or company.owner_id != row.user_id
        ):
            row.status = "cancelled"
            db.commit()
            return {"status": "cancelled"}
    if row.source_kind == "update":
        from app.professional.models import UpdateSubscription

        update = db.get(m.RegulatoryUpdate, row.source_id)
        subscription = db.scalar(
            select(UpdateSubscription.id).where(
                UpdateSubscription.user_id == row.user_id,
                UpdateSubscription.subject
                == (
                    update.metadata_extra.get("subject", "Corporate Tax")
                    if update
                    else ""
                ),
            )
        )
        if not update or update.status != "published" or not subscription:
            row.status = "cancelled"
            db.commit()
            return {"status": "cancelled"}
    if row.source_kind == "webinar":
        from app.professional.models import WebinarRegistration

        event = db.get(m.Webinar, row.source_id)
        registration = db.scalar(
            select(WebinarRegistration.id).where(
                WebinarRegistration.webinar_id == row.source_id,
                WebinarRegistration.user_id == row.user_id,
                WebinarRegistration.status == "registered",
            )
        )
        if not event or event.status != "published" or not registration:
            row.status = "cancelled"
            db.commit()
            return {"status": "cancelled"}
    if row.channel == "in_app":
        nid = str(uuid.uuid5(uuid.NAMESPACE_URL, "notification:" + row.id))
        if not db.get(m.Notification, nid):
            db.add(
                m.Notification(
                    id=nid,
                    title=row.payload["title"],
                    body=row.payload["body"],
                    category=row.source_kind,
                    deep_link=row.payload.get("deep_link", "/notifications"),
                    status="published",
                )
            )
            db.flush()
            db.add(m.NotificationRecipient(notification_id=nid, user_id=row.user_id))
        row.status = "delivered"
        row.attempts += 1
        db.add(
            NotificationDelivery(
                job_id=row.id,
                attempt=row.attempts,
                outcome="in_app_available",
                provider_id=nid,
            )
        )
        db.commit()
        return {
            "job_id": row.id,
            "status": "delivered",
            "meaning": "in-app record available; not email/device delivery",
        }
    row.status = "running"
    row.lease_token = secrets.token_hex(24)
    row.lease_until = m.now() + timedelta(seconds=120)
    row.attempts += 1
    lease = row.lease_token
    db.commit()
    try:
        outcome, receipt, error = await (adapter or external)(row.channel, row, db)
    except Exception:
        outcome, receipt, error = (
            ("uncertain", None, "PUSH_AMBIGUOUS_RESULT")
            if row.channel == "push"
            else ("retry", None, "EMAIL_TRANSIENT")
        )
    db.refresh(row, with_for_update=True)
    if row.lease_token != lease:
        return {"status": "stale"}
    row.status = outcome
    row.error_code = error
    row.lease_token = None
    row.lease_until = None
    if outcome == "retry":
        row.due_at = m.now() + timedelta(minutes=min(60, 2**row.attempts))
    db.add(
        NotificationDelivery(
            job_id=row.id, attempt=row.attempts, outcome=outcome, provider_id=receipt
        )
    )
    db.commit()
    return {"job_id": row.id, "status": outcome, "error_code": error}


def schedule_obligation(db, obligation, user):
    cancel_future(db, "obligation", obligation.id)
    pref = db.scalar(
        select(m.ReminderPreference).where(m.ReminderPreference.user_id == user.id)
    )
    if (
        obligation.status != "pending"
        or not obligation.due_on
        or (pref and not pref.enabled)
    ):
        return
    for day in pref.schedule if pref else [30, 7, 0]:
        when = datetime.combine(
            obligation.due_on - timedelta(days=day), time(5), tzinfo=timezone.utc
        )
        if when < m.now() - timedelta(days=1):
            continue
        plan(
            db,
            user.id,
            "obligation",
            obligation.id,
            when,
            {
                "title": obligation.title,
                "body": f"Due {obligation.due_on}; review the recorded basis and any extensions.",
                "deep_link": "/reminders",
            },
            pref.channels if pref else ["in_app"],
        )
