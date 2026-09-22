"""Reusable OpenAPI `responses` blocks.

Keeps the status-code documentation consistent across routers instead of
repeating the same dict at every path operation. Compose with `{**A, **B}`.
"""
from typing import Any, Dict

from app.schemas.schemas import ErrorResponse


def _err(description: str, example_message: str) -> Dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {
            "application/json": {
                "example": {"detail": example_message},
            }
        },
    }


UNAUTHORIZED: Dict[int, Any] = {
    401: _err(
        "Missing, malformed, or expired bearer token.",
        "Could not validate credentials",
    )
}

INACTIVE: Dict[int, Any] = {
    400: _err("The account exists but has been deactivated.", "Inactive user")
}

FORBIDDEN_ADMIN: Dict[int, Any] = {
    403: _err(
        "Authenticated, but this endpoint is administrator-only.",
        "Admin access required",
    )
}

NOT_FOUND: Dict[int, Any] = {
    404: _err("The resource does not exist.", "Not found")
}

NOT_FOUND_OR_NOT_YOURS: Dict[int, Any] = {
    404: _err(
        "The resource does not exist, or belongs to another user. These two "
        "cases are deliberately indistinguishable — returning 403 would confirm "
        "that the id exists.",
        "Not found",
    )
}

VALIDATION: Dict[int, Any] = {
    422: {
        "description": (
            "Request body failed validation. Note that unknown fields are "
            "rejected, not ignored — sending `role` to the registration "
            "endpoint lands here."
        ),
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "type": "extra_forbidden",
                            "loc": ["body", "role"],
                            "msg": "Extra inputs are not permitted",
                        }
                    ]
                }
            }
        },
    }
}

RATE_LIMITED: Dict[int, Any] = {
    429: {
        "description": "Rate limit exceeded. Retry after the window resets.",
        "content": {
            "application/json": {
                "example": {"error": "Rate limit exceeded: 10 per 1 hour"}
            }
        },
    }
}

CONFLICT_QUOTA: Dict[int, Any] = {
    409: _err(
        "A per-user quota would be exceeded. Delete an existing submission first.",
        "Submission limit reached (5). Delete an existing submission first.",
    )
}

PAYLOAD_TOO_LARGE: Dict[int, Any] = {
    413: _err(
        "The upload exceeds the configured size limit.",
        "Upload exceeds the 26214400 byte limit",
    )
}

BAD_ARCHIVE: Dict[int, Any] = {
    400: _err(
        "The upload is not a valid zip, is empty, or failed a safety check "
        "(path traversal, symlink entry, or size limit).",
        "Archive contains a parent-directory reference: ../escape.py",
    )
}

# Convenience bundles.
AUTHENTICATED = {**UNAUTHORIZED, **INACTIVE}
ADMIN_ONLY = {**AUTHENTICATED, **FORBIDDEN_ADMIN}
OWNED_RESOURCE = {**AUTHENTICATED, **NOT_FOUND_OR_NOT_YOURS}
