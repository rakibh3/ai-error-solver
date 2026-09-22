import logging

import uvicorn
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.catalog import router as catalog_router
from app.api.submissions import router as submissions_router
from app.core.database import SessionLocal
from app.core.limiter import limiter
from app.services import reference_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Schema is owned by Alembic (`alembic upgrade head`), not by create_all.

API_DESCRIPTION = """
An AI-powered error solver for learners.

An administrator curates **reference repositories** and indexes their branches.
Any registered user uploads their own codebase, picks a reference branch to
compare against, and receives a step-by-step fix with file, line, and exact
replacement.

## The comparison flow

1. `GET /api/v1/catalog/projects` — see what you can compare against
2. `GET /api/v1/catalog/projects/{project_id}/branches` — pick a branch
3. `POST /api/v1/submissions` — upload your code as a zip
4. `POST /api/v1/submissions/{submission_id}/analyze` — paste your error, get a fix

## Authentication

Register at `POST /api/v1/auth/register`, then log in at
`POST /api/v1/auth/login` and send the returned token on every request as
`Authorization: Bearer <access_token>`.

Registration is open to anyone, but **always creates a regular user**. There is
no way to register as an administrator: the request schema has no `role` field
and rejects one outright. Administrators are provisioned out of band.

## Conventions

- Accessing another user's resource returns **404**, never 403 — a 403 would
  confirm that the id exists.
- Unknown fields in a request body are **rejected with 422**, not ignored.
- A failed analysis returns **200** with `status: "failed"`, not an error code.
  Error codes are reserved for auth, ownership, and validation problems.
- Long-running administrator operations return **202** and continue in the
  background; poll for status rather than waiting on the request.
"""

app = FastAPI(
    title="Error Navigator API",
    description=API_DESCRIPTION,
    version="2.0.0",
    summary="Compare your code against a reference solution and get a targeted fix.",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Error Navigator", "url": "https://error-navigator.com"},
    license_info={"name": "Proprietary"},
    servers=[
        {"url": "/", "description": "This server"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.openapi_tags = [
    {
        "name": "Authentication API",
        "description": (
            "Open registration and login. Registration **always** creates a "
            "regular `USER` — sending a `role` field returns 422. Tokens are "
            "valid for 30 days."
        ),
    },
    {
        "name": "Catalog API",
        "description": (
            "Browse the reference projects and branches available to compare "
            "against. Only fully indexed branches appear here. **Steps 1-2** of "
            "the comparison flow."
        ),
    },
    {
        "name": "Submissions API",
        "description": (
            "Upload your codebase, run a comparison, and review past analyses. "
            "**Steps 3-4** of the comparison flow. All endpoints operate on "
            "your own submissions; administrators can see and act on any."
        ),
    },
    {
        "name": "Admin API",
        "description": (
            "Administrator-only. Ingest and re-index reference repositories, "
            "reconcile the vector store, and manage accounts — including the "
            "only endpoint that can grant administrator access."
        ),
    },
    {
        "name": "Root API",
        "description": "Liveness check.",
    },
]

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication API"])
app.include_router(catalog_router, prefix="/api/v1/catalog", tags=["Catalog API"])
app.include_router(
    submissions_router, prefix="/api/v1/submissions", tags=["Submissions API"]
)
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin API"])


@app.on_event("startup")
def sweep_interrupted_indexing() -> None:
    """BackgroundTasks die with the process; rescue rows stuck at `indexing`."""
    db = SessionLocal()
    try:
        count = reference_service.sweep_stale_indexing(db)
        if count:
            logger.warning("Marked %d interrupted indexing job(s) as failed", count)
    except Exception as e:
        logger.error("Startup sweep failed: %s", e)
    finally:
        db.close()


@app.get(
    "/",
    tags=["Root API"],
    summary="Liveness check",
    response_description="A static payload confirming the process is up.",
    description=(
        "Returns 200 while the process is running. Does not check the database "
        "or the vector store — use `GET /api/v1/admin/reference-projects/health` "
        "for that."
    ),
)
def read_root():
    return {"message": "Server is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
