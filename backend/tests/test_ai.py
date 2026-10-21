import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.ai import models as m
from app.ai.schemas import GroundedAnswer, Claim
from app.ai.providers import SAFETY_POLICY
from app.ai.ingestion import claim_job, run_step
from app.core.config import settings
from app.ai.storage import LocalPrivateStorage
from conftest import account
from test_workflows import make_admin

PDF = (
    Path(__file__).resolve().parents[2]
    / "output/pdf/Corporate_Tax_Review_Checklist_DEMO.pdf"
)
WORDS = [
    "trial",
    "balance",
    "invoice",
    "revenue",
    "ledger",
    "evidence",
    "tax",
    "review",
    "reconcile",
    "workflow",
    "transfer",
    "pricing",
    "audit",
    "request",
    "document",
    "vat",
]


class FixtureEmbeddings:
    """Controlled test vectors. Never offered as a production semantic model."""

    model = "fixture-512"

    async def embed_documents(self, texts):
        return [await self.embed_query(t) for t in texts]

    async def embed_query(self, text):
        values = [float(text.lower().count(w)) for w in WORDS] + [0.0] * (
            512 - len(WORDS)
        )
        return values


class FixtureChat:
    async def generate_answer(self, question, evidence, history, config):
        source = (
            next(e for e in evidence if "trial balance" in e["passage"].lower())
            if any("trial balance" in e["passage"].lower() for e in evidence)
            else evidence[0]
        )
        quote = source["passage"]
        return GroundedAnswer(
            claims=[
                Claim(
                    text=quote, evidence_ids=[source["id"]], supporting_quotes=[quote]
                )
            ],
            missing_information=[],
            limitations=["Controlled provider fixture, not live AI."],
        ), {"input_tokens": 100, "output_tokens": 60, "model": "fixture-chat"}


@pytest.fixture
def ai_setup(client, tmp_path, monkeypatch):
    cfg = settings()
    monkeypatch.setattr(cfg, "pdf_storage_backend", "local")
    monkeypatch.setattr(cfg, "pdf_local_root", str(tmp_path / "private"))
    monkeypatch.setattr(cfg, "ai_vector_backend", "exact")
    monkeypatch.setattr(cfg, "ai_min_evidence_score", 0.20)
    monkeypatch.setattr(cfg, "ai_daily_tokens", 1000000)
    admin, _ = account(client)
    make_admin(client, admin)
    reader, _ = account(client, "researcher@example.com")
    other, _ = account(client, "stranger@example.com")
    with (
        patch("app.ai.retrieval.embedding_provider", return_value=FixtureEmbeddings()),
        patch("app.ai.chat.chat_provider", return_value=FixtureChat()),
    ):
        yield client, admin, reader, other


