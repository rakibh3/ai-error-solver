"""Admin-only surface: reference repositories and user administration.

Every route here depends on `require_admin`. Nothing in this module is
reachable by a regular USER.
"""
import uuid
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api import responses as r
from app.core.database import get_db
from app.middleware.role_checker import require_admin
from app.models.reference import ReferenceBranch, ReferenceProject
from app.models.user import User
from app.schemas.schemas import (
    AdminProjectOut,
    DeleteResponse,
    IngestAcceptedResponse,
    RepoRequest,
)
from app.schemas.user import RoleUpdateRequest, UserResponse
from app.services import auth_service, reference_service, vector_store_service

router = APIRouter()

ProjectId = Annotated[
    uuid.UUID,
    Path(
        ...,
        description="A reference project id.",
        examples=["3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f607"],
    ),
]


@router.post(
    "/reference-projects",
    response_model=IngestAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a reference repository",
    response_description="The registered project and the branches queued for indexing.",
    description=(
        "Registers a repository as a comparison reference.\n\n"
        "Returns **202 immediately** after enumerating the repository's "
        "branches. Cloning and embedding happen in the background, because a "
        "repository with several branches takes minutes to index and would "
        "otherwise time out behind a proxy.\n\n"
        "Poll `GET /api/v1/admin/reference-projects` for per-branch progress: "
        "each branch moves `pending` → `indexing` → `ready` or `failed`. One "
        "branch failing does not stop the others. Branches only become visible "
        "to regular users once they reach `ready`.\n\n"
        "The project name is derived from the last path segment of the URL, and "
        "must be unique."
    ),
    responses={
        **r.ADMIN_ONLY,
        400: {
            "description": "The repository could not be read, or its name is unusable.",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not read repository: not found"}
                }
            },
        },
        404: {
            "description": "The repository has no branches.",
            "content": {
                "application/json": {
                    "example": {"detail": "No branches found in repository"}
                }
            },
        },
        409: {
            "description": "A reference project with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A reference project named 'fastapi-course' already exists"
                    }
                }
            },
        },
        504: {
            "description": "Timed out contacting the repository.",
            "content": {
                "application/json": {
                    "example": {"detail": "Timed out contacting the repository"}
                }
            },
        },
        **r.VALIDATION,
    },
)
def ingest_reference_project(
    payload: RepoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    project = reference_service.create_reference_project(
        db=db, repo_url=str(payload.repo_url), admin_id=current_user.id
    )
    branch_names = [b.branch_name for b in project.branches]
    background_tasks.add_task(reference_service.ingest_project_branches, project.id)

    return IngestAcceptedResponse(
        project_id=project.id,
        name=project.name,
        branches=branch_names,
        message=f"Indexing {len(branch_names)} branch(es) in the background",
    )


@router.get(
    "/reference-projects",
    response_model=List[AdminProjectOut],
    summary="List reference projects with per-branch indexing status",
    response_description="All reference projects, newest first, with every branch.",
    description=(
        "The administrator's view of the catalog. Unlike "
        "`GET /api/v1/catalog/projects`, this shows **every** branch regardless "
        "of status, includes `repo_url` and `collection_name`, and surfaces the "
        "`error` text for branches that failed to index.\n\n"
        "Use this to monitor an ingestion started with "
        "`POST /api/v1/admin/reference-projects`."
    ),
    responses={**r.ADMIN_ONLY},
)
def list_reference_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return (
        db.query(ReferenceProject).order_by(ReferenceProject.created_at.desc()).all()
    )


@router.get(
    "/reference-projects/health",
    summary="Reconcile the catalog against the vector store",
    response_description="Rows and collections that do not line up.",
    description=(
        "Health check comparing the `reference_branches` table against the "
        "collections that actually exist in Qdrant.\n\n"
        "- `missing_collections` — branches marked `ready` whose collection is "
        "gone; re-index them.\n"
        "- `orphaned_collections` — collections with no owning row, usually "
        "left behind by a failed delete; safe to drop.\n\n"
        "Returns `status: \"error\"` with a message if Qdrant is unreachable."
    ),
    responses={
        **r.ADMIN_ONLY,
        200: {
            "description": "Reconciliation result.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "total_branches": 7,
                        "ready_branches": 6,
                        "missing_collections": [],
                        "orphaned_collections": ["reference_old_project_main_deadbeef"],
                    }
                }
            },
        },
    },
)
def collections_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    return vector_store_service.verify_collections(db)


