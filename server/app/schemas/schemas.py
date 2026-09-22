"""Request/response schemas for the catalog, submission, and analysis surface.

Every model carries OpenAPI examples so the Swagger UI at /docs is pre-filled
with realistic demo data and "Try it out" works without hand-typing a body.
FastAPI emits OpenAPI 3.1.0, so examples use the standard `examples` list via
`json_schema_extra` rather than the deprecated singular `example` key.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.core import config
from app.core.config import MAX_ERROR_MESSAGE_CHARS
from app.models.analysis import AnalysisStatus
from app.models.reference import BranchStatus

# Reused in examples so ids look consistent across the docs.
_PROJECT_ID = "3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f607"
_BRANCH_ID = "9c8b7a65-4321-4def-90ab-1122334455aa"
_SUBMISSION_ID = "7e1d2c3b-4a59-4687-b0c1-d2e3f4a5b6c7"
_ANALYSIS_ID = "1a2b3c4d-5e6f-4071-8293-a4b5c6d7e8f9"


class ErrorResponse(BaseModel):
    """The shape of every non-2xx body produced by this API."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"status": "error", "message": "Reference project not found"}]
        }
    )

    status: str = Field(default="error", examples=["error"])
    message: str = Field(
        ...,
        description="Human-readable explanation of what went wrong.",
        examples=["Reference project not found"],
    )


# --- Catalog (visible to any authenticated user) ---------------------------

class CatalogBranchOut(BaseModel):
    """A branch a user can compare against. Only `ready` branches are exposed."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _BRANCH_ID,
                    "branch_name": "lesson-03-routing",
                    "indexed_at": "2026-09-20T11:42:07Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(
        ...,
        description="Pass this as `branch_id` when running an analysis.",
        examples=[_BRANCH_ID],
    )
    branch_name: str = Field(..., examples=["lesson-03-routing"])
    indexed_at: Optional[datetime] = Field(
        None,
        description="When this branch was last embedded.",
        examples=["2026-09-20T11:42:07Z"],
    )


class CatalogProjectOut(BaseModel):
    """A reference project.

    `repo_url` is deliberately absent — it may be a private URL and non-admins
    have no reason to see it.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _PROJECT_ID,
                    "name": "fastapi-course",
                    "ready_branch_count": 4,
                }
            ]
        },
    )

    id: uuid.UUID = Field(..., examples=[_PROJECT_ID])
    name: str = Field(..., examples=["fastapi-course"])
    ready_branch_count: int = Field(
        default=0,
        description="How many branches of this project are indexed and comparable.",
        examples=[4],
    )


# --- Admin views (include failure detail) ----------------------------------

class AdminBranchOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _BRANCH_ID,
                    "branch_name": "lesson-03-routing",
                    "collection_name": "reference_fastapi_course_lesson_03_routing_a1b2c3d4",
                    "status": "ready",
                    "error": None,
                    "files_indexed": 37,
                    "chunks_indexed": 412,
                    "indexed_at": "2026-09-20T11:42:07Z",
                },
                {
                    "id": "0d1e2f3a-4b5c-4d6e-8f90-a1b2c3d4e5f6",
                    "branch_name": "lesson-04-auth",
                    "collection_name": "reference_fastapi_course_lesson_04_auth_e5f6a7b8",
                    "status": "failed",
                    "error": "Clone failed: Repository not found",
                    "files_indexed": None,
                    "chunks_indexed": None,
                    "indexed_at": None,
                },
            ]
        },
    )

    id: uuid.UUID = Field(..., examples=[_BRANCH_ID])
    branch_name: str = Field(..., examples=["lesson-03-routing"])
    collection_name: str = Field(
        ...,
        description="The Qdrant collection backing this branch.",
        examples=["reference_fastapi_course_lesson_03_routing_a1b2c3d4"],
    )
    status: BranchStatus = Field(
        ...,
        description=(
            "`pending` → queued, `indexing` → in progress, `ready` → comparable, "
            "`failed` → see `error`."
        ),
        examples=["ready"],
    )
    error: Optional[str] = Field(
        None,
        description="Populated only when `status` is `failed`.",
        examples=["Clone failed: Repository not found"],
    )
    files_indexed: Optional[int] = Field(None, examples=[37])
    chunks_indexed: Optional[int] = Field(None, examples=[412])
    indexed_at: Optional[datetime] = Field(None, examples=["2026-09-20T11:42:07Z"])


class AdminProjectOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _PROJECT_ID,
                    "name": "fastapi-course",
                    "repo_url": "https://github.com/acme/fastapi-course.git",
                    "created_by": 1,
                    "created_at": "2026-09-20T11:30:00Z",
                    "branches": [
                        {
                            "id": _BRANCH_ID,
                            "branch_name": "lesson-03-routing",
                            "collection_name": "reference_fastapi_course_lesson_03_routing_a1b2c3d4",
                            "status": "ready",
                            "error": None,
                            "files_indexed": 37,
                            "chunks_indexed": 412,
                            "indexed_at": "2026-09-20T11:42:07Z",
                        }
                    ],
                }
            ]
        },
    )

    id: uuid.UUID = Field(..., examples=[_PROJECT_ID])
    name: str = Field(..., examples=["fastapi-course"])
    repo_url: str = Field(
        ..., examples=["https://github.com/acme/fastapi-course.git"]
    )
    created_by: Optional[int] = Field(
        None, description="Id of the admin who ingested it.", examples=[1]
    )
    created_at: datetime = Field(..., examples=["2026-09-20T11:30:00Z"])
    branches: List[AdminBranchOut] = Field(default_factory=list)


class RepoRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"repo_url": "https://github.com/acme/fastapi-course.git"}
            ]
        },
    )

    repo_url: HttpUrl = Field(
        ...,
        description=(
            "HTTPS clone URL. Every branch is enumerated and indexed; the "
            "project name is derived from the last path segment.\n\n"
            "Must not embed credentials (`https://token@host/...`) — they would "
            "be stored and shown to every admin. The host must be in the "
            "server's `REPO_ALLOWED_HOSTS`."
        ),
        examples=["https://github.com/acme/fastapi-course.git"],
    )

    @field_validator("repo_url")
    @classmethod
    def safe_repo_url(cls, v: HttpUrl) -> HttpUrl:
        # Credentials in the URL would be persisted, returned by the admin
        # API, rendered in the UI, and echoed in git's error output.
        if v.username or v.password:
            raise ValueError(
                "Remove the credentials from the URL. Private repositories need a "
                "server-side git credential, not a token embedded in the link."
            )
        if v.scheme != "https":
            raise ValueError("Only https:// repository URLs are accepted")
        # An allow-list keeps git from being pointed at internal hosts (SSRF).
        host = (v.host or "").lower()
        allowed = config.REPO_ALLOWED_HOSTS
        if "*" not in allowed and host not in allowed:
            raise ValueError(
                f"Repositories from {host!r} are not allowed. Allowed hosts: "
                + ", ".join(sorted(allowed))
            )
        return v


class IngestAcceptedResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "accepted",
                    "project_id": _PROJECT_ID,
                    "name": "fastapi-course",
                    "branches": ["main", "lesson-03-routing", "lesson-04-auth"],
                    "message": "Indexing 3 branch(es) in the background",
                }
            ]
        }
    )

    status: str = Field(default="accepted", examples=["accepted"])
    project_id: uuid.UUID = Field(..., examples=[_PROJECT_ID])
    name: str = Field(..., examples=["fastapi-course"])
    branches: List[str] = Field(
        ...,
        description="Branches queued for indexing.",
        examples=[["main", "lesson-03-routing", "lesson-04-auth"]],
    )
    message: str = Field(..., examples=["Indexing 3 branch(es) in the background"])


# --- Submissions -----------------------------------------------------------

class SubmissionOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _SUBMISSION_ID,
                    "owner_id": 42,
                    "display_name": "My routing assignment",
                    "file_count": 12,
                    "total_bytes": 48213,
                    "created_at": "2026-09-22T09:15:44Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(
        ...,
        description="Also the on-disk directory name for this submission.",
        examples=[_SUBMISSION_ID],
    )
    owner_id: int = Field(..., examples=[42])
    display_name: str = Field(
        ...,
        description="Your label for the upload. Never used to build a file path.",
        examples=["My routing assignment"],
    )
    file_count: int = Field(
        ..., description="Files kept after pruning build artefacts.", examples=[12]
    )
    total_bytes: int = Field(
        ..., description="Total size on disk, counted against your quota.", examples=[48213]
    )
    created_at: datetime = Field(..., examples=["2026-09-22T09:15:44Z"])


