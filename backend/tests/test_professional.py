import asyncio, copy, json
from datetime import timedelta, date
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session
import pytest
from conftest import account
from test_workflows import make_admin
from app import models as m
from app.professional import models as p
from app.calculators.reference_rules import TEMPLATES
from app.professional.notifications import tick
from app.core.config import settings


@pytest.fixture
def professional(client, tmp_path, monkeypatch):
    a, _ = account(client)
    make_admin(client, a)
    b, _ = account(client, "reviewer@example.com")
    make_admin(client, b, "admin")
    u, _ = account(client, "reader@example.com")
    other, _ = account(client, "other@example.com")
    monkeypatch.setattr(settings(), "pdf_storage_backend", "local")
    monkeypatch.setattr(settings(), "pdf_local_root", str(tmp_path / "private"))
    return client, a, b, u, other


def rule(c, a, b, code):
    template = copy.deepcopy(next(x for x in TEMPLATES if x["code"] == code))
    response = c.post("/api/v1/admin/professional/rules", headers=a, json=template)
    assert response.status_code == 201, response.text
    rid = response.json()["id"]
    assert (
        c.post(
            f"/api/v1/admin/professional/rules/{rid}/publish", headers=b, json={}
        ).status_code
        == 409
    )
    r = c.post(f"/api/v1/admin/professional/rules/{rid}/validate", headers=a, json={})
    assert r.status_code == 200, r.text
    assert (
        c.post(
            f"/api/v1/admin/professional/rules/{rid}/publish", headers=a, json={}
        ).status_code
        == 403
    )
    r = c.post(f"/api/v1/admin/professional/rules/{rid}/publish", headers=b, json={})
    assert r.status_code == 200, r.text
    return rid


def company(c, u):
    return c.post(
        "/api/v1/companies",
        headers=u,
        json={
            "name": "Private company",
            "profile_data": {"zone": "Mainland", "entity_type": "LLC"},
        },
    ).json()["id"]


def test_calculation_rules_save_history_and_ownership(professional):
    c, a, b, u, other = professional
    inputs = {
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "accounting_profit": "900000",
    }
    restricted = c.post(
        "/api/v1/professional/calculators/corporate_tax/calculate",
        headers=u,
        json={"inputs": inputs},
    ).json()
    assert restricted["status"] == "restricted"
    rid = rule(c, a, b, "corporate_tax")
    r = c.post(
        "/api/v1/professional/calculators/corporate_tax/calculate",
        headers=u,
        json={"inputs": inputs, "save": True, "rule_id": rid},
    )
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["results"]["corporate_tax"] == "47250.00"
    saved = c.get(
        "/api/v1/professional/calculations/" + result["run_id"], headers=u
    ).json()
    assert saved["rule_snapshot"]["id"] == rid
    assert (
        c.get(
            "/api/v1/professional/calculations/" + result["run_id"], headers=other
        ).status_code
        == 404
    )
    assert (
        c.get(
            "/api/v1/professional/calculations/" + result["run_id"] + "/export",
            headers=u,
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/v1/professional/calculators/corporate_tax/calculate",
            headers=u,
            json={"inputs": {**inputs, "period_end": "2027-01-01"}},
        ).json()["status"]
        == "restricted"
    )


def test_all_reference_templates_validate_and_publish(professional):
    c, a, b, _, _ = professional
    for template in TEMPLATES:
        rule(c, a, b, template["code"])


def test_document_renewal_and_notification_idempotency(professional):
    c, a, b, u, other = professional
    cid = company(c, u)
    body = {
        "title": "Trade Licence",
        "category": "Trade Licence",
        "expires_on": str(date.today() + timedelta(days=30)),
        "details": {"issue_date": "2025-01-01"},
    }
    created = c.post(
        f"/api/v1/professional/companies/{cid}/documents", headers=u, json=body
    )
    assert created.status_code == 201, created.text
    doc = created.json()
    assert (
        c.get(
            f"/api/v1/professional/companies/{cid}/compliance", headers=other
        ).status_code
        == 404
    )
    with Session(c.engine, expire_on_commit=False) as db:
        jobs = list(db.scalars(select(p.NotificationJob)))
        assert len(jobs) == 3
        for j in jobs:
            j.due_at = m.now() - timedelta(seconds=1)
        db.commit()
        for _ in jobs:
            assert asyncio.run(tick(db))["status"] == "delivered"
        assert asyncio.run(tick(db))["status"] == "idle"
        assert db.scalar(select(func.count()).select_from(m.NotificationRecipient)) == 3
    renewed = c.put(
        f'/api/v1/professional/companies/{cid}/documents/{doc["id"]}',
        headers=u,
        json={**body, "expires_on": str(date.today() + timedelta(days=365))},
    )
    assert renewed.status_code == 200
    view = c.get(f"/api/v1/professional/companies/{cid}/compliance", headers=u).json()
    assert (
        view["documents"][0]["expiry_status"] == "upcoming"
        and view["history"][0]["action"] == "renew"
    )
    settings_response = c.put(
        "/api/v1/professional/reminder-settings",
        headers=u,
        json={"days": [90, 60, 30, 15, 7, 0], "channels": ["in_app"], "enabled": False},
    )
    assert settings_response.status_code == 200
    with Session(c.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(p.NotificationJob)
                .where(p.NotificationJob.status == "planned")
            )
            == 0
        )


