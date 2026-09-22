"""Column types that work on Postgres in production and SQLite in tests.

Postgres is the production database and the only one migrations target. The
`with_variant` fallbacks exist so the test suite can run without a Postgres
server; they are not a supported deployment target.
"""
import enum
from typing import Type

from sqlalchemy import JSON, Enum, Uuid
from sqlalchemy.dialects.postgresql import JSONB as _JSONB
from sqlalchemy.dialects.postgresql import UUID as _UUID


def ValueEnum(enum_cls: Type[enum.Enum], name: str) -> Enum:
    """An Enum column that stores each member's *value*, not its name.

    SQLAlchemy defaults to member names ("INDEXING"), but the migrations create
    the Postgres types from the values ("indexing"). Without this, every query
    or insert touching the column fails with `invalid input value for enum`.
    """
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda members: [m.value for m in members],
    )

# Native uuid on Postgres. On SQLite, the generic `Uuid` type converts uuid.UUID
# to and from text itself; a bare String(36) left sqlite3 unable to bind the
# UUID objects the models pass in.
UUIDType = _UUID(as_uuid=True).with_variant(Uuid(as_uuid=True), "sqlite")

# Generic JSON on SQLite; JSONB on Postgres.
JSONType = _JSONB().with_variant(JSON(), "sqlite")
