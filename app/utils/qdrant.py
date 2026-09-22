import re
import uuid

from qdrant_client import QdrantClient

from app.core import config


def get_qdrant_client() -> QdrantClient:
    """Initialize and return a Qdrant client."""
    return QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)


def build_collection_name(project_name: str, branch_name: str) -> str:
    """Build a collection name for a (project, branch) pair.

    A short uuid suffix keeps the name unique even when two different
    (project, branch) pairs sanitize to the same string — e.g. `feature/a` and
    `feature-a`. The result is persisted on `reference_branches.collection_name`
    and never parsed back apart; `parse_collection_name` used to guess the split
    from underscores and got it wrong for any project name containing one.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", f"{project_name}_{branch_name}".lower()).strip("_")
    return f"reference_{slug}_{uuid.uuid4().hex[:8]}"


def sanitize_path_segment(segment: str) -> str:
    """Make a git ref or repo name safe to use as a single directory name.

    A branch named `../evil` is legal in git and would otherwise traverse out
    of the project directory when joined onto a path.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", segment).strip("._-")
    if not cleaned or cleaned in (".", ".."):
        raise ValueError(f"Unusable path segment: {segment!r}")
    return cleaned[:100]
