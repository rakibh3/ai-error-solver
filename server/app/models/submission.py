import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models.types import UUIDType

from app.core.database import Base


class Submission(Base):
    """A codebase a user uploaded for comparison.

    `id` is the on-disk directory name. `display_name` is a user-supplied label
    and never participates in path construction.
    """

    __tablename__ = "submissions"

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name = Column(String(255), nullable=False)
    storage_path = Column(Text, nullable=False)
    file_count = Column(Integer, nullable=False, server_default="0")
    total_bytes = Column(BigInteger, nullable=False, server_default="0")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    analyses = relationship(
        "Analysis",
        back_populates="submission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
