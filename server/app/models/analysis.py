import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models.types import JSONType, UUIDType

from app.core.database import Base


class AnalysisStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"


class Analysis(Base):
    """The result of comparing one submission against one reference branch."""

    __tablename__ = "analyses"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    submission_id = Column(
        UUIDType,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUIDType,
        ForeignKey("reference_branches.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message = Column(Text, nullable=False)
    status = Column(Enum(AnalysisStatus, name="analysisstatus"), nullable=False)
    result = Column(JSONType, nullable=True)
    raw_response = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    submission = relationship("Submission", back_populates="analyses")
    branch = relationship("ReferenceBranch")
