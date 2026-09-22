# Plan — Self-Service Error Navigator (Admin-owned references, open user registration)

Status: proposed · Target branch: `feature/self-service-analysis` · Author: planning pass, 2026-09-22

---

## 1. What changes and why

**Today**

- Three roles: `ADMIN`, `INSTRUCTOR`, `STUDENT`.
- An instructor indexes a repo, and the instructor (not the student) calls `POST /api/v1/index/compare` on the student's behalf. The student's only action is uploading a zip.
- `role` is accepted from the registration request body, so anyone can self-register as `ADMIN`.
- Nothing about a submission is stored in Postgres — `student_projects/` on disk *is* the database, and no row ties a submission to a user.

**Target**

- Two roles: `ADMIN` and `USER`. `INSTRUCTOR` is removed; every instructor-only capability becomes admin-only.
- Registration is open to the public but **always** creates a `USER`. The `role` field is removed from the registration contract entirely — it is not merely ignored, it is not accepted.
- Admin status can only be granted out-of-band (seed script / admin-only promotion endpoint), never through the public API.
- The admin embeds reference repositories. A logged-in user browses the catalog of indexed projects/branches, picks the one to compare against, and runs the analysis themselves. No human is in the loop.
- Submissions and analysis results become first-class database rows owned by a user.

**Why the persistence change is not optional:** once the user drives the comparison, every request must answer "is this submission yours?". That question cannot be answered from a directory listing. Ownership has to live in Postgres before the endpoints can be safely opened up.

---

## 2. Role model

```python
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER  = "USER"
```

| Capability | Before | After |
|---|---|---|
| Index a reference repo | INSTRUCTOR or ADMIN | **ADMIN** |
| Re-index / list / delete references | INSTRUCTOR or ADMIN (delete: ADMIN) | **ADMIN** |
| Browse indexed catalog | INSTRUCTOR or ADMIN | **any authenticated user** (ready branches only) |
| Upload own codebase | STUDENT | **any authenticated user** |
| Run comparison | INSTRUCTOR or ADMIN | **owner of the submission** (admin may run any) |
| View analysis history | — (not stored) | **owner** (admin: all) |
| List all submissions | INSTRUCTOR or ADMIN | **ADMIN** |
| Delete a submission | ADMIN | **owner or ADMIN** |
| Promote a user to admin | — | **ADMIN only**, out of the public surface |

### Protecting admin status

Four layers, all required:

1. **Schema** — `UserCreate` has no `role` field. An extra `role` key in the JSON is rejected, not silently dropped: set `model_config = ConfigDict(extra="forbid")`.
2. **Service** — `auth_service.create_user` hardcodes `role=UserRole.USER`. It never reads a role from its input.
3. **Seeding** — `scripts/seed_admin.py` reads `ADMIN_EMAIL` / `ADMIN_PASSWORD` from the environment and upserts exactly one admin. Idempotent, safe to re-run, refuses to run if `ADMIN_PASSWORD` is unset or shorter than 12 chars.
4. **Promotion** — optional `PATCH /api/v1/admin/users/{id}/role`, admin-only, which refuses to demote the last remaining active admin (guard against locking yourself out).

Anything that writes `role` outside those two code paths is a bug; add a test that asserts it.

---

## 3. Data model

New tables. All timestamps `timestamptz`, default `now()`.

### `reference_projects` (what the admin embedded)

| column | type | notes |
|---|---|---|
| `id` | uuid PK | |
| `name` | text, unique | derived from repo URL |
| `repo_url` | text | |
| `created_by` | int FK `users.id` | the admin who ingested it |
| `created_at` | timestamptz | |

### `reference_branches` (one row per Qdrant collection)

| column | type | notes |
|---|---|---|
| `id` | uuid PK | |
| `project_id` | uuid FK `reference_projects.id` ON DELETE CASCADE | |
| `branch_name` | text | unique together with `project_id` |
| `collection_name` | text, unique | **stored**, never re-derived |
| `status` | enum(`pending`,`indexing`,`ready`,`failed`) | catalog exposes `ready` only |
| `error` | text null | failure reason |
| `files_indexed` / `chunks_indexed` | int null | |
| `indexed_at` | timestamptz null | |

> This table deletes `app/utils/qdrant.py::parse_collection_name` outright. That function guesses the project/branch split from underscores against a hardcoded branch-name list and mis-splits anything like `feature/login-v2` or a project whose name ends in `test`. Storing `collection_name` alongside its `(project, branch)` makes the guess unnecessary.

