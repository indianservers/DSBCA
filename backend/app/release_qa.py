"""Explicit loopback-only QA dataset. No production provider simulation."""

import asyncio
import json
import secrets
from pathlib import Path
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.database import engine
from app import models as m
from app.ai.models import KnowledgeDocument
from app.ai.ingestion import claim_job, run_step
from app.main import app
from app.professional.dev_seed import run as professional_seed


class QAFixtureEmbeddings:
    model = "qa-fixture-512-not-production"

    async def embed_documents(self, texts):
        return [await self.embed_query(t) for t in texts]

    async def embed_query(self, text):
        words = [
            "trial",
            "balance",
            "invoice",
            "revenue",
            "ledger",
            "evidence",
            "review",
            "workflow",
            "tax",
        ]
        return [float(text.lower().count(w)) for w in words] + [0.0] * 503


def guard():
    if not (
        settings().app_env == "development"
        and engine().url.database == "dsbca_phase4_qa"
        and engine().url.host in {"localhost", "127.0.0.1"}
    ):
        raise RuntimeError("QA refuses production or non-loopback databases")


def seed():
    guard()
    professional_seed("dsbca_phase4_qa", ".local-phase4-access.json")
    root = Path(__file__).resolve().parents[2]
    path = root / ".local-phase4-access.json"
    values = json.loads(path.read_text(encoding="utf-8"))
    for name in ["reader2", "editor"]:
        values.setdefault(
            name,
            {
                "email": f"qa-{name}-{secrets.token_hex(4)}@example.com",
                "password": secrets.token_urlsafe(24),
            },
        )
    path.write_text(json.dumps(values, indent=2), encoding="utf-8")
    with TestClient(app) as client:
        headers = {}
        for name, credentials in values.items():
            with Session(engine()) as db:
                exists = db.scalar(
                    select(m.User.id).where(m.User.email == credentials["email"])
                )
            response = client.post(
                "/api/v1/auth/login" if exists else "/api/v1/auth/register",
                json={**credentials, **({} if exists else {"name": "QA " + name})},
            )
            if response.status_code not in (200, 201):
                raise RuntimeError("QA account setup failed")
            headers[name] = {
                "Authorization": "Bearer " + response.json()["access_token"]
            }
        with Session(engine()) as db:
            for name, role_name in [
                ("reviewer", "admin"),
                ("editor", "content_editor"),
            ]:
                user = db.scalar(
                    select(m.User).where(m.User.email == values[name]["email"])
                )
                role = db.scalar(select(m.Role).where(m.Role.name == role_name))
                if not role:
                    role = m.Role(name=role_name)
                    db.add(role)
                    db.flush()
                for assignment in db.scalars(
                    select(m.UserRole).where(m.UserRole.user_id == user.id)
                ):
                    db.delete(assignment)
                db.flush()
                db.add(m.UserRole(user_id=user.id, role_id=role.id))
                db.add(
                    m.AuditLog(
                        actor_id=user.id,
                        action="local_qa_role_fixture",
                        resource_id=user.id,
                    )
                )
            db.commit()
        for name in ["reader", "reader2"]:
            h = headers[name]
            for i in range(2):
                title = f"QA fictional {name} company {i + 1}"
                existing = client.get("/api/v1/companies", headers=h).json()["items"]
                if any(x["name"] == title for x in existing):
                    continue
                company = client.post(
                    "/api/v1/companies",
                    headers=h,
                    json={
                        "name": title,
                        "profile_data": {
                            "entity_type": "LLC",
                            "zone": "Mainland",
                            "demonstration": True,
                        },
                    },
                ).json()
                for role in ["partner", "manager"]:
                    client.post(
                        f"/api/v1/companies/{company['id']}/people",
                        headers=h,
                        json={"name": "Fictional " + role, "role": role},
                    )
                for days in [-10, 15, 90]:
                    client.post(
                        f"/api/v1/professional/companies/{company['id']}/documents",
                        headers=h,
                        json={
                            "title": "QA licence " + str(days),
                            "category": "Trade Licence",
                            "expires_on": str(m.now().date() + timedelta(days=days)),
                        },
                    )
        if not client.get("/api/v1/articles", headers=headers["reader"]).json()[
            "items"
        ]:
            client.post(
                "/api/v1/admin/content/articles",
                headers=headers["operator"],
                json={
                    "title": "QA fictional record review",
                    "body": "Fictional training fixture, not tax guidance.",
                    "status": "published",
                    "demo": True,
                },
            )
        pdf = root / "output/pdf/Corporate_Tax_Review_Checklist_DEMO.pdf"
        for disposition in ["approved", "rejected", "superseded"]:
            title = "QA demonstration PDF — " + disposition
            pdf = (
                root
                / "output/pdf"
                / {
                    "approved": "Corporate_Tax_Review_Checklist_DEMO.pdf",
                    "rejected": "VAT_Review_Checklist_DEMO.pdf",
                    "superseded": "Audit_TP_Evidence_Checklist_DEMO.pdf",
                }[disposition]
            )
            with Session(engine()) as db:
                exists = db.scalar(
                    select(KnowledgeDocument.id).where(KnowledgeDocument.title == title)
                )
            if exists:
                continue
            metadata = {
                "title": title,
                "subject": "Corporate Tax",
                "issuer": "DSBCA QA demonstration",
                "document_type": "Demonstration Material",
                "scope": "demo",
                "version": "qa-v1",
            }
            uploaded = client.post(
                "/api/v1/admin/ai/documents",
                headers=headers["operator"],
                data={"metadata": json.dumps(metadata)},
                files={"file": ("demo.pdf", pdf.read_bytes(), "application/pdf")},
            )
            if uploaded.status_code != 201:
                raise RuntimeError(
                    "QA PDF upload failed: "
                    + str(uploaded.status_code)
                    + " "
                    + uploaded.text[:400]
                )
            docid = uploaded.json()["document_id"]
            for _ in range(50):
                with Session(engine(), expire_on_commit=False) as db:
                    claimed = claim_job(db)
                    if not claimed:
                        break
                    result = asyncio.run(
                        run_step(db, *claimed, embedder=QAFixtureEmbeddings())
                    )
                    if result["status"] == "failed":
                        raise RuntimeError("QA fixture indexing failed")
            action = "reject" if disposition == "rejected" else "approve"
            if (
                client.post(
                    f"/api/v1/admin/ai/documents/{docid}/{action}",
                    headers=headers["reviewer"],
                ).status_code
                != 200
            ):
                raise RuntimeError("QA source disposition failed")
            if disposition == "superseded":
                client.post(
                    f"/api/v1/admin/ai/documents/{docid}/supersede",
                    headers=headers["reviewer"],
                )
    print(
        "QA fixtures ready: five accounts, four companies, roles, expiries, learning and three demonstration PDF dispositions. No live AI provider used."
    )
