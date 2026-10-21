from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Role, UserRole, CompanyReminder
from app.services.gratuity import gratuity
from conftest import account


def make_admin(client, headers, role_name="super_admin"):
    uid = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    with Session(client.engine) as db:
        role = Role(name=role_name)
        db.add(role)
        db.flush()
        db.add(UserRole(user_id=uid, role_id=role.id))
        db.commit()


def test_auth_rotation_revocation(client):
    headers, token = account(client)
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": token["refresh_token"]}
        ).status_code
        == 401
    )
    new = refreshed.json()
    h = {"Authorization": "Bearer " + new["access_token"]}
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers=h,
            json={"refresh_token": new["refresh_token"]},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_company_ownership_and_foreign_keys(client):
    h, _ = account(client)
    other, _ = account(client, "other@example.com")
    company = client.post(
        "/api/v1/companies", headers=h, json={"name": "Demo LLC"}
    ).json()
    cid = company["id"]
    assert client.get("/api/v1/companies/" + cid, headers=other).status_code == 404
    assert client.delete("/api/v1/companies/" + cid, headers=other).status_code == 404
    person = client.post(
        f"/api/v1/companies/{cid}/people",
        headers=h,
        json={"name": "Demo Partner", "role": "partner"},
    ).json()
    doc = client.post(
        f"/api/v1/companies/{cid}/documents",
        headers=h,
        json={
            "title": "Licence",
            "category": "Trade Licence",
            "expires_on": "2027-01-01",
            "person_id": person["id"],
        },
    ).json()
    r = client.post(
        f"/api/v1/companies/{cid}/reminders",
        headers=h,
        json={
            "title": "Renew licence",
            "due_on": "2026-12-01",
            "document_id": doc["id"],
        },
    )
    assert r.status_code == 201, r.text
    assert (
        client.get(f"/api/v1/companies/{cid}/reminders", headers=h).json()["total"] == 1
    )
    assert (
        client.get(f"/api/v1/companies/{cid}/documents", headers=other).status_code
        == 404
    )
    c2 = client.post(
        "/api/v1/companies", headers=other, json={"name": "Other LLC"}
    ).json()["id"]
    assert (
        client.post(
            f"/api/v1/companies/{c2}/reminders",
            headers=other,
            json={
                "title": "Cross tenant",
                "due_on": "2027-01-01",
                "document_id": doc["id"],
            },
        ).status_code
        == 422
    )
    with Session(client.engine) as db:
        assert db.scalar(select(CompanyReminder)).title == "Renew licence"
    assert client.delete(f"/api/v1/companies/{cid}", headers=h).status_code == 204


def test_admin_publish_and_notifications(client):
    h, _ = account(client)
    assert client.get("/api/v1/admin/users", headers=h).status_code == 403
    make_admin(client, h)
    v = client.post(
        "/api/v1/admin/content/videos",
        headers=h,
        json={"title": "Demo lesson", "status": "draft", "demo": True},
    )
    assert v.status_code == 201, v.text
    assert client.get("/api/v1/videos").json()["total"] == 0
    vid = v.json()["id"]
    assert (
        client.put(
            "/api/v1/admin/content/videos/" + vid,
            headers=h,
            json={"title": "Demo lesson", "status": "published", "demo": True},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/videos").json()["items"][0]["title"] == "Demo lesson"
    article = client.post(
        "/api/v1/admin/content/articles",
        headers=h,
        json={"title": "Demo article", "status": "published"},
    ).json()
    assert client.get("/api/v1/articles").json()["total"] == 1
    assert (
        client.put(
            "/api/v1/articles/" + article["id"] + "/bookmark", headers=h
        ).status_code
        == 200
    )
    notification = client.post(
        "/api/v1/admin/notifications",
        headers=h,
        json={
            "title": "Demo alert",
            "body": "Preview",
            "category": "Corporate Tax",
            "status": "published",
        },
    ).json()
    assert client.get("/api/v1/notifications", headers=h).json()["total"] == 1
    assert (
        client.patch(
            "/api/v1/notifications/" + notification["id"] + "/read", headers=h
        ).status_code
        == 200
    )
    assert client.get("/api/v1/notifications", headers=h).json()["items"][0]["read_at"]
    assert client.get("/api/v1/admin/audit-logs", headers=h).json()["total"] >= 4
    assert "password_hash" not in client.get("/api/v1/admin/users", headers=h).text


def test_validation_health_and_security(client):
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/ready").status_code == 200
    assert client.get("/api/v1/companies").status_code == 401
    assert client.get("/api/v1/videos?page=0").status_code == 422
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": "broken", "name": "", "password": "short"},
        ).status_code
        == 422
    )
    assert client.get("/api/v1/auth/oauth/google").status_code == 503
    assert (
        client.get("/api/v1/discuss/capabilities").json()["inference_enabled"] is False
    )


def test_gratuity_boundaries():
    assert gratuity(Decimal(15000), Decimal(7))["total"] == "82500.00"
    assert gratuity(Decimal(15000), Decimal(".99"))["total"] == "0.00"
    assert gratuity(Decimal(15000), Decimal(1))["total"] == "10500.00"
    assert gratuity(Decimal(15000), Decimal(5))["total"] == "52500.00"
    assert gratuity(Decimal(15000), Decimal(40))["total"] == "360000.00"