### `submissions` (a user's uploaded codebase)

| column | type | notes |
|---|---|---|
| `id` | uuid PK | also the on-disk directory name |
| `owner_id` | int FK `users.id` ON DELETE CASCADE, indexed | |
| `display_name` | text | user-supplied label — **never** used to build a path |
| `storage_path` | text | `student_projects/{id}` |
| `file_count` / `total_bytes` | int / bigint | for quota enforcement |
| `created_at` | timestamptz | |

### `analyses` (result of one comparison)

| column | type | notes |
|---|---|---|
| `id` | uuid PK | |
| `submission_id` | uuid FK `submissions.id` ON DELETE CASCADE | |
| `branch_id` | uuid FK `reference_branches.id` ON DELETE SET NULL | |
| `error_message` | text | the error the user pasted |
| `status` | enum(`success`,`failed`) | |
| `result` | jsonb null | validated `{error_explanation, fix_instructions{...}}` |
| `raw_response` | text null | kept for debugging model output |
| `model` | text | e.g. `gemini-2.5-flash` |
| `created_at` | timestamptz, indexed | |

Persisting `analyses` gives the user a history view and gives you the only dataset worth having later: which fixes were suggested, for which error, against which branch.

---

## 4. API surface

### Public

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/auth/register` | open; always creates `USER`; `role` rejected |
| POST | `/api/v1/auth/login` | unchanged |

### Authenticated (any role)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/catalog/projects` | reference projects having ≥1 `ready` branch |
| GET | `/api/v1/catalog/projects/{project_id}/branches` | `ready` branches only — this is the picker |
| POST | `/api/v1/submissions` | multipart: `display_name`, `file` (zip) → `{submission_id}` |
| GET | `/api/v1/submissions` | own only; admin sees all |
| GET | `/api/v1/submissions/{id}` | owner or admin |
| DELETE | `/api/v1/submissions/{id}` | owner or admin; removes rows + directory + nothing in Qdrant |
| POST | `/api/v1/submissions/{id}/analyze` | body `{branch_id, error_message}` → runs RAG, stores + returns an `analyses` row |
| GET | `/api/v1/submissions/{id}/analyses` | history, newest first |

