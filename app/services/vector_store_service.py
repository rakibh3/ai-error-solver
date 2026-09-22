"""Vector-store views driven by the database rather than by Qdrant enumeration.

`get_all_indexed_projects` used to list Qdrant collections and guess the
project/branch split back out of each collection name. The catalog now reads
`reference_branches`, which stores that mapping explicitly.
"""
import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.reference import BranchStatus, ReferenceBranch
from app.utils.qdrant import get_qdrant_client

logger = logging.getLogger(__name__)


def verify_collections(db: Session) -> Dict[str, Any]:
    """Admin health check: reconcile `reference_branches` against Qdrant.

    Reports rows marked ready whose collection is missing, and collections with
    no owning row (leaked by a failed delete).
    """
    try:
        client = get_qdrant_client()
        live = {c.name for c in client.get_collections().collections}
    except Exception as e:
        return {"status": "error", "message": f"Could not reach Qdrant: {e}"}

    rows = db.query(ReferenceBranch).all()
    known = {r.collection_name for r in rows}

    missing = [
        {
            "branch_id": str(r.id),
            "branch_name": r.branch_name,
            "collection_name": r.collection_name,
        }
        for r in rows
        if r.status == BranchStatus.READY and r.collection_name not in live
    ]

    orphaned = sorted(
        name for name in live if name.startswith("reference_") and name not in known
    )

    return {
        "status": "success",
        "total_branches": len(rows),
        "ready_branches": sum(1 for r in rows if r.status == BranchStatus.READY),
        "missing_collections": missing,
        "orphaned_collections": orphaned,
    }
