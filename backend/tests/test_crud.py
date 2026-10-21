from conftest import account
from test_workflows import make_admin


def test_document_renewal_and_reminder_completion(client):
    h, _ = account(client)
    cid = client.post(
        "/api/v1/companies", headers=h, json={"name": "Renewal Demo"}
    ).json()["id"]
    payload = {
        "title": "Trade Licence",
        "category": "Trade Licence",
        "expires_on": "2026-11-01",
    }
    doc = client.post(
        f"/api/v1/companies/{cid}/documents", headers=h, json=payload
    ).json()
    renewed = client.put(
        f"/api/v1/companies/{cid}/documents/{doc['id']}",
        headers=h,
        json={**payload, "expires_on": "2027-11-01"},
    )
    assert renewed.status_code == 200
    assert (
        client.get(f"/api/v1/companies/{cid}/documents", headers=h).json()["items"][0][
            "expires_on"
        ]
        == "2027-11-01"
    )
    reminder = {"title": "Renew", "document_id": doc["id"], "due_on": "2027-10-01"}
    rid = client.post(
        f"/api/v1/companies/{cid}/reminders", headers=h, json=reminder
    ).json()["id"]
    assert (
        client.put(
            f"/api/v1/companies/{cid}/reminders/{rid}",
            headers=h,
            json={**reminder, "completed": True},
        ).status_code
        == 200
    )
    # Completing the manual reminder does not remove the still-active licence expiry.
    next_deadline = client.get("/api/v1/dashboard", headers=h).json()["next_deadline"]
    assert next_deadline["id"] == doc["id"] and next_deadline["due_on"] == "2027-11-01"


def test_publication_chapters_respect_status_and_order(client):
    h, _ = account(client)
    make_admin(client, h)
    publication = client.post(
        "/api/v1/admin/content/publications", headers=h, json={"title": "Demo book"}
    ).json()
    for position in [3, 1, 2]:
        assert (
            client.post(
                "/api/v1/admin/content/chapters",
                headers=h,
                json={
                    "title": f"Chapter {position}",
                    "publication_id": publication["id"],
                    "position": position,
                },
            ).status_code
            == 201
        )
    assert (
        client.get(
            "/api/v1/publications/" + publication["id"] + "/chapters"
        ).status_code
        == 404
    )
    client.put(
        "/api/v1/admin/content/publications/" + publication["id"],
        headers=h,
        json={"title": "Demo book", "status": "published"},
    )
    chapters = client.get(
        "/api/v1/publications/" + publication["id"] + "/chapters"
    ).json()["items"]
    assert [c["position"] for c in chapters] == [1, 2, 3]
    assert (
        client.delete(
            "/api/v1/admin/content/publications/" + publication["id"], headers=h
        ).status_code
        == 204
    )
    assert client.get("/api/v1/publications/" + publication["id"]).status_code == 404


def test_failed_write_rolls_back_and_notification_preferences_isolate(client):
    admin, _ = account(client)
    make_admin(client, admin)
    reader, _ = account(client, "reader@example.com")
    before = client.get("/api/v1/admin/audit-logs", headers=admin).json()["total"]
    invalid = client.post(
        "/api/v1/admin/content/videos",
        headers=admin,
        json={"title": "Bad foreign key", "category_id": "missing"},
    )
    assert invalid.status_code == 422
    assert (
        client.get("/api/v1/admin/audit-logs", headers=admin).json()["total"] == before
    )
    assert (
        client.put(
            "/api/v1/notifications/preferences",
            headers=reader,
            json={"in_app": False, "categories": []},
        ).status_code
        == 200
    )
    client.post(
        "/api/v1/admin/notifications",
        headers=admin,
        json={
            "title": "Demo",
            "body": "Preference check",
            "category": "VAT",
            "status": "published",
        },
    )
    assert client.get("/api/v1/notifications", headers=reader).json()["total"] == 0
    own = client.get("/api/v1/notifications", headers=admin).json()["items"][0]
    assert (
        client.patch(
            "/api/v1/notifications/" + own["id"] + "/read", headers=reader
        ).status_code
        == 404
    )


def test_role_changes_and_account_suspension_are_server_enforced(client):
    admin, _ = account(client)
    make_admin(client, admin, "admin")
    target, _ = account(client, "target@example.com")
    uid = client.get("/api/v1/auth/me", headers=target).json()["id"]
    assert (
        client.put(
            "/api/v1/admin/users/" + uid,
            headers=admin,
            json={"status": "active", "roles": ["super_admin"]},
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/v1/admin/users/" + uid,
            headers=admin,
            json={"status": "suspended", "roles": ["user"]},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me", headers=target).status_code == 401