### Admin only

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/admin/reference-projects` | body `{repo_url}` → clones all branches, indexes in background, returns `202` + project id |
| GET | `/api/v1/admin/reference-projects` | includes `pending`/`indexing`/`failed` branches |
| POST | `/api/v1/admin/reference-projects/{id}/reindex` | optional `?branch=` for a single branch |
| DELETE | `/api/v1/admin/reference-projects/{id}` | drops collections, directory, and rows |
| GET | `/api/v1/admin/users` | paginated |
| PATCH | `/api/v1/admin/users/{id}/role` | optional; last-admin guard |

### Removed

`POST /api/v1/index/compare` (admin-driven comparison), `GET /api/v1/student/student-projects`, `POST /api/v1/student/upload`, and the whole `/api/v1/project` + `/api/v1/index` routers as currently shaped. Their logic moves, it is not deleted.

---

## 5. Implementation phases

### Phase 0 — Alembic baseline (prerequisite)

**Dependency preconditions — check these first.** `uv.lock` is missing packages the code already assumes or that the phases below require:

| Package | Needed by | Status |
|---|---|---|
| `bcrypt` | `CryptContext(schemes=["bcrypt"])` in `app/core/security.py:9` and `app/middleware/role_checker.py:13` | **absent from `uv.lock`** — passlib has no backend to hash with, so `hash_password` raises and *registration and login cannot work on a clean `uv sync`*. Fix before anything else. |
| `alembic` | Every migration below | absent |
| `email-validator` (`pydantic[email]`) | `EmailStr` in Phase 1 | absent |
| `pytest`, `pytest-asyncio`, `httpx` | Phase 8 | absent (`httpx` is present only transitively) |
| `slowapi` | Phase 5 rate limits | absent |

Verify the bcrypt failure before assuming it is theoretical — `uv sync && uv run python -c "from app.core.security import hash_password; print(hash_password('abcdefgh'))"`. If it raises `UnknownBackendError`, that alone is a production outage on the current `production` branch.


`Base.metadata.create_all()` in `main.py:10` cannot perform any of the changes below. Before touching models:

```bash
uv add alembic
alembic init --template pyproject alembic
```

- In `alembic/env.py`: import every model module, then `target_metadata = Base.metadata`; read the URL from `app.core.config.DATABASE_URL` rather than hardcoding it in `alembic.ini` (keeps the password out of a committed file).
- Baseline the existing database so the current `users` table isn't re-created: generate an initial revision matching today's schema, then `alembic stamp head` against the live DB.
- Remove `Base.metadata.create_all(bind=engine)` from `main.py`; migrations become the only schema path.
- Verify with `alembic upgrade head` on a scratch database created from `create_db.py`.

**Deliverables:** `alembic/`, `alembic.ini`, revision 0001 (baseline), `main.py` no longer creates tables.

---

### Phase 1 — Roles and registration lockdown

1. `app/models/user.py` — enum becomes `ADMIN` / `USER`, column default `USER`.
2. Migration `0002_roles_admin_user`:

```sql
ALTER TYPE userrole RENAME TO userrole_old;
CREATE TYPE userrole AS ENUM ('ADMIN', 'USER');
ALTER TABLE users ALTER COLUMN role DROP DEFAULT;
ALTER TABLE users ALTER COLUMN role TYPE userrole
  USING (CASE WHEN role::text = 'ADMIN' THEN 'ADMIN' ELSE 'USER' END)::userrole;
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'USER';
DROP TYPE userrole_old;
```

   **Decision — existing `INSTRUCTOR` rows map to `USER`, not `ADMIN`.** Instructor duties become admin duties, so promoting them is the tempting read. Don't: because registration currently accepts a client-supplied role, any existing `INSTRUCTOR` row may have been self-assigned by an anonymous signup. Demote everyone, then promote the real admins deliberately via the seed script. Record how many rows were affected before running it:
   `SELECT role, count(*) FROM users GROUP BY role;`

3. `app/schemas/user.py` — drop `role` from `UserCreate`, add `extra="forbid"`, switch `email` to `EmailStr` (it is a bare `str` today, so `not-an-email` currently registers fine; add `uv add "pydantic[email]"`), keep the 8-char minimum but raise it to 10 with a basic complexity check now that signup is public.
4. `app/services/auth_service.py` — `create_user` sets `role=UserRole.USER` literally.
5. `app/middleware/role_checker.py` — delete `require_instructor_or_admin` and `require_role`; keep `get_current_user` and `require_admin`; **rewrite** `require_owner_or_admin`, which is currently broken (it takes `resource_owner_id` as a plain parameter, so FastAPI would bind it as a query parameter if it were ever used as a dependency). Replace with an explicit helper called inside the handler:

```python
def assert_can_access(resource_owner_id: int, current_user: User) -> None:
    if current_user.role != UserRole.ADMIN and current_user.id != resource_owner_id:
        raise HTTPException(status_code=404, detail="Not found")
