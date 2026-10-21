"""Non-destructive development demonstration of the shared API contract against configured Neon.

Run deliberately with --allow-demo-writes. Creates labeled sample records and stores random
development account credentials ONLY in ignored .local-access.json. Never runs in production.
"""

import argparse
import json
import secrets
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.main import app
from app.core.config import settings
from app.core.database import engine
from app.models import Role, UserRole, User, AuditLog
from app.seed import seed


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-demo-writes", action="store_true")
    args = parser.parse_args()
    if settings().app_env != "development" or not args.allow_demo_writes:
        raise SystemExit(
            "Requires development environment and explicit --allow-demo-writes"
        )
    path = Path("../.local-access.json")
    credentials = (
        json.loads(path.read_text())
        if path.exists()
        else {
            "operator": {
                "email": "demo-operator-" + secrets.token_hex(5) + "@example.com",
                "password": secrets.token_urlsafe(24),
            },
            "user": {
                "email": "demo-reader-" + secrets.token_hex(5) + "@example.com",
                "password": secrets.token_urlsafe(24),
            },
        }
    )
    results = []
    with TestClient(app) as client:
        headers = {}
        for name, values in credentials.items():
            with Session(engine()) as db:
                exists = db.scalar(select(User.id).where(User.email == values["email"]))
            response = client.post(
                "/api/v1/auth/login" if exists else "/api/v1/auth/register",
                json={
                    **values,
                    **({} if exists else {"name": "Demonstration " + name.title()}),
                },
            )
            assert response.status_code in (
                200,
                201,
            ), "Demo account authentication failed"
            headers[name] = {
                "Authorization": "Bearer " + response.json()["access_token"]
            }
        with Session(engine()) as db:
            operator = db.scalar(
                select(User).where(User.email == credentials["operator"]["email"])
            )
            role = db.scalar(select(Role).where(Role.name == "super_admin"))
            if role is None:
                role = Role(name="super_admin")
                db.add(role)
                db.flush()
            if not db.scalar(
                select(UserRole).where(
                    UserRole.user_id == operator.id, UserRole.role_id == role.id
                )
            ):
                db.add(UserRole(user_id=operator.id, role_id=role.id))
                db.add(
                    AuditLog(
                        actor_id=operator.id,
                        action="development_demo_operator_grant",
                        resource_id=operator.id,
                    )
                )
            db.commit()
            seed(db, credentials["user"]["email"])
        path.write_text(json.dumps(credentials, indent=2) + "\n")
        results.append(
            "Random development accounts saved in ignored .local-access.json"
        )
        h = headers["operator"]
        for kind, title in [
            ("videos", "Demonstration: API publishing verification"),
            ("articles", "Demonstration: article publication verification"),
        ]:
            existing = client.get("/api/v1/" + kind, params={"q": title}).json()[
                "items"
            ]
            if not existing:
                response = client.post(
                    "/api/v1/admin/content/" + kind,
                    headers=h,
                    json={
                        "title": title,
                        "body": "Demonstration verification record. Not professional advice.",
                        "status": "published",
                        "demo": True,
                    },
                )
                assert response.status_code == 201, "Admin publish failed"
            assert (
                client.get("/api/v1/" + kind, params={"q": title}).json()["total"] >= 1
            )
            results.append(
                "Admin publishes " + kind + "; public User API reads it: PASS"
            )
        companies = client.get("/api/v1/companies", headers=headers["user"]).json()[
            "items"
        ]
        assert companies
        cid = companies[0]["id"]
        assert (
            client.get(
                f"/api/v1/companies/{cid}/reminders", headers=headers["user"]
            ).json()["total"]
            > 0
        )
        assert client.get(f"/api/v1/companies/{cid}", headers=h).status_code == 404
        results.append(
            "Owned companies/reminders persist; administrator cannot access private company: PASS"
        )
        notifications = client.get(
            "/api/v1/notifications", headers=headers["user"]
        ).json()["items"]
        assert notifications
        assert (
            client.patch(
                "/api/v1/notifications/" + notifications[0]["id"] + "/read",
                headers=headers["user"],
            ).status_code
            == 200
        )
        assert client.get("/api/v1/ready").status_code == 200
        results.append("In-app notification read state and readiness: PASS")
    print("\n".join(results))


if __name__ == "__main__":
    run()
