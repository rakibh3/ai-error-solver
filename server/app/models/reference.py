import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.models.types import UUIDType

from app.core.database import Base


class BranchStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class ReferenceProject(Base):
    """A repository the admin ingested as a comparison reference."""

    __tablename__ = "reference_projects"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    repo_url = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    branches = relationship(
        "ReferenceBranch",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReferenceBranch(Base):
    """One branch of a reference project == one Qdrant collection.

    `collection_name` is stored rather than re-derived. The old
    `parse_collection_name` heuristic guessed the project/branch split from
    underscores and mis-split anything with an underscore in the project name.
    """

    __tablename__ = "reference_branches"
    __table_args__ = (
        UniqueConstraint("project_id", "branch_name", name="uq_reference_branch"),
    )

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUIDType,
        ForeignKey("reference_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_name = Column(String(255), nullable=False)
    collection_name = Column(String(255), unique=True, nullable=False)
    status = Column(
        Enum(BranchStatus, name="branchstatus"),
        default=BranchStatus.PENDING,
        server_default=BranchStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    error = Column(Text, nullable=True)
    files_indexed = Column(Integer, nullable=True)
    chunks_indexed = Column(Integer, nullable=True)
    indexed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project = relationship("ReferenceProject", back_populates="branches")
