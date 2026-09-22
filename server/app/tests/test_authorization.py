"""The authorization matrix — the test that protects the whole redesign.

For every endpoint: anonymous / USER / other-USER / ADMIN.
"""
import uuid

import pytest

from app.tests.conftest import auth_header

FAKE_ID = str(uuid.uuid4())

# (method, path, anon, user, admin)
MATRIX = [
    ("GET", "/api/v1/catalog/projects", 401, 200, 200),
    ("GET", f"/api/v1/catalog/projects/{FAKE_ID}/branches", 401, 404, 404),
    ("GET", "/api/v1/submissions", 401, 200, 200),
    ("GET", f"/api/v1/submissions/{FAKE_ID}", 401, 404, 404),
    ("DELETE", f"/api/v1/submissions/{FAKE_ID}", 401, 404, 404),
    ("GET", f"/api/v1/submissions/{FAKE_ID}/analyses", 401, 404, 404),
    ("GET", "/api/v1/admin/reference-projects", 401, 403, 200),
    ("GET", "/api/v1/admin/users", 401, 403, 200),
    ("DELETE", f"/api/v1/admin/reference-projects/{FAKE_ID}", 401, 403, 404),
    ("POST", f"/api/v1/admin/reference-projects/{FAKE_ID}/reindex", 401, 403, 404),
]


@pytest.mark.parametrize("method,path,anon,user,admin", MATRIX)
def test_authorization_matrix(
    client, user_token, admin_token, method, path, anon, user, admin
):
    assert client.request(method, path).status_code == anon

    r = client.request(method, path, headers=auth_header(user_token))
    assert r.status_code == user, f"USER {method} {path}: {r.status_code} ({r.text})"

    r = client.request(method, path, headers=auth_header(admin_token))
    assert r.status_code == admin, f"ADMIN {method} {path}: {r.status_code} ({r.text})"


def test_user_cannot_ingest_a_reference_project(client, user_token):
    r = client.post(
        "/api/v1/admin/reference-projects",
        json={"repo_url": "https://github.com/example/repo.git"},
        headers=auth_header(user_token),
    )
    assert r.status_code == 403


def test_user_cannot_promote_themselves(client, user_token, db_session):
    from app.models.user import User, UserRole

    me = db_session.query(User).filter(User.email == "user@example.com").first()
    r = client.patch(
        f"/api/v1/admin/users/{me.id}/role",
        json={"role": "ADMIN"},
        headers=auth_header(user_token),
    )
    assert r.status_code == 403
    db_session.refresh(me)
    assert me.role == UserRole.USER


def test_admin_can_promote_a_user(client, admin_token, user_token, db_session):
    from app.models.user import User, UserRole

    target = db_session.query(User).filter(User.email == "user@example.com").first()
    r = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "ADMIN"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "ADMIN"
    db_session.refresh(target)
    assert target.role == UserRole.ADMIN


def test_last_admin_cannot_be_demoted(client, admin_token, db_session):
    from app.models.user import User

    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    r = client.patch(
        f"/api/v1/admin/users/{admin.id}/role",
        json={"role": "USER"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 409


def test_role_update_rejects_unknown_fields(client, admin_token, db_session):
    from app.models.user import User

    target = db_session.query(User).filter(User.email == "admin@example.com").first()
    r = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "ADMIN", "is_active": False},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 422
