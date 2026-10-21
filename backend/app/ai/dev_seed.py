"""Explicit isolated-development seed. No automatic approval and no fake model answers."""

import json
import secrets
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import engine
from app.models import User, Role, UserRole, AuditLog
from app.ai.models import KnowledgeDocument
from app.main import app
from app.ai.demo_pdfs import LIBRARY


def run():
    cfg = settings()
    if cfg.app_env != "development" or "dsbca_phase2_dev" not in cfg.database_url:
        raise SystemExit("Seed is restricted to the isolated dsbca_phase2_dev database")
    root = Path(__file__).resolve().parents[3]
    path = root / ".local-phase2-access.json"
    values = (
        json.loads(path.read_text())
        if path.exists()
        else {
            name: {
                "email": f"phase2-{name}-{secrets.token_hex(4)}@example.com",
                "password": secrets.token_urlsafe(24),
            }
            for name in ["operator", "researcher"]
        }
    )
    with TestClient(app) as client:
        headers = {}
        for name, account in values.items():
            with Session(engine()) as db:
                exists = db.scalar(
                    select(User.id).where(User.email == account["email"])
                )
            response = client.post(
                "/api/v1/auth/login" if exists else "/api/v1/auth/register",
                json={
                    **account,
                    **({} if exists else {"name": "Demonstration " + name.title()}),
                },
            )
            if response.status_code not in (200, 201):
                raise RuntimeError("Development account setup failed")
            headers[name] = {
                "Authorization": "Bearer " + response.json()["access_token"]
            }
        with Session(engine()) as db:
            user = db.scalar(
                select(User).where(User.email == values["operator"]["email"])
            )
            role = db.scalar(select(Role).where(Role.name == "super_admin"))
            if not role:
                role = Role(name="super_admin")
                db.add(role)
                db.flush()
            if not db.scalar(
                select(UserRole).where(
                    UserRole.user_id == user.id, UserRole.role_id == role.id
                )
            ):
                db.add(UserRole(user_id=user.id, role_id=role.id))
                db.add(
                    AuditLog(
                        actor_id=user.id,
                        action="ai_development_operator_bootstrap",
                        resource_id=user.id,
                    )
                )
                db.commit()
        path.write_text(json.dumps(values, indent=2) + "\n")
        for filename, subject, title, _ in LIBRARY:
            with Session(engine()) as db:
                if db.scalar(
                    select(KnowledgeDocument.id).where(KnowledgeDocument.title == title)
                ):
                    continue
            metadata = {
                "title": title,
                "subject": subject,
                "issuer": "DSBCA demonstration library",
                "document_type": "Demonstration Material",
                "scope": "demo",
                "version": "1",
                "description": "DEMONSTRATION ONLY — NOT UAE LAW. Fictional review checklists.",
            }
            result = client.post(
                "/api/v1/admin/ai/documents",
                headers=headers["operator"],
                data={"metadata": json.dumps(metadata)},
                files={
                    "file": (
                        filename,
                        (root / "output/pdf" / filename).read_bytes(),
                        "application/pdf",
                    )
                },
            )
            if result.status_code != 201:
                raise RuntimeError("Demonstration PDF upload failed")
            print(filename + ": uploaded privately, pending processing and approval")
    print("Random local account details saved in ignored .local-phase2-access.json")


if __name__ == "__main__":
    run()
