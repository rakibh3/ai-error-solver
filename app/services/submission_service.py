"""User-owned code submissions.

Two path-injection holes from the previous student_service are closed here:
the user-supplied `project_name` form field was joined into the storage path
(so `../../` escaped the directory), and `file.filename` was joined in for the
temporary zip. Neither value touches the filesystem now — the submission UUID
is the only path component.
"""
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import config
from app.models.submission import Submission
from app.models.user import User, UserRole
from app.utils import archive

logger = logging.getLogger(__name__)

CHUNK = 1024 * 1024


def _storage_root() -> Path:
    return Path(config.SUBMISSIONS_DIR)


def _submission_dir(submission_id: UUID) -> Path:
    return _storage_root() / str(submission_id)


def _enforce_quota(db: Session, owner: User) -> None:
    if owner.role == UserRole.ADMIN:
        return

    count = db.query(func.count(Submission.id)).filter(
        Submission.owner_id == owner.id
    ).scalar() or 0
    if count >= config.USER_SUBMISSION_QUOTA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Submission limit reached ({config.USER_SUBMISSION_QUOTA}). "
                "Delete an existing submission first."
            ),
        )

    used = db.query(func.coalesce(func.sum(Submission.total_bytes), 0)).filter(
        Submission.owner_id == owner.id
    ).scalar() or 0
    if used >= config.USER_STORAGE_QUOTA_BYTES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Storage quota exceeded. Delete an existing submission first.",
        )


def _spool_upload(file: UploadFile, tmpdir: Path) -> Path:
    """Stream the upload to disk, enforcing the size cap as we go.

    The previous implementation called `file.file.read()`, loading the whole
    upload into memory before any check.
    """
    zip_path = tmpdir / "upload.zip"
    written = 0
    head = b""

    with open(zip_path, "wb") as dst:
        while True:
            chunk = file.file.read(CHUNK)
            if not chunk:
                break
            if not head:
                head = chunk[:4]
            written += len(chunk)
            if written > config.MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        f"Upload exceeds the {config.MAX_UPLOAD_BYTES} byte limit"
                    ),
                )
            dst.write(chunk)

    if written == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Verify by magic bytes, not by the client-supplied filename.
    if not archive.is_zip_magic(head):
        raise HTTPException(status_code=400, detail="Uploaded file is not a zip archive")

    return zip_path


def create_submission(
    db: Session, owner: User, display_name: str, file: UploadFile
) -> Submission:
    _enforce_quota(db, owner)

    submission_id = uuid4()
    final_dir = _submission_dir(submission_id)
    final_dir.parent.mkdir(parents=True, exist_ok=True)

    # Extract into a temp dir and move into place only once it validates.
    tmp_parent = tempfile.mkdtemp(prefix="submission_", dir=str(final_dir.parent))
    tmp_parent_path = Path(tmp_parent)
    staging = tmp_parent_path / "extracted"

    try:
        zip_path = _spool_upload(file, tmp_parent_path)

        try:
            archive.safe_extract(
                zip_path=zip_path,
                dest_root=staging,
                max_members=config.MAX_ARCHIVE_MEMBERS,
                max_total_bytes=config.MAX_EXTRACTED_BYTES,
                max_member_bytes=config.MAX_MEMBER_BYTES,
            )
        except archive.UnsafeArchiveError as e:
            raise HTTPException(status_code=400, detail=str(e))

        archive.prune_noise(staging)
        file_count, total_bytes = archive.measure_tree(staging)

        if file_count == 0:
            raise HTTPException(
                status_code=400, detail="Archive contained no usable files"
            )

        shutil.move(str(staging), str(final_dir))

        submission = Submission(
            id=submission_id,
            owner_id=owner.id,
            display_name=display_name.strip()[:255],
            storage_path=str(final_dir),
            file_count=file_count,
            total_bytes=total_bytes,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    except Exception:
        # Roll back both sides: no orphan row, no orphan directory.
        db.rollback()
        shutil.rmtree(final_dir, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(tmp_parent_path, ignore_errors=True)


def get_submission(db: Session, submission_id: UUID) -> Submission:
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Not found")
    return submission


def list_submissions(db: Session, current_user: User) -> List[Submission]:
    query = db.query(Submission)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Submission.owner_id == current_user.id)
    return query.order_by(Submission.created_at.desc()).all()


def delete_submission(db: Session, submission: Submission) -> dict:
    path = Path(submission.storage_path)
    submission_id = submission.id

    db.delete(submission)  # cascades to analyses
    db.commit()

    # Only remove a path that is actually inside the storage root.
    try:
        root = _storage_root().resolve()
        resolved = path.resolve()
        if resolved != root and root in resolved.parents:
            shutil.rmtree(resolved, ignore_errors=True)
    except OSError as e:
        logger.warning("Could not remove directory for submission %s: %s", submission_id, e)

    return {"status": "success", "message": f"Submission {submission_id} deleted"}
