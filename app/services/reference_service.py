"""Admin-owned reference repositories: ingestion, indexing, deletion.

Ingestion is asynchronous. The old implementation cloned every branch and
embedded every chunk inside the request, which holds the connection open for
minutes and times out behind any proxy. Now the request enumerates branches and
returns 202; the clone+index runs in the background, and each branch carries its
own status so one bad branch does not sink the others.
"""
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import config
from app.core.database import SessionLocal
from app.models.reference import BranchStatus, ReferenceBranch, ReferenceProject
from app.services import indexing_service
from app.utils.qdrant import build_collection_name, get_qdrant_client, sanitize_path_segment

logger = logging.getLogger(__name__)

GIT_TIMEOUT_SECONDS = 300


def _project_root(project_name: str) -> Path:
    return Path(config.REFERENCE_PROJECTS_DIR) / sanitize_path_segment(project_name)


def _branch_dir(project_name: str, branch_name: str) -> Path:
    return _project_root(project_name) / sanitize_path_segment(branch_name)


def _derive_project_name(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


def list_remote_branches(repo_url: str) -> List[str]:
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url],
            capture_output=True,
            text=True,
            check=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timed out contacting the repository")
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=400, detail=f"Could not read repository: {e.stderr.strip()}"
        )

    branches = [
        line.split("\t")[-1].replace("refs/heads/", "")
        for line in result.stdout.strip().split("\n")
        if line.strip()
    ]
    if not branches:
        raise HTTPException(status_code=404, detail="No branches found in repository")
    return branches


def create_reference_project(db: Session, repo_url: str, admin_id: int) -> ReferenceProject:
    """Register a project and one pending row per branch. Does not index."""
    repo_url = str(repo_url)
    project_name = _derive_project_name(repo_url)

    try:
        sanitize_path_segment(project_name)
    except ValueError:
        raise HTTPException(status_code=400, detail="Could not derive a usable project name")

    if db.query(ReferenceProject).filter(ReferenceProject.name == project_name).first():
        raise HTTPException(
            status_code=409,
            detail=f"A reference project named '{project_name}' already exists",
        )

    branches = list_remote_branches(repo_url)

    project = ReferenceProject(name=project_name, repo_url=repo_url, created_by=admin_id)
    db.add(project)
    db.flush()

    for branch in branches:
        try:
            sanitize_path_segment(branch)
        except ValueError:
            logger.warning("Skipping unusable branch name %r", branch)
            continue
        db.add(
            ReferenceBranch(
                project_id=project.id,
                branch_name=branch,
                collection_name=build_collection_name(project_name, branch),
                status=BranchStatus.PENDING,
            )
        )

    db.commit()
    db.refresh(project)
    return project


def ingest_project_branches(project_id: UUID, only_branch: Optional[str] = None) -> None:
    """Background worker: clone and index each pending branch.

    Owns its own session — the request's session is closed by the time this
    runs.
    """
    db = SessionLocal()
    try:
        project = db.query(ReferenceProject).filter(ReferenceProject.id == project_id).first()
        if not project:
            logger.error("Reference project %s vanished before indexing", project_id)
            return

        query = db.query(ReferenceBranch).filter(ReferenceBranch.project_id == project_id)
        if only_branch:
            query = query.filter(ReferenceBranch.branch_name == only_branch)

        for branch in query.all():
            _ingest_single_branch(db, project, branch)
    finally:
        db.close()


def _ingest_single_branch(
    db: Session, project: ReferenceProject, branch: ReferenceBranch
) -> None:
    branch.status = BranchStatus.INDEXING
    branch.error = None
    db.commit()

    branch_dir = _branch_dir(project.name, branch.branch_name)

    try:
        if branch_dir.exists():
            shutil.rmtree(branch_dir)
        branch_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                "git", "clone", "--branch", branch.branch_name, "--single-branch",
                "--depth", "1", project.repo_url, str(branch_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )

        git_dir = branch_dir / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

        result = indexing_service.index_reference_branch(
            project_name=project.name,
            branch_name=branch.branch_name,
            project_path=str(branch_dir),
            collection_name=branch.collection_name,
        )

        if result.get("status") == "success":
            branch.status = BranchStatus.READY
            branch.files_indexed = result.get("files_indexed")
            branch.chunks_indexed = result.get("unique_chunks_indexed")
            branch.indexed_at = datetime.now(timezone.utc)
            branch.error = None
        else:
            branch.status = BranchStatus.FAILED
            branch.error = str(result.get("error", "Unknown indexing error"))[:2000]

    except subprocess.TimeoutExpired:
        branch.status = BranchStatus.FAILED
        branch.error = "Timed out cloning the branch"
    except subprocess.CalledProcessError as e:
        branch.status = BranchStatus.FAILED
        branch.error = f"Clone failed: {(e.stderr or '').strip()[:2000]}"
    except Exception as e:  # one branch failing must not sink the rest
        logger.exception("Indexing failed for %s/%s", project.name, branch.branch_name)
        branch.status = BranchStatus.FAILED
        branch.error = str(e)[:2000]

    db.commit()


def delete_reference_project(db: Session, project: ReferenceProject) -> dict:
    """Drop the Qdrant collections, the directory, and the rows."""
    client = get_qdrant_client()
    dropped = []
    for branch in project.branches:
        try:
            client.delete_collection(branch.collection_name)
            dropped.append(branch.collection_name)
        except Exception as e:
            logger.warning(
                "Could not drop collection %s: %s", branch.collection_name, e
            )

    try:
        root = _project_root(project.name)
        if root.exists():
            shutil.rmtree(root)
    except (OSError, ValueError) as e:
        logger.warning("Could not remove directory for %s: %s", project.name, e)

    name = project.name
    db.delete(project)  # cascades to reference_branches
    db.commit()

    return {
        "status": "success",
        "message": f"Deleted reference project '{name}' and {len(dropped)} collection(s)",
    }


def sweep_stale_indexing(db: Session) -> int:
    """Mark rows left at `indexing` by a process restart as failed.

    BackgroundTasks dies with the process, so an interrupted restart would
    otherwise strand branches at `indexing` forever.
    """
    stale = db.query(ReferenceBranch).filter(
        ReferenceBranch.status == BranchStatus.INDEXING
    ).all()
    for branch in stale:
        branch.status = BranchStatus.FAILED
        branch.error = "Indexing interrupted by a server restart; re-index to retry."
    if stale:
        db.commit()
    return len(stale)