def test_supported_deadlines_require_confirmed_facts(professional):
    c, a, b, u, other = professional
    cid = company(c, u)
    rid = rule(c, a, b, "ct_filing")
    body = {
        "title": "CT filing",
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
        "rule_id": rid,
    }
    unknown = c.post(
        f"/api/v1/professional/companies/{cid}/obligations", headers=u, json=body
    ).json()
    assert unknown["due_on"] is None and unknown["status"] == "awaiting_confirmation"
    confirmed = c.post(
        f"/api/v1/professional/companies/{cid}/obligations",
        headers=u,
        json={
            **body,
            "facts_confirmed": True,
            "facts": {"registered": True, "exceptions": False},
        },
    ).json()
    assert (
        confirmed["due_on"] == "2026-09-30" and confirmed["basis"]["rule"]["id"] == rid
    )
    assert (
        c.patch(
            f'/api/v1/professional/companies/{cid}/obligations/{confirmed["id"]}',
            headers=other,
            json={"status": "completed"},
        ).status_code
        == 404
    )


def test_learning_progress_bookmarks_chapters_paths(professional):
    c, a, b, u, _ = professional
    video = c.post(
        "/api/v1/admin/content/videos",
        headers=a,
        json={
            "title": "Player demonstration",
            "status": "published",
            "media_url": "https://flutter.github.io/assets-for-api-docs/assets/videos/bee.mp4",
            "duration_seconds": 10,
        },
    ).json()
    vid = video["id"]
    assert (
        c.put(
            f"/api/v1/professional/learning/videos/{vid}/progress",
            headers=u,
            json={"position": 5},
        ).status_code
        == 200
    )
    assert (
        c.get(f"/api/v1/professional/learning/videos/{vid}/state", headers=u).json()[
            "progress"
        ]["position"]
        == 5
    )
    c.put(
        f"/api/v1/professional/learning/videos/{vid}/bookmark",
        headers=u,
        json={"saved": True},
    )
    assert (
        c.get("/api/v1/professional/learning/library", headers=u).json()["total"] == 1
    )
    publication = c.post(
        "/api/v1/admin/content/publications",
        headers=a,
        json={"title": "Fictional checklist", "status": "published"},
    ).json()
    chapter = c.post(
        "/api/v1/admin/content/chapters",
        headers=a,
        json={
            "publication_id": publication["id"],
            "title": "Review records",
            "position": 1,
            "body": "Fictional chapter body",
        },
    ).json()
    assert (
        c.put(
            f'/api/v1/professional/learning/chapters/{chapter["id"]}/progress',
            headers=u,
            json={"completed": True},
        ).status_code
        == 200
    )
    path = c.post(
        "/api/v1/admin/professional/learning-paths",
        headers=a,
        json={
            "title": "Fundamentals",
            "subject": "Corporate Tax",
            "status": "published",
            "items": [{"kind": "videos", "resource_id": vid}],
        },
    ).json()
    c.post(
        "/api/v1/professional/learning/paths/" + path["id"] + "/enroll",
        headers=u,
        json={},
    )
    c.put(
        f"/api/v1/professional/learning/videos/{vid}/progress",
        headers=u,
        json={"position": 10, "completed": True},
    )
    assert (
        c.get("/api/v1/professional/learning/paths", headers=u).json()["items"][0][
            "progress_percent"
        ]
        == 100
    )


