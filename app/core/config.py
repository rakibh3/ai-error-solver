import os
from urllib.parse import quote

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    """Read an int from the environment, falling back to `default` if unset or unparseable."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

# Database Configuration
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = _int_env("POSTGRES_PORT", 5432)


def _build_database_url() -> str | None:
    """Assemble the SQLAlchemy URL, or None if the credentials are missing.

    User and password are percent-encoded: both come from the environment and
    a `@`, `/` or `:` in either would otherwise split the URL in the wrong place.
    """
    if not (POSTGRES_USER and POSTGRES_PASSWORD and POSTGRES_DB):
        return None
    user = quote(POSTGRES_USER, safe="")
    password = quote(POSTGRES_PASSWORD, safe="")
    return f"postgresql://{user}:{password}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


DATABASE_URL = _build_database_url()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = _int_env("QDRANT_PORT", 6333)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

# Admin seeding (scripts/seed_admin.py only — never read by the request path)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_FULLNAME = os.getenv("ADMIN_FULLNAME", "Administrator")

# Upload limits
MAX_UPLOAD_BYTES = _int_env("MAX_UPLOAD_BYTES", 25 * 1024 * 1024)
MAX_EXTRACTED_BYTES = _int_env("MAX_EXTRACTED_BYTES", 50 * 1024 * 1024)
MAX_ARCHIVE_MEMBERS = _int_env("MAX_ARCHIVE_MEMBERS", 2000)
MAX_MEMBER_BYTES = _int_env("MAX_MEMBER_BYTES", 10 * 1024 * 1024)

# Per-user quotas
USER_SUBMISSION_QUOTA = _int_env("USER_SUBMISSION_QUOTA", 5)
USER_STORAGE_QUOTA_BYTES = _int_env("USER_STORAGE_QUOTA_BYTES", 200 * 1024 * 1024)

# Retrieval / analysis
RETRIEVAL_K = _int_env("RETRIEVAL_K", 8)
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "gemini-2.5-flash")
MAX_ERROR_MESSAGE_CHARS = _int_env("MAX_ERROR_MESSAGE_CHARS", 8000)
MAX_STUDENT_CONTEXT_CHARS = _int_env("MAX_STUDENT_CONTEXT_CHARS", 60000)
MAX_CANDIDATE_FILES = _int_env("MAX_CANDIDATE_FILES", 12)

# Rate limits (slowapi syntax)
AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "10/minute")
ANALYZE_RATE_LIMIT = os.getenv("ANALYZE_RATE_LIMIT", "10/hour")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "20/hour")

# Storage roots
REFERENCE_PROJECTS_DIR = os.getenv("REFERENCE_PROJECTS_DIR", "instructor_projects")
SUBMISSIONS_DIR = os.getenv("SUBMISSIONS_DIR", "student_projects")

genai.configure(api_key=GEMINI_API_KEY)
