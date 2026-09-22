import os
from urllib.parse import quote, urlparse

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    """Read a boolean from the environment (1/true/yes/on), falling back to `default`."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    """Read an int from the environment, falling back to `default` if unset or unparseable."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# LLM provider. OpenRouter speaks the OpenAI chat-completions protocol, so the
# `openai` SDK is pointed at its base URL rather than a dedicated client.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
# Optional attribution headers; they only affect your listing on openrouter.ai.
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL")
OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "Error Navigator")

# Embeddings still go to Voyage directly -- OpenRouter routes chat, not embeddings.
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

# Tokens carry only an email, so anyone who knows the key can mint an admin
# token. Refuse to start with a missing, short, or published placeholder key.
_JWT_PLACEHOLDERS = {"your-super-secret-jwt-key-change-this-in-production"}
_JWT_MIN_BYTES = 32
if (
    not JWT_SECRET_KEY
    or JWT_SECRET_KEY in _JWT_PLACEHOLDERS
    or len(JWT_SECRET_KEY.encode()) < _JWT_MIN_BYTES
):
    raise RuntimeError(
        f"JWT_SECRET_KEY must be a random secret of at least {_JWT_MIN_BYTES} bytes "
        "(not the .env.example placeholder). Generate one with: "
        "python -c 'import secrets; print(secrets.token_urlsafe(48))'"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

# Qdrant Configuration
# QDRANT_URL wins when set (e.g. a managed cluster's https:// endpoint);
# otherwise it is assembled from scheme, host and port.
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = _int_env("QDRANT_PORT", 6333)
QDRANT_SCHEME = os.getenv("QDRANT_SCHEME", "http").strip().lower()
QDRANT_URL = os.getenv("QDRANT_URL") or f"{QDRANT_SCHEME}://{QDRANT_HOST}:{QDRANT_PORT}"
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
# Optional key restricted to reads; used by the analysis path so a request that
# only retrieves can never write. Falls back to QDRANT_API_KEY when unset.
QDRANT_READ_ONLY_API_KEY = os.getenv("QDRANT_READ_ONLY_API_KEY") or None

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _check_qdrant_transport(url: str, api_key: str | None) -> None:
    """Refuse to start when Qdrant is off-host without auth or over plain HTTP.

    Qdrant holds every reference repository. On loopback (local dev, Compose
    ports bound to 127.0.0.1) anything goes; anywhere else it needs an API key,
    and that key must not travel in cleartext.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in _LOOPBACK_HOSTS:
        return
    if not api_key:
        raise RuntimeError(
            f"QDRANT_API_KEY is required when Qdrant is not on localhost (host: {host!r})."
        )
    if parsed.scheme != "https":
        raise RuntimeError(
            f"Qdrant at {host!r} must use https:// (set QDRANT_URL or QDRANT_SCHEME=https) "
            "so the API key is not sent in cleartext."
        )


_check_qdrant_transport(QDRANT_URL, QDRANT_API_KEY)

# Interactive API docs (/docs, /redoc, and the OpenAPI schema). On by default
# for development; set ENABLE_API_DOCS=false on a publicly reachable API.
ENABLE_API_DOCS = _bool_env("ENABLE_API_DOCS", True)

# Hosts an admin may register reference repositories from. Anything else is
# rejected, which keeps `git ls-remote`/`git clone` from reaching internal
# hosts. Set to "*" to allow any public https host.
REPO_ALLOWED_HOSTS = {
    h.strip().lower()
    for h in os.getenv("REPO_ALLOWED_HOSTS", "github.com,gitlab.com,bitbucket.org,codeberg.org").split(",")
    if h.strip()
}

# Admin seeding (scripts/seed_admin.py only — never read by the request path)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_FULLNAME = os.getenv("ADMIN_FULLNAME", "Administrator")

_MB = 1024 * 1024


def _mb_env(name: str, default_mb: int) -> int:
    """Read a size configured in megabytes (`<NAME>_MB`) and return it in bytes.

    Falls back to the legacy byte-valued `<NAME>_BYTES` variable so existing
    deployments keep their limits, then to `default_mb`. Non-positive or
    unparseable values are ignored.
    """
    raw = os.getenv(f"{name}_MB")
    if raw is not None and raw.strip():
        try:
            mb = float(raw)
            if mb > 0:
                return int(mb * _MB)
        except ValueError:
            pass
    legacy = _int_env(f"{name}_BYTES", 0)
    return legacy if legacy > 0 else default_mb * _MB


# Upload limits (configured in MB, used in bytes)
MAX_UPLOAD_BYTES = _mb_env("MAX_UPLOAD", 25)
MAX_EXTRACTED_BYTES = _mb_env("MAX_EXTRACTED", 50)
MAX_ARCHIVE_MEMBERS = _int_env("MAX_ARCHIVE_MEMBERS", 2000)
MAX_MEMBER_BYTES = _mb_env("MAX_MEMBER", 10)

# Per-user quotas
USER_SUBMISSION_QUOTA = _int_env("USER_SUBMISSION_QUOTA", 5)
USER_STORAGE_QUOTA_BYTES = _mb_env("USER_STORAGE_QUOTA", 200)

# Retrieval / analysis
RETRIEVAL_K = _int_env("RETRIEVAL_K", 8)
# Model names live in the environment, never in code -- no in-code default, so
# swapping a model is an .env edit and a restart.
#
# ANALYSIS_MODEL is an OpenRouter slug (`vendor/model`), not a bare provider
# model name. EMBEDDING_MODEL is a Voyage model and goes to Voyage directly.
#
# EMBEDDING_MODEL must match what the existing Qdrant collections were built
# with: vectors from a different model are not comparable, and a model with a
# different dimension will fail outright. Changing it means re-indexing every
# reference branch.
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
# The SDK default is 10 minutes, which outlives any sane request.
ANALYSIS_TIMEOUT_SECONDS = _int_env("ANALYSIS_TIMEOUT_SECONDS", 60)
MAX_ERROR_MESSAGE_CHARS = _int_env("MAX_ERROR_MESSAGE_CHARS", 8000)
MAX_STUDENT_CONTEXT_CHARS = _int_env("MAX_STUDENT_CONTEXT_CHARS", 60000)
MAX_CANDIDATE_FILES = _int_env("MAX_CANDIDATE_FILES", 12)

# Rate limits (slowapi syntax)
AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "10/minute")
# Per-account cap on login attempts, whatever IP they come from.
LOGIN_EMAIL_RATE_LIMIT = os.getenv("LOGIN_EMAIL_RATE_LIMIT", "20/hour")
ANALYZE_RATE_LIMIT = os.getenv("ANALYZE_RATE_LIMIT", "10/hour")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "20/hour")

# Storage roots
REFERENCE_PROJECTS_DIR = os.getenv("REFERENCE_PROJECTS_DIR", "instructor_projects")
SUBMISSIONS_DIR = os.getenv("SUBMISSIONS_DIR", "student_projects")