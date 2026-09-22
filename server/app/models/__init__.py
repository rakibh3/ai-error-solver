"""SQLAlchemy models.

Importing this package registers every model on `Base.metadata`, which is what
Alembic autogenerate relies on. Keep every model module imported here.
"""

from app.models.analysis import Analysis, AnalysisStatus
from app.models.reference import BranchStatus, ReferenceBranch, ReferenceProject
from app.models.submission import Submission
from app.models.user import User, UserRole

__all__ = [
    "Analysis",
    "AnalysisStatus",
    "BranchStatus",
    "ReferenceBranch",
    "ReferenceProject",
    "Submission",
    "User",
    "UserRole",
]