```

   Return `404`, not `403`, on someone else's resource — `403` confirms the id exists.
6. `scripts/seed_admin.py` + a `README` note on running it.

**Tests:** registering with `{"role": "ADMIN"}` → `422`; registering normally → `USER`; seed script is idempotent; last-admin demotion is refused.

---

### Phase 2 — Catalog and submission persistence

1. New models in `app/models/`: `reference.py` (`ReferenceProject`, `ReferenceBranch`, `BranchStatus`), `submission.py` (`Submission`), `analysis.py` (`Analysis`, `AnalysisStatus`).
2. Migration `0003_catalog_and_submissions`.
3. `app/schemas/` — `CatalogProjectOut`, `CatalogBranchOut`, `SubmissionOut`, `AnalyzeRequest {branch_id: UUID, error_message: str = Field(min_length=1, max_length=8000)}`, `AnalysisOut`, `FixInstruction`.
4. **Backfill decision:** existing directories under `instructor_projects/` and `student_projects/` have no owner and no repo URL. Do not attempt to adopt them. Write `scripts/backfill_references.py` to register *instructor* projects against the seeded admin by scanning Qdrant collections (their content is still valid), and discard existing student uploads — they are anonymous by construction. State this in the release notes.

---

### Phase 3 — Admin ingestion, made asynchronous

Today `index_instructor_project` clones every branch and embeds every chunk inside the request. A repo with a handful of branches will hold the connection open for minutes and time out behind any proxy.

1. `app/services/reference_service.py` (from `instructor_service.py`):
   - `create_reference_project(db, repo_url, admin_id)` — `git ls-remote --heads` to enumerate branches, insert the project plus one `reference_branches` row per branch at `status=pending`, return immediately with `202`.
   - Clone + index runs via `BackgroundTasks` (single-process) with each branch transitioning `pending → indexing → ready|failed` and `error` populated on failure. A branch that fails must not block the others — the current loop already does this correctly; preserve that.
   - Storage stays `instructor_projects/{project_name}/{branch}/`, but sanitize both segments: a branch named `../evil` is legal in git and currently becomes a directory traversal in `parent_path / branch`.
2. `app/services/indexing_service.py` — mostly unchanged (the ignore lists, 1000/200 chunking, SHA-256 dedupe, `voyage-code-3` embeddings all stay). Two changes: take `collection_name` as an argument instead of computing it, and return counts for the status row.
3. `app/services/vector_store_service.py` — `get_all_indexed_projects` stops enumerating Qdrant collections and reads `reference_branches` instead; keep a thin `verify_collections()` admin health check that reports DB rows with no matching collection and vice versa.
4. Delete `parse_collection_name`.

> **Scaling note, deliberately deferred:** `BackgroundTasks` dies with the process, so an interrupted restart leaves rows stuck at `indexing`. Acceptable for a single-instance deployment if you add a startup sweep that marks stale `indexing` rows as `failed`. Move to a real queue only when you run more than one worker — don't build it now.

---

### Phase 4 — User self-service flow

1. `app/api/catalog.py` — the two read endpoints, `ready` branches only. Cache-friendly, no admin data leaked (don't expose `repo_url` to non-admins; it may be a private URL).
2. `app/api/submissions.py` — upload, list, get, delete, analyze, history. Every handler that takes an `{id}` loads the row and calls `assert_can_access` before anything else.
3. `app/services/submission_service.py` (from `student_service.py`):
   - Extract to `student_projects/{submission_id}/` — the UUID only. **`display_name` never touches the filesystem.** Today `os.path.join("student_projects", project_name, uuid)` takes `project_name` straight from a form field, so `../../` escapes the directory; with open registration that becomes remotely exploitable by anyone.
   - Same for the saved zip: `file.filename` is currently joined into a path unsanitized.
   - Row is written first, files second; on any extraction failure, roll back the row and `rmtree` the directory.
4. `app/services/analysis_service.py` — signature becomes `run_analysis(db, submission, branch, error_message)`: resolve the collection from `branch.collection_name`, call the analyzer, validate, persist an `analyses` row, return it. It no longer takes loose strings from the request body, which is what made the old `/compare` trivially able to read any submission.

---

### Phase 5 — Upload hardening (blocking for public launch)

Open registration turns the upload path into an anonymous-attacker surface. All of these are required before the endpoint ships:

- **Zip-slip** — `zipfile.extractall` is called directly today (`student_service.py:28`). Replace with a member-by-member loop: reject absolute paths, any component equal to `..`, and any symlink entries; resolve each destination and assert it stays under the submission directory.
- **Zip bombs** — cap total uncompressed size (suggest 50 MB), member count (suggest 2,000), and per-member size using `ZipInfo.file_size` *before* writing; abort on breach.
- **Upload size** — reject the request body above ~25 MB before buffering. `file.file.read()` currently loads the whole upload into memory; stream to a temp file in chunks instead.
- **Content type** — accept `.zip` only, verified by magic bytes, not by the client-supplied filename.
- **Per-user quota** — e.g. 5 active submissions and 200 MB total per `USER`; enforced from `submissions.total_bytes`, so it needs Phase 2.
- **Rate limits** — `slowapi` or equivalent: login and register per-IP; `analyze` per-user (it costs a Voyage embedding call plus a Gemini call, so an unthrottled loop bills you directly).
- **Extraction sandbox** — extract into a temp dir and move into place only after validation passes.

---

### Phase 6 — Analysis quality

The current analyzer has three problems that get much worse when users drive it directly.

1. **Whole-codebase prompt.** `analysis_service` concatenates every matching file into one string, sends it as the prompt *and* uses it as the retrieval query. Instead: build the retrieval query from the error message plus any file paths parsed out of the traceback; select at most N candidate student files by relevance to those paths; cap the assembled context by token budget with a documented truncation order.
2. **Unvalidated model output.** The prompt asks for JSON but `analyzer.py` returns `response.text` raw, and the interpolation `{[doc.page_content for doc in relevant_docs]}` embeds a Python list repr into the prompt. Fix the interpolation to use the already-formatted `instructor_context` variable (which is built and then never used), strip ``` fences, `json.loads`, validate against a Pydantic `AnalysisResult`, and on parse failure store `status=failed` with `raw_response` rather than handing the caller malformed JSON.
3. **Prompt injection.** Reference repos are admin-supplied so they are trusted, but the user's own code and error message are not — and they now reach the model without review. Fence user content explicitly and instruct the model to treat it as data. The blast radius is limited (the output is JSON shown back to the same user), but the fencing is nearly free.

