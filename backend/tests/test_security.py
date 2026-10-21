from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import PasswordResetToken
from app.core.config import settings
from app.core.security import digest
from conftest import account


def test_password_reset_and_session_invalidation(client):
    h, _ = account(client)
    cfg = settings()
    cfg.reset_delivery_url = "https://delivery.example.test/reset"
    cfg.reset_delivery_token = "test-delivery-token"
    response = MagicMock(is_error=False)
    with patch("app.api.auth.httpx.Client") as mock:
        mock.return_value.__enter__.return_value.post.return_value = response
        result = client.post(
            "/api/v1/auth/request-password-reset", json={"email": "test@example.com"}
        )
        assert result.status_code == 200
        raw = mock.return_value.__enter__.return_value.post.call_args.kwargs["json"][
            "reset_token"
        ]
        assert raw not in result.text
    with Session(client.engine) as db:
        assert db.scalar(select(PasswordResetToken)).token_hash == digest(raw)
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "password": "New-strong-password-456!"},
    )
    assert reset.status_code == 200
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw, "password": "New-strong-password-456!"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "New-strong-password-456!"},
        ).status_code
        == 200
    )
    cfg.reset_delivery_url = cfg.reset_delivery_token = ""


def test_rate_limit_counts_failed_credentials(client):
    for _ in range(15):
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "missing@example.com",
                    "password": "Wrong-password-123!",
                },
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "Wrong-password-123!"},
        ).status_code
        == 429
    )


def test_content_editor_cannot_read_users_or_private_companies(client):
    from test_workflows import make_admin

    owner, _ = account(client)
    company = client.post(
        "/api/v1/companies", headers=owner, json={"name": "Private LLC"}
    ).json()
    editor, _ = account(client, "editor@example.com")
    make_admin(client, editor, "content_editor")
    assert client.get("/api/v1/admin/dashboard", headers=editor).status_code == 200
    assert client.get("/api/v1/admin/users", headers=editor).status_code == 403
    assert (
        client.get("/api/v1/companies/" + company["id"], headers=editor).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/admin/settings",
            headers=editor,
            json={"key": "identity", "value": {}},
        ).status_code
        == 403
    )


def test_notification_deep_link_validation(client):
    from test_workflows import make_admin

    h, _ = account(client)
    make_admin(client, h)
    for link in [
        "https://evil.example",
        "//evil.example",
        "/\\evil.example",
        "javascript:alert(1)",
    ]:
        response = client.post(
            "/api/v1/admin/notifications",
            headers=h,
            json={
                "title": "Unsafe",
                "body": "Test",
                "category": "Test",
                "deep_link": link,
            },
        )
        assert response.status_code == 422


def test_seed_is_repeatable(client):
    from app.seed import seed

    h, _ = account(client)
    with Session(client.engine) as db:
        seed(db, "test@example.com")
        seed(db, "test@example.com")
    assert client.get("/api/v1/companies", headers=h).json()["total"] == 1
    assert client.get("/api/v1/videos").json()["total"] == 5
    assert client.get("/api/v1/notifications", headers=h).json()["total"] == 4
    update = client.get("/api/v1/updates").json()["items"][0]
    assert (
        client.patch("/api/v1/updates/" + update["id"] + "/read", headers=h).status_code
        == 200
    )
    assert client.get("/api/v1/updates", headers=h).json()["items"][0]["read_at"]
    assert client.get("/api/v1/updates").json()["items"][0]["read_at"] is None
