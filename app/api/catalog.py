"""The picker: what a logged-in user can compare against.

Only `ready` branches are exposed, and `repo_url` is never returned — it may be
a private URL and a regular user has no reason to see it.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.api import responses as r
from app.core.database import get_db
from app.middleware.role_checker import get_current_user
from app.models.reference import BranchStatus, ReferenceBranch, ReferenceProject
from app.models.user import User
from app.schemas.schemas import CatalogBranchOut, CatalogProjectOut

router = APIRouter()


@router.get(
    "/projects",
    response_model=List[CatalogProjectOut],
    summary="List reference projects available for comparison",
    response_description="Projects with at least one indexed branch.",
    description=(
        "**Step 1 of the comparison flow.**\n\n"
        "Lists the reference repositories an administrator has indexed. Only "
        "projects with at least one `ready` branch appear — a project still "
        "being indexed is invisible here until it has something comparable.\n\n"
        "`repo_url` is intentionally omitted from this response; it may point "
        "at a private repository."
    ),
    responses={**r.AUTHENTICATED},
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(ReferenceProject)
        .join(ReferenceBranch, ReferenceBranch.project_id == ReferenceProject.id)
        .filter(ReferenceBranch.status == BranchStatus.READY)
        .order_by(ReferenceProject.name)
        .all()
    )

    # De-duplicate the join and count ready branches per project.
    seen = {}
    for project in rows:
        if project.id in seen:
            continue
        ready = sum(1 for b in project.branches if b.status == BranchStatus.READY)
        seen[project.id] = CatalogProjectOut(
            id=project.id, name=project.name, ready_branch_count=ready
        )
    return list(seen.values())


@router.get(
    "/projects/{project_id}/branches",
    response_model=List[CatalogBranchOut],
    summary="List the comparable branches of a reference project",
    response_description="Indexed branches, alphabetically by name.",
    description=(
        "**Step 2 of the comparison flow.**\n\n"
        "Lists the branches of one reference project that are ready to compare "
        "against. Take the `id` of the branch you want and pass it as "
        "`branch_id` to `POST /api/v1/submissions/{submission_id}/analyze`.\n\n"
        "Branches still `pending`, `indexing`, or `failed` are not shown. If a "
        "project exists but none of its branches are ready yet, this returns "
        "**404** rather than an empty list."
    ),
    responses={**r.AUTHENTICATED, **r.NOT_FOUND},
)
def list_branches(
    project_id: uuid.UUID = Path(
        ...,
        description="A project id from `GET /api/v1/catalog/projects`.",
        examples=["3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f607"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(ReferenceProject).filter(ReferenceProject.id == project_id).first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Not found")

    branches = [b for b in project.branches if b.status == BranchStatus.READY]
    if not branches:
        raise HTTPException(
            status_code=404, detail="This project has no indexed branches yet"
        )

    branches.sort(key=lambda b: b.branch_name)
    return branches
