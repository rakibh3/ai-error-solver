"""Regression tests for the findings in docs/SECURITY_FOLLOWUPS.md."""
import importlib
import logging

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.tests.conftest import auth_header, login, register


# --- 3. Qdrant transport ------------------------------------------------------

@pytest.mark.parametrize(
    "url, key",
    [
        ("http://localhost:6333", None),
        ("http://127.0.0.1:6333", None),
        ("https://qdrant.internal:6333", "k"),
    ],
)
def test_qdrant_transport_allowed(url, key):
    config._check_qdrant_transport(url, key)


@pytest.mark.parametrize(
    "url, key, message",
    [
        ("http://qdrant.internal:6333", None, "QDRANT_API_KEY is required"),
        ("http://qdrant.internal:6333", "k", "must use https"),
    ],
)
def test_qdrant_transport_refused_off_host(url, key, message):
    with pytest.raises(RuntimeError, match=message):
        config._check_qdrant_transport(url, key)


# --- 4. Token revocation ------------------------------------------------------

def test_logout_revokes_every_token(client):
    register(client, "leaver@example.com")
    first = login(client, "leaver@example.com")
    second = login(client, "leaver@example.com")
    assert client.get("/api/v1/auth/me", headers=auth_header(second)).status_code == 200

    assert client.post("/api/v1/auth/logout", headers=auth_header(first)).status_code == 204

    for token in (first, second):
        assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 401
    # Signing in again issues a working token.
    fresh = login(client, "leaver@example.com")
    assert client.get("/api/v1/auth/me", headers=auth_header(fresh)).status_code == 200


def test_role_change_revokes_old_tokens(client, db_session, admin_token):
    from app.models.user import User

    register(client, "promoted@example.com")
    old = login(client, "promoted@example.com")
    target = db_session.query(User).filter(User.email == "promoted@example.com").first()

    r = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "ADMIN"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200, r.text
    assert client.get("/api/v1/auth/me", headers=auth_header(old)).status_code == 401


def test_token_without_version_is_rejected(client, user_token):
    claims = jwt.decode(user_token, config.JWT_SECRET_KEY, algorithms=[config.ALGORITHM])
    claims.pop("tv")
    legacy = jwt.encode(claims, config.JWT_SECRET_KEY, algorithm=config.ALGORITHM)
    assert client.get("/api/v1/auth/me", headers=auth_header(legacy)).status_code == 401


# --- 5a. API docs -------------------------------------------------------------

def test_api_docs_can_be_disabled(monkeypatch):
    import main

    monkeypatch.setattr(config, "ENABLE_API_DOCS", False)
    try:
        app = importlib.reload(main).app
        c = TestClient(app)  # no startup hook: these routes need no database
        for path in ("/docs", "/redoc", "/api/v1/openapi.json"):
            assert c.get(path).status_code == 404, path
    finally:
        monkeypatch.undo()
        importlib.reload(main)


def test_api_docs_enabled_by_default(client):
    assert client.get("/api/v1/openapi.json").status_code == 200


# --- 5b. No raw emails in logs --------------------------------------------------

def test_auth_logs_contain_no_email(client, caplog):
    caplog.set_level(logging.DEBUG)
    register(client, "private.person@example.com")
    login(client, "private.person@example.com")
    client.post("/api/v1/auth/login", json={"email": "private.person@example.com", "password": "wrong-pass1"})
    client.post("/api/v1/auth/login", json={"email": "nobody.here@example.com", "password": "wrong-pass1"})

    text = caplog.text.lower()
    assert "private.person@example.com" not in text
    assert "nobody.here@example.com" not in text
    assert "email_hash=" in text  # failed attempts stay correlatable


def test_email_fingerprint_is_stable_and_case_insensitive():
    from app.core.security import email_fingerprint

    assert email_fingerprint("A@Example.com") == email_fingerprint("a@example.com ")
    assert len(email_fingerprint("a@example.com")) == 12
    assert email_fingerprint("a@example.com") != email_fingerprint("b@example.com")


# --- 5c. repo_url ------------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "https://user:ghp_token@github.com/acme/repo.git",
        "https://ghp_token@github.com/acme/repo.git",
        "http://github.com/acme/repo.git",
        "https://169.254.169.254/latest/meta-data",
        "https://internal.corp/acme/repo.git",
    ],
)
def test_unsafe_repo_urls_are_rejected(client, admin_token, url):
    r = client.post(
        "/api/v1/admin/reference-projects",
        json={"repo_url": url},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 422, r.text


def test_repo_host_allow_list_can_be_opened(monkeypatch):
    from app.schemas.schemas import RepoRequest

    monkeypatch.setattr(config, "REPO_ALLOWED_HOSTS", {"*"})
    assert RepoRequest(repo_url="https://git.example.org/a/b.git")


def test_git_errors_are_redacted():
    from app.services.reference_service import redact_credentials

    raw = "fatal: unable to access 'https://bob:s3cret@github.com/a/b.git/': 403"
    assert redact_credentials(raw) == "fatal: unable to access 'https://***@github.com/a/b.git/': 403"
    assert redact_credentials("https://github.com/a/b.git") == "https://github.com/a/b.git"
