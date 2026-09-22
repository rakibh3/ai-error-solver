"""Rate-limit keying and the per-account login cap."""
import pytest
from starlette.requests import Request

from app.core.limiter import rate_limit_key, reset_login_email_limits
from app.core.security import create_access_token
from app.tests.conftest import register


def _request(headers=None, client_host="203.0.113.7"):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw, "client": (client_host, 1234)})


def test_valid_token_is_keyed_by_user_not_token():
    """Logging in again (a new token) must not reset the user's budget."""
    a = create_access_token({"sub": "42", "email": "a@example.com"})
    b = create_access_token({"sub": "42", "email": "a@example.com", "jti": "fresh"})
    assert a != b
    key_a = rate_limit_key(_request({"Authorization": f"Bearer {a}"}))
    key_b = rate_limit_key(_request({"Authorization": f"Bearer {b}"}))
    assert key_a == key_b == "user:42"


@pytest.mark.parametrize("token", ["random", "x" * 200, "a.b.c"])
def test_unverifiable_token_falls_back_to_ip(token):
    key = rate_limit_key(_request({"Authorization": f"Bearer {token}"}))
    assert key == "ip:203.0.113.7"


@pytest.fixture()
def limits_on(client):
    client.app.state.limiter.enabled = True
    client.app.state.limiter.reset()
    reset_login_email_limits()
    yield client
    client.app.state.limiter.enabled = False
    client.app.state.limiter.reset()
    reset_login_email_limits()


def test_random_bearer_does_not_bypass_login_ip_limit(limits_on):
    """Every attempt carries a different fake token; they must share one bucket."""
    statuses = [
        limits_on.post(
            "/api/v1/auth/login",
            json={"email": f"nobody{i}@example.com", "password": "Wrong12345"},
            headers={"Authorization": f"Bearer fake-{i}"},
        ).status_code
        for i in range(12)
    ]
    assert statuses[:10] == [401] * 10
    assert statuses[10:] == [429, 429]


def test_login_attempts_are_capped_per_account(limits_on, monkeypatch):
    from limits import parse

    from app.core import limiter as limiter_module

    monkeypatch.setattr(limiter_module, "_login_limit", parse("3/hour"))
    register(limits_on, "victim@example.com")

    statuses = [
        limits_on.post(
            "/api/v1/auth/login",
            json={"email": "Victim@Example.com", "password": "Wrong12345"},
        ).status_code
        for _ in range(4)
    ]
    assert statuses == [401, 401, 401, 429]