Also raise `k=5` to a configurable `RETRIEVAL_K`, and filter the search by `project_name`/`branch_name` payload metadata as defence in depth against a collection-name mix-up.

---

### Phase 7 — Remove the old surface

- Delete `app/api/project.py`, `app/api/index.py`, `app/api/student.py`; register `auth`, `catalog`, `submissions`, `admin` routers in `main.py`.
- Delete `app/services/instructor_service.py` and `app/services/student_service.py` once their logic has moved.
- Fix the cross-import in `app/api/index.py:12` (it imports a guard from `app.api.project`) by deleting both files.
- Update the FastAPI `description` and `openapi_tags` in `main.py:12` — they still describe the instructor-mediated flow.
- Remove the `print()` debugging in `app/api/auth.py:27` (it prints the login payload, password included, to stdout) and `student_service.py:9`.
- Fix `auth_service.login:144`: the failed-login log line reads `user.email` after `user` has been reassigned to `None`, so a bad login raises `AttributeError` instead of returning `401`. Capture the email before authenticating.

---

### Phase 8 — Tests

`app/tests/` is empty. Minimum set before launch, with `pytest`, `httpx.AsyncClient`, and a throwaway Postgres schema per run:

- **Auth:** role cannot be set at registration (`422`); default role is `USER`; login with a wrong password returns `401` (regression test for the `AttributeError` above); expired/garbage token → `401`.
- **Authorization matrix:** for every endpoint, assert anonymous / `USER` / other-`USER` / `ADMIN` each get the expected status. Table-driven — this is the test that protects the whole redesign.
- **Ownership:** user B gets `404` on user A's submission for GET, DELETE, analyze, and history.
- **Upload security:** zip-slip archive is rejected; oversized archive is rejected; `display_name` of `../../etc` produces a directory named after the UUID.
- **Catalog:** `pending`/`failed` branches are invisible to a `USER` and visible to an `ADMIN`.
- **Analysis:** with Voyage and Gemini stubbed, a malformed model response is stored as `failed` rather than raising.

---

## 6. Rollout

1. Merge Phase 0 and run `alembic stamp head` in production before anything else.
2. Set `ADMIN_EMAIL` / `ADMIN_PASSWORD`; deploy Phase 1; run `seed_admin.py`; verify `SELECT email, role FROM users WHERE role='ADMIN'` returns only the intended account.
3. Deploy Phases 2–4 together — they are one schema and one API surface; splitting them leaves the API half-migrated.
4. Phase 5 gates the public announcement. Do not open registration before the zip handling is fixed.
5. Phases 6–8 can land incrementally after launch, except the `auth_service.login` fix in Phase 7, which should be pulled forward into Phase 1.

**Config additions for `.env.example`:** `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `MAX_UPLOAD_BYTES`, `MAX_EXTRACTED_BYTES`, `MAX_ARCHIVE_MEMBERS`, `USER_SUBMISSION_QUOTA`, `RETRIEVAL_K`, `ANALYZE_RATE_LIMIT`.

---

## 7. Open questions

1. **Does a user pick a project *and* a branch, or just a branch?** The plan assumes a two-step picker (project → branch) because branches represent course stages. A flat list of `project/branch` pairs is simpler if the catalog stays small.
2. **Email verification.** Open registration without it means unlimited throwaway accounts against your Gemini and Voyage billing. The per-user rate limit in Phase 5 is the cheap mitigation; verification is the real one. Out of scope here — worth deciding before launch.
3. **Retention.** Submissions accumulate on local disk forever. Suggest a TTL (e.g. delete submissions older than 30 days, keep the `analyses` rows) — not planned above.
4. **"IF FLAT NOTA"** — unparsed. This phrase from the requirements has not been translated into anything in this plan. If it names a specific error-finding mode, matching strategy, or UI, Phase 6 is where it belongs; needs clarification.
