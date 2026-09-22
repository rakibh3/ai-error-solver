"""Column types that work on Postgres in production and SQLite in tests.

Postgres is the production database and the only one migrations target. The
`with_variant` fallbacks exist so the test suite can run without a Postgres
server; they are not a supported deployment target.
"""
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB as _JSONB
from sqlalchemy.dialects.postgresql import UUID as _UUID

# CHAR(36) on SQLite; native uuid on Postgres.
UUIDType = _UUID(as_uuid=True).with_variant(String(36), "sqlite")

# Generic JSON on SQLite; JSONB on Postgres.
JSONType = _JSONB().with_variant(JSON(), "sqlite")