# --- Analysis --------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "branch_id": _BRANCH_ID,
                    "error_message": (
                        'Traceback (most recent call last):\n'
                        '  File "app/routes/items.py", line 24, in get_item\n'
                        '    return item.serialise()\n'
                        "AttributeError: 'Item' object has no attribute 'serialise'"
                    ),
                }
            ]
        },
    )

    branch_id: uuid.UUID = Field(
        ...,
        description=(
            "A branch id from `GET /api/v1/catalog/projects/{project_id}/branches`. "
            "Must be `ready`."
        ),
        examples=[_BRANCH_ID],
    )
    error_message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_ERROR_MESSAGE_CHARS,
        description=(
            "The error or traceback you are seeing. File paths mentioned here "
            "are used to pick which of your files are sent for analysis, so "
            "paste the whole traceback rather than just the last line."
        ),
        examples=[
            "AttributeError: 'Item' object has no attribute 'serialise'"
        ],
    )


class CodeChange(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"old_code": "return item.serialise()", "new_code": "return item.serialize()"}
            ]
        }
    )

    old_code: str = Field(default="", examples=["return item.serialise()"])
    new_code: str = Field(default="", examples=["return item.serialize()"])


class FixInstruction(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "file": "app/routes/items.py",
                    "line": 24,
                    "change": {
                        "old_code": "return item.serialise()",
                        "new_code": "return item.serialize()",
                    },
                }
            ]
        }
    )

    file: str = Field(default="", examples=["app/routes/items.py"])
    line: Optional[int] = Field(default=None, examples=[24])
    change: CodeChange = Field(default_factory=CodeChange)


class AnalysisResult(BaseModel):
    """The shape the model is asked to return. Validated before persisting."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error_explanation": "The method is spelled `serialize`, not `serialise`.",
                    "fix_instructions": {
                        "file": "app/routes/items.py",
                        "line": 24,
                        "change": {
                            "old_code": "return item.serialise()",
                            "new_code": "return item.serialize()",
                        },
                    },
                }
            ]
        }
    )

    error_explanation: str = Field(
        ..., examples=["The method is spelled `serialize`, not `serialise`."]
    )
    fix_instructions: FixInstruction


class AnalysisOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _ANALYSIS_ID,
                    "submission_id": _SUBMISSION_ID,
                    "branch_id": _BRANCH_ID,
                    "error_message": "AttributeError: 'Item' object has no attribute 'serialise'",
                    "status": "success",
                    "result": {
                        "error_explanation": "The method is spelled `serialize`, not `serialise`.",
                        "fix_instructions": {
                            "file": "app/routes/items.py",
                            "line": 24,
                            "change": {
                                "old_code": "return item.serialise()",
                                "new_code": "return item.serialize()",
                            },
                        },
                    },
                    "failure_reason": None,
                    "model": "google/gemini-2.5-flash",
                    "created_at": "2026-09-22T09:18:02Z",
                },
                {
                    "id": "2b3c4d5e-6f70-4812-93a4-b5c6d7e8f901",
                    "submission_id": _SUBMISSION_ID,
                    "branch_id": _BRANCH_ID,
                    "error_message": "ImportError: cannot import name 'Router'",
                    "status": "failed",
                    "result": None,
                    "failure_reason": "Model response did not match the expected schema",
                    "model": "google/gemini-2.5-flash",
                    "created_at": "2026-09-22T09:20:31Z",
                },
            ]
        },
    )

    id: uuid.UUID = Field(..., examples=[_ANALYSIS_ID])
    submission_id: uuid.UUID = Field(..., examples=[_SUBMISSION_ID])
    branch_id: Optional[uuid.UUID] = Field(
        None,
        description="Null if the reference branch was deleted after the analysis ran.",
        examples=[_BRANCH_ID],
    )
    error_message: str = Field(
        ..., examples=["AttributeError: 'Item' object has no attribute 'serialise'"]
    )
    status: AnalysisStatus = Field(
        ...,
        description=(
            "`failed` is a normal outcome, not an HTTP error: the row is stored "
            "either way and `failure_reason` explains it."
        ),
        examples=["success"],
    )
    result: Optional[dict] = Field(
        None,
        description="Validated `AnalysisResult`. Null when `status` is `failed`.",
    )
    failure_reason: Optional[str] = Field(
        None,
        description="Why the analysis failed. Null when `status` is `success`.",
        examples=["Model response did not match the expected schema"],
    )
    model: str = Field(
        ..., description="The model that produced this result.", examples=["google/gemini-2.5-flash"]
    )
    created_at: datetime = Field(..., examples=["2026-09-22T09:18:02Z"])


class DeleteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "success",
                    "message": f"Submission {_SUBMISSION_ID} deleted",
                }
            ]
        }
    )

    status: str = Field(default="success", examples=["success"])
    message: str = Field(..., examples=[f"Submission {_SUBMISSION_ID} deleted"])
