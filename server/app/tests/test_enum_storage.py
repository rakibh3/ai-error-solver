"""Enum columns must store exactly the labels the Postgres migrations create.

SQLAlchemy's Enum defaults to member *names* ("INDEXING") while migration 0003
created `branchstatus`/`analysisstatus` from the *values* ("indexing"). SQLite
accepts either, so the rest of the suite cannot catch a mismatch; these tests
pin the stored strings to the migration definitions instead.
"""
import uuid

from sqlalchemy import text

from app.models.analysis import Analysis
from app.models.reference import BranchStatus, ReferenceBranch, ReferenceProject
from app.models.user import User

# Labels as created in alembic/versions/0002 and 0003.
MIGRATION_LABELS = {
    "branchstatus": ["pending", "indexing", "ready", "failed"],
    "analysisstatus": ["success", "failed"],
    "userrole": ["ADMIN", "USER"],
}


def test_enum_columns_match_migration_labels():
    for column in (ReferenceBranch.__table__.c.status, Analysis.__table__.c.status, User.__table__.c.role):
        enum_type = column.type
        assert enum_type.name in MIGRATION_LABELS, enum_type.name
        assert list(enum_type.enums) == MIGRATION_LABELS[enum_type.name], enum_type.name


def test_branch_status_is_persisted_as_its_value(db_session):
    project = ReferenceProject(name=f"p-{uuid.uuid4().hex[:6]}", repo_url="https://example.com/p.git")
    db_session.add(project)
    db_session.flush()
    branch = ReferenceBranch(
        project_id=project.id,
        branch_name="main",
        collection_name=f"reference_{uuid.uuid4().hex}",
        status=BranchStatus.INDEXING,
    )
    db_session.add(branch)
    db_session.commit()

    raw = db_session.execute(text("SELECT status FROM reference_branches")).scalar_one()
    assert raw == "indexing"

    found = db_session.query(ReferenceBranch).filter(ReferenceBranch.status == BranchStatus.INDEXING).one()
    assert found.status is BranchStatus.INDEXING
