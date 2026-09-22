"""Registration lockdown: the core security property of this redesign."""
import pytest

from app.models.user import User, UserRole
from app.tests.conftest import auth_header, register


def test_registration_creates_a_regular_user(client, db_session):
    r = register(client, "new@example.com")
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "USER"

    row = db_session.query(User).filter(User.email == "new@example.com").first()
    assert row.role == UserRole.USER


@pytest.mark.parametrize("role", ["ADMIN", "USER", "INSTRUCTOR", "admin", ""])
def test_role_in_registration_body_is_rejected(client, db_session, role):
    """extra='forbid' means this is a 422, not a silently-ignored field."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "fullname": "Sneaky",
            "email": f"sneaky-{role or 'blank'}@example.com",
            "password": "Password123",
            "role": role,
        },
    )
    assert r.status_code == 422, r.text
    assert db_session.query(User).filter(User.role == UserRole.ADMIN).count() == 0


def test_no_admin_can_ever_be_created_through_the_public_api(client, db_session):
    for payload in (
        {"role": "ADMIN"},
        {"is_active": True, "role": "ADMIN"},
        {"Role": "ADMIN"},
        {"user_role": "ADMIN"},
    ):
        body = {
            "fullname": "X",
            "email": "x@example.com",
            "password": "Password123",
        }
        body.update(payload)
        r = client.post("/api/v1/auth/register", json=body)
        assert r.status_code == 422, (payload, r.text)

    assert db_session.query(User).filter(User.role == UserRole.ADMIN).count() == 0


def test_duplicate_email_is_rejected(client):
    assert register(client, "dup@example.com").status_code == 201
    assert register(client, "dup@example.com").status_code == 400


@pytest.mark.parametrize(
    "email", ["not-an-email", "missing@", "@nohost.com", "spaces in@x.com"]
)
def test_invalid_email_is_rejected(client, email):
    r = client.post(
        "/api/v1/auth/register",
        json={"fullname": "X", "email": email, "password": "Password123"},
    )
    assert r.status_code == 422


@pytest.mark.parametrize("password", ["short1", "alllettersonly", "1234567890"])
def test_weak_password_is_rejected(client, password):
    r = client.post(
        "/api/v1/auth/register",
        json={"fullname": "X", "email": "weak@example.com", "password": password},
    )
    assert r.status_code == 422


def test_wrong_password_returns_401_not_500(client):
    """Regression: the old login logged user.email after rebinding user to
    None, raising AttributeError instead of returning 401."""
    register(client, "login@example.com")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "WrongPassword1"},
    )
    assert r.status_code == 401


def test_unknown_email_returns_401(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "Password123"},
    )
    assert r.status_code == 401


def test_inactive_user_cannot_log_in(client, db_session):
    register(client, "inactive@example.com")
    user = db_session.query(User).filter(User.email == "inactive@example.com").first()
    user.is_active = False
    db_session.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "Password123"},
    )
    assert r.status_code == 401


@pytest.mark.parametrize("token", ["garbage", "a.b.c", ""])
def test_bad_token_is_rejected(client, token):
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_me_returns_the_current_user(client, user_token):
    r = client.get("/api/v1/auth/me", headers=auth_header(user_token))
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"
    assert r.json()["role"] == "USER"