def test_update_review_targeted_notification_and_no_bypass(professional):
    c, a, b, u, _ = professional
    assert (
        c.post(
            "/api/v1/admin/updates",
            headers=a,
            json={"title": "Unreviewed", "status": "published"},
        ).status_code
        == 409
    )
    update = c.post(
        "/api/v1/admin/updates",
        headers=a,
        json={
            "title": "Reviewed reference update",
            "source_url": "https://tax.gov.ae/",
            "metadata_extra": {"subject": "VAT"},
        },
    ).json()
    uid = update["id"]
    c.put(
        "/api/v1/professional/updates/subscriptions",
        headers=u,
        json={"subjects": ["VAT"]},
    )
    assert (
        c.post(
            f"/api/v1/admin/professional/updates/{uid}/workflow",
            headers=a,
            json={"action": "publish"},
        ).status_code
        == 409
    )
    assert (
        c.post(
            f"/api/v1/admin/professional/updates/{uid}/workflow",
            headers=a,
            json={"action": "review"},
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/v1/admin/professional/updates/{uid}/workflow",
            headers=a,
            json={"action": "approve"},
        ).status_code
        == 403
    )
    assert (
        c.post(
            f"/api/v1/admin/professional/updates/{uid}/workflow",
            headers=b,
            json={"action": "approve"},
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/v1/admin/professional/updates/{uid}/workflow",
            headers=b,
            json={"action": "publish"},
        ).status_code
        == 200
    )
    with Session(c.engine, expire_on_commit=False) as db:
        assert asyncio.run(tick(db))["status"] == "delivered"
    assert c.get("/api/v1/notifications", headers=u).json()["total"] == 1


def test_webinar_capacity_private_join_cancellation_timezone(professional):
    c, a, b, u, other = professional
    starts = (m.now() + timedelta(days=3)).isoformat()
    event = c.post(
        "/api/v1/admin/content/webinars",
        headers=a,
        json={
            "title": "Training event",
            "status": "published",
            "starts_at": starts,
            "join_url": "https://example.com/private-room",
            "metadata_extra": {
                "capacity": 1,
                "timezone": "Asia/Dubai",
                "presenter": "Test presenter",
            },
        },
    ).json()
    wid = event["id"]
    assert c.get("/api/v1/webinars/" + wid).json()["join_url"] is None
    assert (
        c.get(f"/api/v1/professional/webinars/{wid}/join", headers=u).status_code == 403
    )
    assert (
        c.post(
            f"/api/v1/professional/webinars/{wid}/register", headers=u, json={}
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/v1/professional/webinars/{wid}/register", headers=u, json={}
        ).status_code
        == 200
    )
    assert (
        c.post(
            f"/api/v1/professional/webinars/{wid}/register", headers=other, json={}
        ).status_code
        == 409
    )
    assert (
        c.get(f"/api/v1/professional/webinars/{wid}/join", headers=u)
        .json()["join_url"]
        .endswith("private-room")
    )
    calendar = c.get(f"/api/v1/professional/webinars/{wid}/calendar", headers=u).text
    assert "DTSTART:" in calendar and "private-room" not in calendar
    c.delete(f"/api/v1/professional/webinars/{wid}/register", headers=u)
    assert (
        c.post(
            f"/api/v1/professional/webinars/{wid}/register", headers=other, json={}
        ).status_code
        == 200
    )


def test_ai_tools_match_engine_and_cannot_read_foreign_company_or_write(professional):
    c, a, b, u, other = professional
    cid = company(c, u)
    rule(c, a, b, "vat")
    request = {
        "name": "calculate_vat",
        "arguments": {
            "inputs": {
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "amount": "10000",
                "inclusive": False,
                "treatment": "standard",
            }
        },
        "request_id": "typed_tool_request_001",
    }
    result = c.post(
        "/api/v1/professional/ai/tools/execute", headers=u, json=request
    ).json()
    assert (
        result["result"]["results"]["output_vat"] == "500.00"
        and result["deterministic"]
    )
    assert (
        c.post(
            "/api/v1/professional/ai/tools/execute",
            headers=other,
            json={
                "name": "get_company_reminders",
                "arguments": {"company_id": cid},
                "request_id": "foreign_company_request",
            },
        ).status_code
        == 404
    )
    assert (
        c.post(
            "/api/v1/professional/ai/tools/execute",
            headers=u,
            json={
                "name": "renew_document",
                "arguments": {},
                "request_id": "unconfirmed_write_01",
            },
        ).status_code
        == 422
    )
    conversation = c.post("/api/v1/ai/conversations", headers=u, json={}).json()["id"]
    answer = c.post(
        "/api/v1/ai/chat",
        headers=u,
        json={
            "conversation_id": conversation,
            "request_id": "chat_tool_request_001",
            "question": "Calculate VAT on the explicitly supplied inputs",
            "application_tool": request,
        },
    ).json()
    assert (
        answer["status"] == "completed"
        and answer["metadata"]["application_result"]["result"]["results"]["output_vat"]
        == "500.00"
    )
    assert "500.00" in answer["text"] and answer["citations"] == []


