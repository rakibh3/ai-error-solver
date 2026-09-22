"""Shared rate limiter.

Keyed by authenticated user where possible so one user on a shared NAT cannot
exhaust everyone else's budget; falls back to remote address for anonymous
requests (register/login).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def rate_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return f"token:{auth[7:][:64]}"
    return get_remote_address(request) or "anonymous"


limiter = Limiter(key_func=rate_limit_key)
