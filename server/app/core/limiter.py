"""Shared rate limiter.

Authenticated requests are keyed by the *verified* user id, so one user on a
shared NAT cannot exhaust everyone else's budget, and logging in again (a fresh
token) does not reset the count. Anything without a valid token is keyed by
client IP. The raw Authorization header is never used as a key: that let any
caller mint a fresh bucket per request by sending `Bearer <random>`.

Client IP: browsers reach the API through the Next.js BFF, so the TCP peer is
the Next.js server. The BFF sends the real client IP in X-Forwarded-For, and
uvicorn's proxy-headers support (on by default) rewrites `request.client` from
it -- but only when the peer is listed in FORWARDED_ALLOW_IPS (default
127.0.0.1). Set that to the Next.js server's address when it is not on
localhost, or every anonymous request shares one bucket.
"""
import jwt
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import ALGORITHM, JWT_SECRET_KEY, LOGIN_EMAIL_RATE_LIMIT


def client_ip(request: Request) -> str:
    return f"ip:{get_remote_address(request) or 'anonymous'}"


def rate_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = jwt.decode(auth[7:], JWT_SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.PyJWTError:
            payload = None
        subject = payload and (payload.get("sub") or payload.get("email"))
        if subject:
            return f"user:{subject}"
    return client_ip(request)


limiter = Limiter(key_func=rate_limit_key)

# Per-account login budget, independent of IP. Backstop for when the client IP
# cannot be trusted (spoofed X-Forwarded-For, botnets): guesses against one
# account stay capped no matter how many addresses they come from.
_login_storage = MemoryStorage()
_login_limiter = MovingWindowRateLimiter(_login_storage)
_login_limit = parse(LOGIN_EMAIL_RATE_LIMIT)


def hit_login_email(email: str) -> bool:
    """Count a login attempt for `email`. False once the budget is spent."""
    if not limiter.enabled:
        return True
    return _login_limiter.hit(_login_limit, "login-email", email.strip().lower())


def reset_login_email_limits() -> None:
    _login_storage.reset()
