import io
import logging
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.ai.chat import validate_citations
from app.ai.schemas import GroundedAnswer, Claim
from app.ai.ingestion import validate_pdf
from app.core.operations import OperationsMiddleware
from conftest import account
from test_professional import professional


@pytest.mark.parametrize(
    "claim",
    [
        "The exemption applies to all entities.",
        "The exemption does not apply to qualifying entities.",
        "The exemption applies without conditions.",
        "The exemption applies",
    ],
)
def test_real_quote_cannot_support_reversed_or_unqualified_claim(claim):
    quote = "The exemption applies only to qualifying entities meeting all listed conditions."
    answer = GroundedAnswer(
        claims=[Claim(text=claim, evidence_ids=["source"], supporting_quotes=[quote])],
        missing_information=[],
        limitations=[],
    )
    with pytest.raises(ValueError, match="UNVERIFIED_PARAPHRASE"):
        validate_citations(answer, [{"id": "source", "passage": quote}])


def test_exact_excerpt_retains_conditions():
    quote = "The exemption applies only to qualifying entities meeting all listed conditions."
    answer = GroundedAnswer(
        claims=[Claim(text=quote, evidence_ids=["source"], supporting_quotes=[quote])],
        missing_information=[],
        limitations=[],
    )
    assert (
        validate_citations(answer, [{"id": "source", "passage": quote}])[0]["id"]
        == "source"
    )


def test_request_envelope_and_failure_redaction(caplog):
    app = FastAPI()
    app.add_middleware(OperationsMiddleware, max_body_bytes=100)

    @app.get("/failure")
    def failure():
        raise RuntimeError("NEVER_LOG_PRIVATE_SECRET")

    with caplog.at_level(logging.INFO, logger="dsbca.operations"), TestClient(
        app
    ) as client:
        response = client.get(
            "/failure?password=NEVER_LOG_PRIVATE_SECRET",
            headers={"X-Request-ID": "not-valid"},
        )
        assert response.status_code == 500
        assert len(response.headers["x-request-id"]) == 32
        assert response.headers["cache-control"] == "no-store"
        assert "NEVER_LOG_PRIVATE_SECRET" not in response.text
        assert "NEVER_LOG_PRIVATE_SECRET" not in caplog.text
        assert client.post("/unknown", content="x" * 101).status_code == 413


