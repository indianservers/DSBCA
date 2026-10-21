"""Isolated development fixtures. Never writes to Neon or publishes production rules."""

import json, secrets, copy
from pathlib import Path
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import app
from app.core.config import settings
from app.core.database import engine
from app import models as m
from app.professional import models as p
from app.calculators.reference_rules import TEMPLATES


def run(database_name="dsbca_phase3_dev", credentials_file=".local-phase3-access.json"):
    cfg = settings()
    if (
        cfg.app_env != "development"
        or database_name not in {"dsbca_phase3_dev", "dsbca_phase4_qa"}
        or engine().url.database != database_name
        or engine().url.host not in {"127.0.0.1", "localhost"}
    ):
        raise SystemExit("Seed requires isolated dsbca_phase3_dev development database")
    root = Path(__file__).resolve().parents[3]
    path = root / credentials_file
    values = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.exists()
        else {
            name: {
                "email": f"phase3-{name}-{secrets.token_hex(4)}@example.com",
                "password": secrets.token_urlsafe(24),
            }
            for name in ["operator", "reviewer", "reader"]
        }
    )
    with TestClient(app) as client:
        headers = {}
        for name, credentials in values.items():
            with Session(engine()) as db:
                exists = db.scalar(
                    select(m.User.id).where(m.User.email == credentials["email"])
                )
            response = client.post(
                "/api/v1/auth/login" if exists else "/api/v1/auth/register",
                json={
                    **credentials,
                    **({} if exists else {"name": "Development " + name.title()}),
                },
            )
            if response.status_code not in [200, 201]:
                raise RuntimeError("Local account setup failed")
            headers[name] = {
                "Authorization": "Bearer " + response.json()["access_token"]
            }
        with Session(engine()) as db:
            role = db.scalar(select(m.Role).where(m.Role.name == "super_admin"))
            if not role:
                role = m.Role(name="super_admin")
                db.add(role)
                db.flush()
            for name in ["operator", "reviewer"]:
                user = db.scalar(
                    select(m.User).where(m.User.email == values[name]["email"])
                )
                if not db.scalar(
                    select(m.UserRole.id).where(
                        m.UserRole.user_id == user.id, m.UserRole.role_id == role.id
                    )
                ):
                    db.add(m.UserRole(user_id=user.id, role_id=role.id))
                    db.add(
                        m.AuditLog(
                            actor_id=user.id,
                            action="phase3_development_operator_bootstrap",
                            resource_id=user.id,
                        )
                    )
            db.commit()
        path.write_text(json.dumps(values, indent=2), encoding="utf-8")
        with Session(engine()) as db:
            for subject in [
                "Corporate Tax",
                "VAT",
                "Transfer Pricing",
                "Pillar Two",
                "IFRS",
                "Audit",
            ]:
                if not db.scalar(
                    select(m.SubjectCategory.id).where(
                        m.SubjectCategory.name == subject
                    )
                ):
                    db.add(m.SubjectCategory(name=subject))
            db.commit()
            subject = db.scalar(
                select(m.SubjectCategory).where(
                    m.SubjectCategory.name == "Corporate Tax"
                )
            )
            for model in [m.Video, m.Publication]:
                for content in db.scalars(select(model)):
                    if content.category_id is None:
                        content.category_id = subject.id
            db.commit()
        for template in TEMPLATES:
            with Session(engine()) as db:
                exists = db.scalar(
                    select(p.RuleVersion.id).where(
                        p.RuleVersion.code == template["code"],
                        p.RuleVersion.version == template["version"],
                    )
                )
            if exists:
                continue
            created = client.post(
                "/api/v1/admin/professional/rules",
                headers=headers["operator"],
                json=template,
            )
            if created.status_code != 201:
                raise RuntimeError("Reference draft creation failed")
            rid = created.json()["id"]
            if (
                client.post(
                    f"/api/v1/admin/professional/rules/{rid}/validate",
                    headers=headers["operator"],
                    json={},
                ).status_code
                != 200
            ):
                raise RuntimeError("Reference validation failed")
            if (
                client.post(
                    f"/api/v1/admin/professional/rules/{rid}/publish",
                    headers=headers["reviewer"],
                    json={},
                ).status_code
                != 200
            ):
                raise RuntimeError("Development second-review simulation failed")
        with Session(engine()) as db:
            exists = db.scalar(
                select(m.Video.id).where(
                    m.Video.title == "Corporate Tax workflow — player demonstration"
                )
            )
        if not exists:
            video = client.post(
                "/api/v1/admin/content/videos",
                headers=headers["operator"],
                json={
                    "title": "Corporate Tax workflow — player demonstration",
                    "body": "Playback test using the official Flutter bee sample. This is not Corporate Tax instruction or verified professional guidance. Use the fictional PDF to test the learning workflow.",
                    "status": "published",
                    "demo": True,
                    "media_url": "https://flutter.github.io/assets-for-api-docs/assets/videos/bee.mp4",
                    "metadata_extra": {
                        "subject": "Corporate Tax",
                        "related_topics": ["Demonstration"],
                    },
                },
            ).json()
            pdf = root / "output/pdf/Corporate_Tax_Review_Checklist_DEMO.pdf"
            uploaded = client.post(
                "/api/v1/professional/media",
                headers=headers["operator"],
                data={"title": pdf.name},
                files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")},
            )
            if uploaded.status_code != 201:
                raise RuntimeError("Private demonstration asset failed")
            asset = uploaded.json()["asset_id"]
            book = client.post(
                "/api/v1/admin/content/publications",
                headers=headers["operator"],
                json={
                    "title": "Corporate Tax review checklist — DEMONSTRATION",
                    "body": "Fictional document review workflow. Not UAE law. Learning publication approval is independent from AI source approval.",
                    "demo": True,
                    "status": "published",
                    "visibility": "authenticated",
                    "metadata_extra": {
                        "subject": "Corporate Tax",
                        "kind": "technical_note",
                        "asset_id": asset,
                    },
                },
            ).json()
            chapter = client.post(
                "/api/v1/admin/content/chapters",
                headers=headers["operator"],
                json={
                    "publication_id": book["id"],
                    "title": "Review records — fictional checklist",
                    "position": 1,
                    "pages": 2,
                    "body": "Request the trial balance and supporting records; investigate differences. Fictional demonstration only.",
                    "asset_id": asset,
                },
            ).json()
            client.post(
                "/api/v1/admin/professional/learning-paths",
                headers=headers["operator"],
                json={
                    "title": "Corporate Tax learning workflow — demonstration",
                    "subject": "Corporate Tax",
                    "description": "Demonstration of enrollment, player progress and private chapter access. No certificate or credit is awarded.",
                    "status": "published",
                    "items": [
                        {"kind": "videos", "resource_id": video["id"]},
                        {"kind": "chapters", "resource_id": chapter["id"]},
                    ],
                },
            )
            client.post(
                "/api/v1/admin/content/webinars",
                headers=headers["operator"],
                json={
                    "title": "Development webinar registration test",
                    "body": "Local event workflow test. No meeting service or presenter has been booked. Joining information is not configured.",
                    "demo": True,
                    "status": "published",
                    "starts_at": (m.now() + timedelta(days=3)).isoformat(),
                    "metadata_extra": {
                        "timezone": "Asia/Dubai",
                        "capacity": 10,
                        "registration_open": True,
                        "presenter": "Development demonstration",
                    },
                },
            )
    print(
        f"Isolated development accounts, source-backed rule fixtures and labeled learning fixtures ready. Credentials remain in ignored {path.name}."
    )
