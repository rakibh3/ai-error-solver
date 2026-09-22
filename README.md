# Error Navigator API

AI-powered error solver. An administrator curates reference repositories and
indexes their branches; any registered user uploads their own codebase, picks a
reference branch to compare against, and receives a step-by-step fix with file,
line, and exact replacement.

## Roles

There are exactly two roles: `ADMIN` and `USER`.

Registration is open to the public and **always** creates a `USER`. The
registration schema has no `role` field and rejects one with a 422 — it is not
silently ignored. Admin access is granted only by:

1. `scripts/seed_admin.py`, from `ADMIN_EMAIL` / `ADMIN_PASSWORD`; or
2. `PATCH /api/v1/admin/users/{id}/role`, by an existing admin.

The second refuses to demote the last remaining active admin.

## Setup

```bash
cp .env.example .env          # then fill it in
uv sync                       # regenerates uv.lock — see "Dependencies" below
alembic upgrade head          # on an EXISTING db, see "Migrating" first
ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='at-least-12-chars' \
  uv run python -m scripts.seed_admin
uv run uvicorn main:app --reload
```

Requires Postgres and Qdrant. `python create_db.py` checks the database
connection.

### Postgres and Qdrant via Docker

`docker-compose.yml` runs just the two stateful dependencies; the API itself
stays on the host, so the `localhost` URLs in `.env` work unmodified.

```bash
docker compose up -d          # postgres on 5432, qdrant on 6333 (REST) / 6334 (gRPC)
docker compose ps             # both should report healthy
alembic upgrade head
```

Both ports are published on `127.0.0.1` only. Data lives in the named volumes
`pgdata` and `qdrant_storage` and survives `docker compose down`; add `-v` to
delete it.

`POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` in `.env` are the single
source of truth: Compose provisions the container from them and
`app/core/config.py` builds the SQLAlchemy URL from the same values, so there is
no separate `DATABASE_URL` to keep in sync. None of the three has a default —
`docker compose up` fails with a named variable rather than booting a database
under a guessed password.

Qdrant runs unsecured locally (dashboard at <http://localhost:6333/dashboard>).
To require an API key, set `QDRANT_API_KEY` in `.env` and uncomment
`QDRANT__SERVICE__API_KEY` in `docker-compose.yml`.

### Migrating an existing database

The pre-existing `users` table is not managed by Alembic. Baseline it first so
revision 0001 is not replayed:

```bash
docker compose exec postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT role, count(*) FROM users GROUP BY role;"   # record this
alembic stamp 0001_baseline_users
alembic upgrade head
```

Revision `0002` collapses the role enum. Every non-`ADMIN` row — including
every existing `INSTRUCTOR` — becomes `USER`. Instructors are deliberately not
promoted: registration previously accepted a client-supplied role, so any
`INSTRUCTOR` row may have been self-assigned. Promote real admins afterwards
with the seed script.

## API

| Method | Path | Who |
|---|---|---|
| POST | `/api/v1/auth/register` | public (always creates USER) |
| POST | `/api/v1/auth/login` | public |
| GET | `/api/v1/auth/me` | any authenticated user |
| GET | `/api/v1/catalog/projects` | any authenticated user |
| GET | `/api/v1/catalog/projects/{project_id}/branches` | any authenticated user |
| POST | `/api/v1/submissions` | any authenticated user |
| GET | `/api/v1/submissions` | own only; admin sees all |
| GET | `/api/v1/submissions/{submission_id}` | owner or admin |
| DELETE | `/api/v1/submissions/{submission_id}` | owner or admin |
| POST | `/api/v1/submissions/{submission_id}/analyze` | owner or admin |
| GET | `/api/v1/submissions/{submission_id}/analyses` | owner or admin |
| POST | `/api/v1/admin/reference-projects` | admin |
| GET | `/api/v1/admin/reference-projects` | admin |
| POST | `/api/v1/admin/reference-projects/{project_id}/reindex` | admin |
| DELETE | `/api/v1/admin/reference-projects/{project_id}` | admin |
| GET | `/api/v1/admin/reference-projects/health` | admin |
| GET | `/api/v1/admin/users` | admin |
| PATCH | `/api/v1/admin/users/{user_id}/role` | admin |

Accessing another user's resource returns **404**, not 403 — a 403 would
confirm the id exists.

### Typical user flow

```bash
TOKEN=$(curl -s localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"Password123"}' | jq -r .token.access_token)

curl -s localhost:8000/api/v1/catalog/projects -H "Authorization: Bearer $TOKEN"
curl -s localhost:8000/api/v1/catalog/projects/$PROJECT_ID/branches -H "Authorization: Bearer $TOKEN"

SID=$(curl -s -X POST localhost:8000/api/v1/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -F display_name='My Project' -F file=@project.zip | jq -r .id)

curl -s -X POST localhost:8000/api/v1/submissions/$SID/analyze \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"branch_id":"'"$BRANCH_ID"'","error_message":"NameError: name '\''retrun'\'' is not defined"}'
```

Admin ingestion returns `202` immediately and indexes in the background; poll
`GET /api/v1/admin/reference-projects` for per-branch status
(`pending` → `indexing` → `ready` | `failed`).

## Dependencies

`uv.lock` predates this change and must be regenerated with `uv sync` or
`uv lock`. Notably, `bcrypt` was missing from the lock entirely even though
`passlib` is configured with the bcrypt scheme — password hashing could not
have worked on a clean install. It is now a direct dependency.

`psycopg2` was replaced with `psycopg2-binary` to avoid requiring `pg_config`
at install time.

## Tests

```bash
uv run pytest                                   # SQLite in-memory
TEST_DATABASE_URL=postgresql://... uv run pytest # what CI should run
```

SQLite will not catch enum, JSONB, or `server_default` issues, and the
migrations are Postgres-only — run the suite against Postgres before releasing.

## Limits

Configured in `.env`; see `.env.example` for every knob. Defaults: 25 MB
upload, 50 MB extracted, 2000 archive members, 5 submissions and 200 MB per
user, 10 analyses/hour.