def test_health_headers_cors_and_profile_persistence(client):
    response = client.get("/api/v1/health")
    assert response.json()["phase"] == 4
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    headers, _ = account(client)
    assert (
        client.patch(
            "/api/v1/users/me", headers=headers, json={"name": "Updated QA name"}
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/auth/me", headers=headers).json()["name"]
        == "Updated QA name"
    )
    response = client.options(
        "/api/v1/users/me",
        headers={
            "Origin": "https://untrusted.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_page_level_pdf_action_rejected():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, TextStringObject

    writer = PdfWriter()
    page = writer.add_blank_page(100, 100)
    page[NameObject("/AA")] = DictionaryObject(
        {
            NameObject("/O"): DictionaryObject(
                {
                    NameObject("/S"): NameObject("/JavaScript"),
                    NameObject("/JS"): TextStringObject('app.alert("untrusted")'),
                }
            )
        }
    )
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(ValueError, match="ACTIVE_PDF_REJECTED"):
        validate_pdf(stream.getvalue())


def test_dashboard_uses_owner_document_deadline_and_no_foreign_data(client):
    from datetime import date, timedelta
    from test_professional import company

    a, _ = account(client)
    b, _ = account(client, "other-owner@example.com")
    cid = company(client, a)
    document = client.post(
        f"/api/v1/professional/companies/{cid}/documents",
        headers=a,
        json={
            "title": "QA licence",
            "category": "Trade Licence",
            "expires_on": str(date.today() + timedelta(days=10)),
        },
    )
    assert document.status_code == 201, document.text
    assert (
        client.get("/api/v1/dashboard", headers=a).json()["next_deadline"]["title"]
        == "QA licence"
    )
    assert client.get("/api/v1/dashboard", headers=b).json()["next_deadline"] is None


def test_declared_image_mime_and_extension_must_match(professional):
    from PIL import Image

    client, a, b, u, _ = professional
    from test_professional import company

    cid = company(client, u)
    stream = io.BytesIO()
    Image.new("RGB", (1, 1)).save(stream, format="PNG")
    for name, mime, status in [
        ("image.webp", "image/webp", 422),
        ("image.exe", "image/png", 415),
    ]:
        response = client.post(
            "/api/v1/professional/media",
            headers=u,
            data={"title": "QA image", "company_id": cid},
            files={"file": (name, stream.getvalue(), mime)},
        )
        assert response.status_code == status, response.text


@pytest.mark.parametrize("kind", ["videos", "publications", "articles", "webinars"])
def test_admin_content_round_trip_and_user_visibility(professional, kind):
    from datetime import timedelta
    from app import models as m

    client, admin, reviewer, reader, other = professional
    payload = {
        "title": "QA cross-app " + kind,
        "body": "Fictional QA record",
        "status": "draft",
        "demo": True,
    }
    if kind == "webinars":
        payload["starts_at"] = (m.now() + timedelta(days=3)).isoformat()
    result = client.post("/api/v1/admin/content/" + kind, headers=admin, json=payload)
    assert result.status_code == 201, result.text
    rid = result.json()["id"]
    assert client.get("/api/v1/" + kind + "/" + rid, headers=reader).status_code == 404
    assert (
        client.put(
            "/api/v1/admin/content/" + kind + "/" + rid,
            headers=other,
            json={**payload, "status": "published"},
        ).status_code
        == 403
    )
    result = client.put(
        "/api/v1/admin/content/" + kind + "/" + rid,
        headers=admin,
        json={**payload, "title": "Edited QA " + kind, "status": "published"},
    )
    assert result.status_code == 200, result.text
    assert (
        client.get("/api/v1/" + kind + "/" + rid, headers=reader).json()["title"]
        == "Edited QA " + kind
    )
    assert (
        client.get(
            "/api/v1/admin/content/" + kind,
            headers=admin,
            params={"q": "Edited QA", "page": 1, "page_size": 1},
        ).json()["items"][0]["id"]
        == rid
    )
    assert (
        client.delete(
            "/api/v1/admin/content/" + kind + "/" + rid, headers=admin
        ).status_code
        == 204
    )
    assert client.get("/api/v1/" + kind + "/" + rid, headers=reader).status_code == 404
    audit = client.get("/api/v1/admin/audit-logs", headers=admin).json()["items"]
    assert any(row["resource_id"] == rid for row in audit)


@pytest.mark.parametrize(
    "query", ["sslmode=disable", "sslmode=require", "sslmode=require&sslmode=disable"]
)
def test_hosted_database_fails_closed_without_verified_tls(monkeypatch, query):
    from types import SimpleNamespace
    from app.core import database

    database.engine.cache_clear()
    monkeypatch.setattr(
        database,
        "settings",
        lambda: SimpleNamespace(
            app_env="production",
            database_url="postgresql+psycopg://qa@localhost/qa?" + query,
        ),
    )
    try:
        with pytest.raises(ValueError):
            database.engine()
    finally:
        database.engine.cache_clear()


from test_ai import ai_setup


def test_total_chat_timeout_preserves_question(ai_setup, monkeypatch):
    import asyncio
    from unittest.mock import patch
    from test_ai import FixtureChat, upload, index, approve, ask
    from app.core.config import settings

    client, admin, reader, _ = ai_setup
    uploaded, _ = upload(client, admin)
    index(client)
    approve(client, admin, uploaded)
    monkeypatch.setattr(settings(), "ai_total_request_timeout", 0.02)

    class Slow(FixtureChat):
        async def generate_answer(self, *args):
            await asyncio.sleep(0.2)
            return await super().generate_answer(*args)

    with patch("app.ai.chat.chat_provider", return_value=Slow()):
        result, request = ask(client, reader)
    assert (
        result["status"] == "failed"
        and result["metadata"]["error_code"] == "request_timeout"
    )
    messages = client.get(
        "/api/v1/ai/conversations/" + request["conversation_id"] + "/messages",
        headers=reader,
    ).json()["items"]
    assert any(
        x["role"] == "user" and x["text"] == request["question"] for x in messages
    )


def test_superseded_rule_cannot_be_republished(professional):
    from test_professional import rule

    client, author, reviewer, _, _ = professional
    rid = rule(client, author, reviewer, "vat")
    base = "/api/v1/admin/professional/rules/" + rid
    assert client.post(base + "/validate", headers=author, json={}).status_code == 409
    assert (
        client.post(base + "/supersede", headers=reviewer, json={}).status_code == 200
    )
    assert client.post(base + "/publish", headers=reviewer, json={}).status_code == 409
    assert (
        client.post(base + "/supersede", headers=reviewer, json={}).status_code == 409
    )


@pytest.mark.parametrize("field", ["reset_delivery_url", "s3_endpoint_url"])
def test_hosted_secret_and_file_delivery_requires_https(monkeypatch, field):
    from app.core import config

    cfg = config.Settings(
        app_env="production",
        cors_allowed_origins=["https://qa.example"],
        data_encryption_key="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        jwt_secret_key="test-only-secret-key-with-at-least-32-characters",
        pdf_storage_backend="s3",
        ai_vector_backend="pgvector",
    )
    setattr(cfg, field, "http://insecure.example")
    config.settings.cache_clear()
    monkeypatch.setattr(config, "Settings", lambda: cfg)
    try:
        with pytest.raises(ValueError, match="HTTPS"):
            config.settings()
    finally:
        config.settings.cache_clear()


def test_saved_renewal_template_is_used_for_new_jobs(professional):
    from datetime import timedelta
    from app import models as m
    from test_professional import company

    client, admin, _, reader, _ = professional
    assert (
        client.put(
            "/api/v1/admin/settings",
            headers=admin,
            json={
                "key": "notification_template.renewal",
                "value": {
                    "title": "QA renewal title",
                    "body": "Review recorded expiry in your private workspace.",
                },
            },
        ).status_code
        == 200
    )
    cid = company(client, reader)
    doc = client.post(
        f"/api/v1/professional/companies/{cid}/documents",
        headers=reader,
        json={
            "title": "QA licence",
            "category": "Trade Licence",
            "expires_on": str(m.now().date() + timedelta(days=30)),
        },
    ).json()
    jobs = client.get("/api/v1/professional/notifications/jobs", headers=reader).json()[
        "items"
    ]
    assert any(
        j["source_id"] == doc["id"] and j["payload"]["title"] == "QA renewal title"
        for j in jobs
    )


def test_vercel_cannot_silently_use_development_defaults(monkeypatch):
    from app.core import config

    cfg = config.Settings(app_env="development")
    config.settings.cache_clear()
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(config, "Settings", lambda: cfg)
    try:
        with pytest.raises(ValueError, match="APP_ENV"):
            config.settings()
    finally:
        config.settings.cache_clear()


def test_pdf_geometry_cannot_force_unbounded_preview_allocation():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=1000000000)
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(ValueError, match="PDF_PAGE_GEOMETRY_LIMIT"):
        validate_pdf(stream.getvalue())