def upload(
    client,
    admin,
    *,
    scope="demo",
    title="Demonstration CT checklist",
    version="v1",
    dates=None,
    data=None,
):
    metadata = {
        "title": title,
        "subject": "Corporate Tax",
        "issuer": "DSBCA demonstration",
        "document_type": (
            "Demonstration Material" if scope == "demo" else "Internal Technical Note"
        ),
        "scope": scope,
        "version": version,
        **(dates or {}),
    }
    response = client.post(
        "/api/v1/admin/ai/documents",
        headers=admin,
        data={"metadata": json.dumps(metadata)},
        files={"file": ("example.pdf", data or PDF.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json(), metadata


def index(client, *, fail=False):
    class Broken(FixtureEmbeddings):
        async def embed_documents(self, texts):
            raise RuntimeError("provider secret should not be logged")

    for _ in range(60):
        with Session(client.engine, expire_on_commit=False) as db:
            claimed = claim_job(db)
            if not claimed:
                break
            result = asyncio.run(
                run_step(
                    db, *claimed, embedder=Broken() if fail else FixtureEmbeddings()
                )
            )
            if result["status"] == "failed":
                break
    return result


def approve(client, admin, uploaded):
    response = client.post(
        "/api/v1/admin/ai/documents/" + uploaded["document_id"] + "/approve",
        headers=admin,
    )
    assert response.status_code == 200, response.text


def ask(
    client,
    reader,
    *,
    question="Which documents support the trial balance review workflow?",
    include_demo=True,
    conversation=None,
    request_id="request_abcdefghij",
    **extra,
):
    if not conversation:
        conversation = client.post(
            "/api/v1/ai/conversations", headers=reader, json={}
        ).json()["id"]
    payload = {
        "conversation_id": conversation,
        "request_id": request_id,
        "question": question,
        "include_demo": include_demo,
        **extra,
    }
    response = client.post("/api/v1/ai/chat", headers=reader, json=payload)
    assert response.status_code == 200, response.text
    return response.json(), payload


def test_upload_extract_index_approve_answer_exact_source(ai_setup):
    c, admin, reader, other = ai_setup
    uploaded, _ = upload(c, admin)
    assert uploaded["sha256"] == hashlib.sha256(PDF.read_bytes()).hexdigest()
    assert index(c)["status"] == "succeeded"
    approve(c, admin, uploaded)
    answer, request = ask(c, reader)
    assert answer["status"] == "completed", answer
    assert answer["citations"]
    assert "DEMONSTRATION ONLY" in answer["text"]
    citation = answer["citations"][0]
    assert citation["version_id"] == uploaded["version_id"]
    source = c.get("/api/v1" + citation["source_path"], headers=reader)
    assert source.status_code == 200
    page = c.get("/api/v1" + citation["page_path"], headers=reader).json()
    assert "DEMONSTRATION ONLY" in page["text"]
    assert page["physical_page"] >= 1
    preview = c.get("/api/v1" + page["preview_path"], headers=reader)
    assert preview.status_code == 200 and preview.content.startswith(b"\x89PNG")
    ticket = c.get(
        f"/api/v1/ai/documents/{uploaded['version_id']}/download", headers=reader
    ).json()
    original = c.get("/api/v1" + ticket["path"])
    assert original.status_code == 200 and original.content == PDF.read_bytes()
    assert (
        c.get(
            "/api/v1/ai/conversations/" + request["conversation_id"], headers=other
        ).status_code
        == 404
    )
    assert (
        c.get(
            "/api/v1/ai/conversations/" + request["conversation_id"] + "/messages",
            headers=other,
        ).status_code
        == 404
    )
    assert (
        c.post(
            "/api/v1/ai/feedback",
            headers=reader,
            json={"message_id": answer["id"], "rating": 1},
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/v1/ai/feedback",
            headers=other,
            json={"message_id": answer["id"], "rating": -1},
        ).status_code
        == 404
    )


def test_pending_demo_and_missing_evidence_are_excluded(ai_setup):
    c, admin, reader, _ = ai_setup
    uploaded, _ = upload(c, admin)
    index(c)
    answer, _ = ask(c, reader)
    assert answer["status"] == "insufficient_evidence"
    approve(c, admin, uploaded)
    answer, _ = ask(c, reader, include_demo=False)
    assert answer["status"] == "insufficient_evidence"
    answer, _ = ask(c, reader, question="Intergalactic giraffes and zebras?")
    assert answer["status"] == "insufficient_evidence"
    assert "does not establish" in answer["text"]


def test_private_sources_and_organizations_do_not_leak(ai_setup):
    c, admin, reader, other = ai_setup
    uploaded, metadata = upload(c, admin, scope="private")
    index(c)
    approve(c, admin, uploaded)
    answer, _ = ask(c, reader)
    assert answer["status"] == "insufficient_evidence"
    assert (
        c.get(
            f"/api/v1/ai/documents/{uploaded['version_id']}/pages/1", headers=reader
        ).status_code
        == 404
    )
    metadata.update(scope="organization", organization_id="missing")
    response = c.post(
        "/api/v1/admin/ai/documents",
        headers=admin,
        data={"metadata": json.dumps(metadata)},
        files={"file": ("x.pdf", PDF.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 403
    assert c.get("/api/v1/admin/ai/documents", headers=reader).status_code == 403


def test_history_versioning_and_historical_applicability(ai_setup):
    c, admin, reader, _ = ai_setup
    uploaded, metadata = upload(
        c,
        admin,
        scope="shared",
        dates={"effective_from": "2024-01-01", "effective_to": "2025-12-31"},
    )
    index(c)
    approve(c, admin, uploaded)
    historical, _ = ask(c, reader, period_start="2025-01-01", period_end="2025-12-31")
    assert historical["status"] == "completed"
    assert (
        c.post(
            "/api/v1/admin/ai/documents/" + uploaded["document_id"] + "/supersede",
            headers=admin,
        ).status_code
        == 200
    )
    assert (
        c.get(
            "/api/v1" + historical["citations"][0]["source_path"], headers=reader
        ).status_code
        == 200
    )
    current, _ = ask(c, reader)
    assert current["status"] == "insufficient_evidence"
    prior, _ = ask(c, reader, period_start="2025-01-01", period_end="2025-12-31")
    assert prior["status"] == "completed"
    assert (
        c.patch(
            "/api/v1/admin/ai/documents/" + uploaded["document_id"],
            headers=admin,
            json=metadata,
        ).status_code
        == 409
    )


def test_failed_embedding_retry_is_idempotent(ai_setup):
    c, admin, reader, _ = ai_setup
    uploaded, _ = upload(c, admin)
    assert index(c, fail=True)["status"] == "failed"
    with Session(c.engine) as db:
        count = db.scalar(select(func.count()).select_from(m.KnowledgeChunk))
    assert (
        c.post(
            "/api/v1/admin/ai/documents/" + uploaded["document_id"] + "/retry",
            headers=admin,
        ).status_code
        == 200
    )
    assert index(c)["status"] == "succeeded"
    with Session(c.engine) as db:
        assert db.scalar(select(func.count()).select_from(m.KnowledgeChunk)) == count
        assert (
            db.scalar(select(func.count()).select_from(m.KnowledgeEmbedding)) == count
        )
    logs = c.get("/api/v1/admin/ai/processing-jobs", headers=admin).text
    assert "provider secret" not in logs


def test_citation_injection_and_provider_outage_preserve_question(ai_setup):
    c, admin, reader, _ = ai_setup
    uploaded, _ = upload(c, admin)
    index(c)
    approve(c, admin, uploaded)

    class Malicious(FixtureChat):
        async def generate_answer(self, *args):
            return (
                GroundedAnswer(
                    claims=[
                        Claim(
                            text="Invented rule 999",
                            evidence_ids=["nonexistent"],
                            supporting_quotes=["this is not supporting evidence"],
                        )
                    ],
                    missing_information=[],
                    limitations=[],
                ),
                {},
            )

    with patch("app.ai.chat.chat_provider", return_value=Malicious()):
        answer, request = ask(c, reader)
    assert answer["status"] == "failed" and not answer["citations"]
    assert answer["metadata"]["error_code"] == "citation_validation_failed"

    class Outage(FixtureChat):
        async def generate_answer(self, *args):
            raise RuntimeError("Sensitive provider detail")

    with patch("app.ai.chat.chat_provider", return_value=Outage()):
        answer, request = ask(c, reader, request_id="request_second_unique")
    assert answer["status"] == "failed"
    assert "Sensitive provider detail" not in json.dumps(answer)
    messages = c.get(
        "/api/v1/ai/conversations/" + request["conversation_id"] + "/messages",
        headers=reader,
    ).json()["items"]
    assert any(
        m["role"] == "user" and m["text"] == request["question"] for m in messages
    )
    assert "UNTRUSTED DATA" in SAFETY_POLICY


def test_streaming_idempotency_delete_and_cancellation_permissions(ai_setup):
    c, admin, reader, other = ai_setup
    answer, request = ask(c, reader)
    assert (
        c.post("/api/v1/ai/chat", headers=reader, json=request).json()["id"]
        == answer["id"]
    )
    stream = c.post(
        "/api/v1/ai/chat/stream",
        headers=reader,
        json={**request, "request_id": "stream_request_unique"},
    )
    assert (
        "event: accepted" in stream.text
        and "event: answer_delta" in stream.text
        and "event: done" in stream.text
    )
    assert (
        c.post(
            "/api/v1/ai/messages/" + answer["id"] + "/cancel", headers=other
        ).status_code
        == 404
    )
    assert (
        c.delete(
            "/api/v1/ai/conversations/" + request["conversation_id"], headers=reader
        ).status_code
        == 204
    )
    assert (
        c.get(
            "/api/v1/ai/conversations/" + request["conversation_id"], headers=reader
        ).status_code
        == 404
    )


def test_file_validation_hash_and_private_storage_paths(ai_setup):
    c, admin, reader, _ = ai_setup
    metadata = {
        "title": "Bad",
        "subject": "VAT",
        "issuer": "DSB",
        "document_type": "Demonstration Material",
        "scope": "demo",
        "version": "1",
    }
    response = c.post(
        "/api/v1/admin/ai/documents",
        headers=admin,
        data={"metadata": json.dumps(metadata)},
        files={"file": ("bad.pdf", b"not a PDF", "application/pdf")},
    )
    assert response.status_code == 422
    with pytest.raises(ValueError):
        LocalPrivateStorage().get("../.env", 1000)
    uploaded, _ = upload(c, admin)
    with Session(c.engine) as db:
        version = db.get(m.DocumentVersion, uploaded["version_id"])
        path = LocalPrivateStorage().path(version.storage_key)
        path.write_bytes(b"%PDF-corrupt")
    assert index(c)["error_code"] == "CONTENT_HASH_MISMATCH"


def test_settings_versions_analytics_and_clarification(ai_setup):
    c, admin, reader, _ = ai_setup
    original = c.get("/api/v1/admin/ai/settings", headers=admin).json()["configuration"]
    updated = c.patch(
        "/api/v1/admin/ai/settings",
        headers=admin,
        json={**original, "name": "Research v2"},
    )
    assert updated.status_code == 200
    assert (
        c.get("/api/v1/admin/ai/settings", headers=admin).json()["version_id"]
        == updated.json()["version_id"]
    )
    answer, _ = ask(c, reader, question="What applied during FY2025?")
    assert answer["status"] == "clarification"
    metrics = c.get("/api/v1/admin/ai/analytics", headers=admin).json()
    assert metrics["questions"] == 1
    assert "question" not in metrics and "text" not in metrics
    assert c.get("/api/v1/internal/ai/jobs/tick").status_code == 401