@router.post(
    "/reference-projects/{project_id}/reindex",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-index a reference project, or one of its branches",
    response_description="Confirmation that re-indexing was queued.",
    description=(
        "Re-clones and re-embeds a project's branches in the background, "
        "returning **202** immediately.\n\n"
        "Pass `?branch=<name>` to re-index a single branch — useful for "
        "retrying one that failed without re-embedding branches that already "
        "succeeded. Omit it to re-index everything.\n\n"
        "The existing collection for each branch is dropped and rebuilt, so a "
        "branch briefly leaves the user-facing catalog while it re-indexes."
    ),
    responses={
        **r.ADMIN_ONLY,
        202: {
            "description": "Re-indexing has been queued.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "accepted",
                        "message": "Re-indexing branch lesson-03-routing",
                    }
                }
            },
        },
        404: {
            "description": "The project, or the named branch, does not exist.",
            "content": {
                "application/json": {
                    "example": {"detail": "Branch 'lesson-99' not found"}
                }
            },
        },
    },
)
def reindex_reference_project(
    background_tasks: BackgroundTasks,
    project_id: ProjectId,
    branch: Optional[str] = Query(
        None,
        description="Re-index only this branch. Omit to re-index all of them.",
        examples=["lesson-03-routing"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    project = (
        db.query(ReferenceProject).filter(ReferenceProject.id == project_id).first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Reference project not found")

    if branch:
        exists = (
            db.query(ReferenceBranch)
            .filter(
                ReferenceBranch.project_id == project.id,
                ReferenceBranch.branch_name == branch,
            )
            .first()
        )
        if not exists:
            raise HTTPException(status_code=404, detail=f"Branch '{branch}' not found")

    background_tasks.add_task(
        reference_service.ingest_project_branches, project.id, branch
    )
    return {
        "status": "accepted",
        "message": f"Re-indexing {'branch ' + branch if branch else 'all branches'}",
    }


@router.delete(
    "/reference-projects/{project_id}",
    response_model=DeleteResponse,
    summary="Delete a reference project, its collections, and its files",
    response_description="Confirmation, including how many collections were dropped.",
    description=(
        "Removes a reference project completely: every branch row, every Qdrant "
        "collection, and the cloned files on disk.\n\n"
        "Analyses that were run against this project are **kept** — their "
        "`branch_id` becomes null rather than the history being deleted. "
        "This cannot be undone."
    ),
    responses={
        **r.ADMIN_ONLY,
        404: {
            "description": "No such reference project.",
            "content": {
                "application/json": {
                    "example": {"detail": "Reference project not found"}
                }
            },
        },
    },
)
def delete_reference_project(
    project_id: ProjectId,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    project = (
        db.query(ReferenceProject).filter(ReferenceProject.id == project_id).first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Reference project not found")
    return reference_service.delete_reference_project(db, project)


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List user accounts",
    response_description="A page of accounts, ordered by id.",
    description=(
        "Paginated list of every account, ordered by id. Use this to find the "
        "`id` you need for a role change."
    ),
    responses={**r.ADMIN_ONLY, **r.VALIDATION},
)
def list_users(
    limit: int = Query(
        50, ge=1, le=200, description="Accounts per page (1-200).", examples=[50]
    ),
    offset: int = Query(0, ge=0, description="Accounts to skip.", examples=[0]),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(User).order_by(User.id).offset(offset).limit(limit).all()


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Change a user's role",
    response_description="The account with its updated role.",
    description=(
        "**The only way to grant administrator access through the API.** "
        "Registration cannot do it, and neither can any other endpoint.\n\n"
        "Demoting the last remaining active administrator is refused with a "
        "**409**, so it is not possible to lock every admin out of the system.\n\n"
        "Unknown fields are rejected: sending anything besides `role` returns "
        "a 422."
    ),
    responses={
        **r.ADMIN_ONLY,
        404: {
            "description": "No account with that id.",
            "content": {"application/json": {"example": {"detail": "User not found"}}},
        },
        409: {
            "description": "Refused: this is the last active administrator.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cannot demote the last remaining active admin"}
                }
            },
        },
        **r.VALIDATION,
    },
)
def update_user_role(
    payload: RoleUpdateRequest,
    user_id: int = Path(..., description="The account to modify.", examples=[42]),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    target = auth_service.get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return auth_service.set_user_role(db, target, payload.role)
