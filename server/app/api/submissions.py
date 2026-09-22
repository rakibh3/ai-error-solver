"""User-driven submissions and comparisons.

Every handler that takes an `{id}` loads the row and calls `assert_can_access`
before doing anything else.
"""
import uuid
from typing import Annotated, List

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api import responses as r
from app.core.config import ANALYZE_RATE_LIMIT, UPLOAD_RATE_LIMIT
from app.core.database import get_db
from app.core.limiter import limiter
from app.middleware.role_checker import assert_can_access, get_current_user
from app.models.analysis import Analysis
from app.models.reference import BranchStatus, ReferenceBranch
from app.models.user import User
from app.schemas.schemas import (
    AnalysisOut,
    AnalyzeRequest,
    DeleteResponse,
    SubmissionOut,
)
from app.services import analysis_service, submission_service

router = APIRouter()

# Annotated alias so the path parameter's docs are declared once and reused
# safely across handlers (sharing a single Path() instance is not).
SubmissionId = Annotated[
    uuid.UUID,
    Path(
        ...,
        description="A submission id returned by `POST /api/v1/submissions`.",
        examples=["7e1d2c3b-4a59-4687-b0c1-d2e3f4a5b6c7"],
    ),
]


@router.post(
    "",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload your codebase",
    response_description="The stored submission record.",
    description=(
        "**Step 3 of the comparison flow.**\n\n"
        "Upload a zip archive of the project you want checked. Send it as "
        "`multipart/form-data` with two parts:\n\n"
        "- `display_name` — your own label for the upload. Stored as data only; "
        "it never becomes part of a file path, so `../../etc` is a perfectly "
        "safe (if odd) label.\n"
        "- `file` — the `.zip` itself, verified by magic bytes rather than by "
        "filename.\n\n"
        "Build artefacts (`node_modules`, `.venv`, `__pycache__`, lockfiles, "
        "`.git`) are stripped after extraction and do not count toward your "
        "quota.\n\n"
        "**Limits:** 25 MB upload, 50 MB extracted, 2000 archive entries, "
        "10 MB per file, 5 submissions and 200 MB per account. Archives "
        "containing absolute paths, `..` traversal, or symlinks are rejected "
        "outright."
    ),
    responses={
        **r.AUTHENTICATED,
        **r.BAD_ARCHIVE,
        **r.CONFLICT_QUOTA,
        **r.PAYLOAD_TOO_LARGE,
        **r.VALIDATION,
        **r.RATE_LIMITED,
    },
)
@limiter.limit(UPLOAD_RATE_LIMIT)
def create_submission(
    request: Request,
    display_name: str = Form(
        ...,
        min_length=1,
        max_length=255,
        description="Your label for this upload. Never used to build a file path.",
        examples=["My routing assignment"],
    ),
    file: UploadFile = File(..., description="A `.zip` archive of your project."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return submission_service.create_submission(
        db=db, owner=current_user, display_name=display_name, file=file
    )


@router.get(
    "",
    response_model=List[SubmissionOut],
    summary="List your submissions",
    response_description="Your submissions, newest first.",
    description=(
        "Lists submissions you own, newest first. Administrators see every "
        "submission from every account."
    ),
    responses={**r.AUTHENTICATED},
)
def list_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return submission_service.list_submissions(db, current_user)


@router.get(
    "/{submission_id}",
    response_model=SubmissionOut,
    summary="Get one submission",
    response_description="The submission record.",
    description=(
        "Fetch a single submission you own. Requesting someone else's "
        "submission returns **404**, identical to a submission that does not "
        "exist — a 403 would confirm the id is real."
    ),
    responses={**r.OWNED_RESOURCE},
)
def get_submission(
    submission_id: SubmissionId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submission = submission_service.get_submission(db, submission_id)
    assert_can_access(submission.owner_id, current_user)
    return submission


@router.delete(
    "/{submission_id}",
    response_model=DeleteResponse,
    summary="Delete a submission",
    response_description="Confirmation that the submission was removed.",
    description=(
        "Deletes the submission, its extracted files, and its entire analysis "
        "history. Frees the quota it was using. Owners and administrators only; "
        "this cannot be undone."
    ),
    responses={**r.OWNED_RESOURCE},
)
def delete_submission(
    submission_id: SubmissionId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submission = submission_service.get_submission(db, submission_id)
    assert_can_access(submission.owner_id, current_user)
    return submission_service.delete_submission(db, submission)


@router.post(
    "/{submission_id}/analyze",
    response_model=AnalysisOut,
    summary="Compare this submission against a reference branch",
    response_description=(
        "The stored analysis. Check `status` — `failed` is returned with 200."
    ),
    description=(
        "**Step 4 of the comparison flow.**\n\n"
        "Compares your uploaded code against the reference branch you pick and "
        "returns a fix with file, line, and exact replacement.\n\n"
        "Paste the **whole traceback** into `error_message`, not just the final "
        "line: file paths in the traceback decide which of your files are sent "
        "for analysis.\n\n"
        "**A failed analysis still returns 200.** If the model cannot produce a "
        "usable answer, the response has `status: \"failed\"` and a "
        "`failure_reason`, and the attempt is recorded in your history. Only "
        "auth, ownership, and validation problems produce error status codes.\n\n"
        "This endpoint costs an embedding call plus a model call, so it is rate "
        "limited per account."
    ),
    responses={
        **r.AUTHENTICATED,
        404: {
            "description": (
                "The submission does not exist or is not yours, **or** the "
                "`branch_id` does not exist or is not `ready`."
            ),
            "content": {
                "application/json": {
                    "example": {"detail": "Reference branch not found or not ready"}
                }
            },
        },
        **r.VALIDATION,
        **r.RATE_LIMITED,
    },
)
@limiter.limit(ANALYZE_RATE_LIMIT)
def analyze(
    request: Request,
    submission_id: SubmissionId,
    payload: AnalyzeRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submission = submission_service.get_submission(db, submission_id)
    assert_can_access(submission.owner_id, current_user)

    branch = (
        db.query(ReferenceBranch)
        .filter(ReferenceBranch.id == payload.branch_id)
        .first()
    )
    if not branch or branch.status != BranchStatus.READY:
        raise HTTPException(
            status_code=404, detail="Reference branch not found or not ready"
        )

    return analysis_service.run_analysis(
        db=db,
        submission=submission,
        branch=branch,
        error_message=payload.error_message,
    )


@router.get(
    "/{submission_id}/analyses",
    response_model=List[AnalysisOut],
    summary="Analysis history for a submission",
    response_description="Every analysis run against this submission, newest first.",
    description=(
        "Returns every comparison run against this submission, newest first, "
        "including failed attempts. Useful for seeing which reference branches "
        "you have already tried."
    ),
    responses={**r.OWNED_RESOURCE},
)
def list_analyses(
    submission_id: SubmissionId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submission = submission_service.get_submission(db, submission_id)
    assert_can_access(submission.owner_id, current_user)

    return (
        db.query(Analysis)
        .filter(Analysis.submission_id == submission.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