def test_private_company_fields_encrypted_and_media_owner_scoped(professional):
    from test_ai import PDF

    c, a, b, u, other = professional
    created = c.post(
        "/api/v1/companies",
        headers=u,
        json={
            "name": "Encryption example",
            "profile_data": {
                "contact_email": "private@example.com",
                "trade_licence_number": "LICENSE-PRIVATE-781",
            },
        },
    ).json()
    cid = created["id"]
    assert created["profile_data"]["contact_email"] == "private@example.com"
    with Session(c.engine) as db:
        stored = db.get(m.Company, cid)
        assert (
            "_encrypted_v1" in stored.profile_data
            and "private@example.com" not in json.dumps(stored.profile_data)
        )
    upload = c.post(
        "/api/v1/professional/media",
        headers=u,
        data={"title": "Private evidence", "company_id": cid},
        files={"file": ("evidence.pdf", PDF.read_bytes(), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    aid = upload.json()["asset_id"]
    assert (
        c.get(f"/api/v1/professional/media/{aid}/download", headers=u).content
        == PDF.read_bytes()
    )
    assert (
        c.get(f"/api/v1/professional/media/{aid}/download", headers=other).status_code
        == 404
    )
    assert (
        c.get(f"/api/v1/professional/media/{aid}/download", headers=a).status_code
        == 404
    )


def test_notification_preference_retry_and_device_removal(professional):
    c, a, b, u, other = professional
    c.put(
        "/api/v1/professional/notifications/settings",
        headers=u,
        json={"in_app": False, "email": True, "push": True},
    )
    uid = c.get("/api/v1/auth/me", headers=u).json()["id"]
    with Session(c.engine, expire_on_commit=False) as db:
        from app.professional.notifications import plan

        plan(
            db,
            uid,
            "test",
            "test-source",
            m.now() - timedelta(seconds=1),
            {"title": "Test", "body": "Test", "deep_link": "/notifications"},
            channels=["in_app", "email"],
        )
        db.commit()
        assert asyncio.run(tick(db))["status"] == "skipped"
        email_job = db.scalar(
            select(p.NotificationJob).where(p.NotificationJob.channel == "email")
        )

        async def fail(channel, job, session):
            return "retry", None, "EMAIL_TRANSIENT"

        assert asyncio.run(tick(db, adapter=fail))["status"] == "retry"
        email_job.due_at = m.now() - timedelta(seconds=1)
        db.commit()

        async def accepted(channel, job, session):
            return (
                "submitted",
                "provider-receipt",
                "PROVIDER_ACCEPTED_NOT_DELIVERY_CONFIRMED",
            )

        assert asyncio.run(tick(db, adapter=accepted))["status"] == "submitted"
        assert asyncio.run(tick(db, adapter=accepted))["status"] == "idle"
        assert (
            db.scalar(
                select(func.count())
                .select_from(p.NotificationDelivery)
                .where(p.NotificationDelivery.job_id == email_job.id)
            )
            == 2
        )
    device = c.post(
        "/api/v1/professional/notifications/devices",
        headers=u,
        json={"token": "fixture-device-token-1234567890", "platform": "android"},
    ).json()
    assert (
        c.delete(
            "/api/v1/professional/notifications/devices/" + device["id"], headers=other
        ).status_code
        == 404
    )
    assert (
        c.delete(
            "/api/v1/professional/notifications/devices/" + device["id"], headers=u
        ).status_code
        == 204
    )
    with Session(c.engine) as db:
        assert not db.get(p.DeviceToken, device["id"]).active


def test_scheduled_private_learning_and_chapter_access(professional):
    c, a, b, u, _ = professional
    pub = c.post(
        "/api/v1/admin/content/publications",
        headers=a,
        json={
            "title": "Member-only manual",
            "status": "published",
            "visibility": "authenticated",
        },
    ).json()
    c.post(
        "/api/v1/admin/content/chapters",
        headers=a,
        json={
            "publication_id": pub["id"],
            "title": "Private chapter",
            "position": 1,
            "body": "Members-only learning text",
        },
    )
    assert (
        c.get(
            "/api/v1/chapters/"
            + c.get(
                "/api/v1/publications/" + pub["id"] + "/chapters", headers=u
            ).json()["items"][0]["id"]
        ).status_code
        == 404
    )
    assert c.get("/api/v1/publications/" + pub["id"]).status_code == 404
    assert c.get("/api/v1/publications/" + pub["id"] + "/chapters").status_code == 404
    assert (
        c.get("/api/v1/publications/" + pub["id"] + "/chapters", headers=u).status_code
        == 200
    )
    future = c.post(
        "/api/v1/admin/content/videos",
        headers=a,
        json={
            "title": "Scheduled lesson",
            "status": "published",
            "publish_at": (m.now() + timedelta(days=1)).isoformat(),
        },
    ).json()
    assert c.get("/api/v1/videos/" + future["id"], headers=u).status_code == 404
    assert all(
        x["id"] != future["id"]
        for x in c.get("/api/v1/videos", headers=u).json()["items"]
    )


def test_video_categories_and_scheduled_asset_authorization(professional):
    from test_ai import PDF

    c, a, b, u, _ = professional
    subject = c.post(
        "/api/v1/admin/content/categories", headers=a, json={"name": "IFRS"}
    ).json()
    category = c.post(
        "/api/v1/admin/professional/video-categories",
        headers=a,
        json={"name": "Leases", "subject_id": subject["id"]},
    )
    assert category.status_code == 201, category.text
    category = category.json()
    video = c.post(
        "/api/v1/admin/content/videos",
        headers=a,
        json={
            "title": "Lease lesson",
            "status": "published",
            "category_id": subject["id"],
            "video_category_id": category["id"],
        },
    ).json()
    assert (
        c.get("/api/v1/videos", params={"video_category_id": category["id"]}).json()[
            "items"
        ][0]["id"]
        == video["id"]
    )
    assert (
        c.delete(
            "/api/v1/admin/professional/video-categories/" + category["id"], headers=a
        ).status_code
        == 409
    )
    asset = c.post(
        "/api/v1/professional/media",
        headers=a,
        data={"title": "Scheduled chapter"},
        files={"file": ("chapter.pdf", PDF.read_bytes(), "application/pdf")},
    ).json()["asset_id"]
    publication = c.post(
        "/api/v1/admin/content/publications",
        headers=a,
        json={
            "title": "Scheduled manual",
            "status": "published",
            "publish_at": (m.now() + timedelta(days=1)).isoformat(),
        },
    ).json()
    c.post(
        "/api/v1/admin/content/chapters",
        headers=a,
        json={
            "publication_id": publication["id"],
            "title": "Future evidence",
            "position": 1,
            "asset_id": asset,
        },
    )
    assert (
        c.get(
            "/api/v1/professional/media/" + asset + "/download", headers=u
        ).status_code
        == 404
    )


def test_unsubscribe_cancels_queued_update_and_guest_math(professional):
    c, a, b, u, _ = professional
    c.put(
        "/api/v1/professional/updates/subscriptions",
        headers=u,
        json={"subjects": ["VAT"]},
    )
    update = c.post(
        "/api/v1/admin/updates",
        headers=a,
        json={
            "title": "Test reviewed update",
            "source_url": "https://tax.gov.ae/",
            "metadata_extra": {"subject": "VAT"},
        },
    ).json()
    for action, actor in [("review", a), ("approve", b), ("publish", b)]:
        assert (
            c.post(
                "/api/v1/admin/professional/updates/" + update["id"] + "/workflow",
                headers=actor,
                json={"action": action},
            ).status_code
            == 200
        )
    c.put(
        "/api/v1/professional/updates/subscriptions", headers=u, json={"subjects": []}
    )
    with Session(c.engine, expire_on_commit=False) as db:
        assert asyncio.run(tick(db))["status"] == "cancelled"
    assert c.get("/api/v1/notifications", headers=u).json()["total"] == 0
    result = c.post(
        "/api/v1/professional/calculators/npv/calculate",
        json={"inputs": {"discount_rate": "0", "cashflows": ["-100", "110"]}},
    )
    assert result.status_code == 200, result.text
    assert (
        c.post(
            "/api/v1/professional/calculators/npv/calculate",
            json={
                "inputs": {"discount_rate": "0", "cashflows": ["-100", "110"]},
                "save": True,
            },
        ).status_code
        == 401
    )
