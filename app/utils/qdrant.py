from typing import Optional, Dict
from qdrant_client import QdrantClient
from app.core import config


def get_qdrant_client() -> QdrantClient:
    """Initialize and return a Qdrant client"""
    return QdrantClient(
        host=config.QDRANT_HOST,
        port=config.QDRANT_PORT,
        api_key=config.QDRANT_API_KEY
    )


def get_collection_name(project_name: str, branch_name: str) -> str:
    """Generate a valid collection name for Qdrant"""
    safe_name = f"instructor_project_{project_name}_{branch_name}"
    safe_name = "".join(c if c.isalnum() or c == '_' else '_' for c in safe_name)
    return safe_name.lower()


def parse_collection_name(collection_name: str) -> Optional[Dict[str, str]]:
    """
    Parse collection name to extract project and branch information.
    
    Handles most common cases with a balanced approach between simplicity and accuracy.
    """
    if not collection_name.startswith("instructor_project_"):
        return None
    
    # Remove the prefix
    remainder = collection_name[len("instructor_project_"):]
    
    # Split by underscore
    parts = remainder.split('_')
    
    if len(parts) < 2:
        return None
    
    # Common single-word branches
    common_branches = {
        'main', 'master', 'dev', 'development', 'staging', 'production',
        'test', 'testing', 'beta', 'alpha', 'rc', 'setup'
    }
    
    # Try last part as branch if it's a common branch name
    if parts[-1] in common_branches:
        return {
            "project_name": '_'.join(parts[:-1]),
            "branch_name": parts[-1]
        }
    
    # Look for multi-word branch patterns
    # Check for patterns like feature_*, bugfix_*, hotfix_*, release_*, part_*
    branch_prefixes = ['feature', 'bugfix', 'hotfix', 'release', 'part']
    
    # Try to find where a branch prefix starts (working backwards)
    for i in range(len(parts) - 1, 0, -1):  # Start from second-to-last and work backwards
        if parts[i] in branch_prefixes and i < len(parts) - 1:
            # Found a branch prefix, everything from here is the branch
            return {
                "project_name": '_'.join(parts[:i]),
                "branch_name": '_'.join(parts[i:])
            }
    
    # Default fallback: assume last part is branch, rest is project
    # This handles most cases including numbers, versions, etc.
    return {
        "project_name": '_'.join(parts[:-1]),
        "branch_name": parts[-1]
    } 