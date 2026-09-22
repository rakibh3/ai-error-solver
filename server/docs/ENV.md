# Environment Variables

Generated from `.env.example`. `app/core/config.py` calls `load_dotenv()` at
import, so every variable below is read from `.env` (gitignored) or the real
environment. **Required** means there is no in-code default — unset, the app
fails with a message naming the variable rather than guessing.

## Secrets and connections

| Variable | Required | Purpose | Read by |
|---|---|---|---|
| `JWT_SECRET_KEY` | Yes | Signs and verifies the HS256 bearer tokens; changing it invalidates every issued token. | `core/security.py`, `middleware/role_checker.py` |
| `POSTGRES_USER` | Yes | DB role — Compose creates it, the app connects as it. | `config.py`, `docker-compose.yml` |
| `POSTGRES_PASSWORD` | Yes | Password for that role; percent-encoded into the URL, so `@ : /` are safe. | same |
| `POSTGRES_DB` | Yes | Database name Compose creates and the app opens. | same |
| `POSTGRES_HOST` | No (`localhost`) | Where the app dials; stays `localhost` while Postgres runs in Compose. | `config.py` |
| `POSTGRES_PORT` | No (`5432`) | Port for the same, and the host port Compose publishes. | `config.py`, Compose |
| `OPENROUTER_API_KEY` | Yes | Authenticates chat generation; every analysis bills against it. | `rag/analyzer.py` |
| `OPENROUTER_BASE_URL` | No (`https://openrouter.ai/api/v1`) | Endpoint the `openai` SDK targets — override only for a proxy or mock. | `rag/analyzer.py` |
| `OPENROUTER_SITE_URL` | No (unset) | Optional `HTTP-Referer` for your openrouter.ai ranking; omitted when blank. | `rag/analyzer.py` |
| `OPENROUTER_APP_TITLE` | No (`Error Navigator`) | Optional `X-OpenRouter-Title` for the same listing. | `rag/analyzer.py` |
| `VOYAGE_API_KEY` | Yes | Authenticates embeddings — still needed, since OpenRouter routes chat, not embeddings. | `rag/analyzer.py`, `services/indexing_service.py` |
| `QDRANT_HOST` | No (`localhost`) | Vector-store host; combined with the port into `QDRANT_URL`. | `config.py` |
| `QDRANT_PORT` | No (`6333`) | Qdrant REST port — the one the client speaks. | `config.py`, Compose |
| `QDRANT_API_KEY` | No (unset) | Sent on every Qdrant call; harmlessly ignored by an unsecured local container. | `utils/qdrant.py` |
| `QDRANT_GRPC_PORT` | No (`6334`) | Published by Compose only; the app does not use gRPC. | `docker-compose.yml` |
| `QDRANT_LOG_LEVEL` | No (`INFO`) | Log verbosity inside the Qdrant container only. | `docker-compose.yml` |

## Admin seeding

Read **only** by `scripts/seed_admin.py`, never on the request path — this is the
only way to create the first admin, since registration always produces a `USER`.

| Variable | Required | Purpose |
|---|---|---|
| `ADMIN_EMAIL` | For the script | Login identity of the seeded admin; re-running is idempotent. |
| `ADMIN_PASSWORD` | For the script | Its password, minimum 12 characters; re-running with a new value resets it. |
| `ADMIN_FULLNAME` | No (`Administrator`) | Display name on that account. |

## Models

| Variable | Required | Purpose |
|---|---|---|
| `ANALYSIS_MODEL` | Yes | OpenRouter `vendor/model` slug that writes the fix; swapping models is an edit here, not a code change. |
| `EMBEDDING_MODEL` | Yes | Voyage model used for **both** indexing and retrieval — changing it invalidates every existing Qdrant collection and requires a full re-index. |
| `ANALYSIS_TIMEOUT_SECONDS` | No (`60`) | Per-request ceiling on the model call; raise for slow reasoning models, lower to fail fast. |

## Storage roots

| Variable | Required | Purpose |
|---|---|---|
| `REFERENCE_PROJECTS_DIR` | No (`instructor_projects`) | Where admin reference repos are cloned, one directory per project/branch. |
| `SUBMISSIONS_DIR` | No (`student_projects`) | Where user uploads are extracted, one directory per submission UUID. |

## Rate limits

slowapi syntax (`count/period`). Keyed by bearer token when present, else by IP,
so one user behind a NAT cannot exhaust everyone's budget.

| Variable | Default | Purpose | Raise it / lower it |
|---|---|---|---|
| `AUTH_RATE_LIMIT` | `10/minute` | Throttles register and login. | Looser invites credential stuffing; tighter frustrates real logins. |
| `UPLOAD_RATE_LIMIT` | `20/hour` | Throttles zip uploads. | Looser costs disk and CPU; tighter blocks iterative work. |
| `ANALYZE_RATE_LIMIT` | `10/hour` | Throttles analysis — the only endpoint that spends money. | Looser raises your OpenRouter and Voyage bill directly; tighter caps spend per user. |

## Size and count limits

Byte values are exact binary sizes (1 MB = 1 048 576 B).

| Variable | Bytes | MB | GB | What it counts | Raise it → / Lower it → |
|---|---|---|---|---|---|
| `MAX_UPLOAD_BYTES` | 26 214 400 | 25 | 0.024 | The compressed zip, measured while streaming to disk. | Accepts bigger projects, more bandwidth and disk per request / rejects with **413** sooner. |
| `MAX_EXTRACTED_BYTES` | 52 428 800 | 50 | 0.049 | Total bytes written during extraction — the zip-bomb ceiling. | Tolerates higher compression ratios, risks filling the disk / rejects legitimately large repos. |
| `MAX_MEMBER_BYTES` | 10 485 760 | 10 | 0.010 | Any single file inside the zip. | Allows large individual files such as media or datasets / blocks them while still accepting the archive. |
| `USER_STORAGE_QUOTA_BYTES` | 209 715 200 | 200 | 0.195 | Total on-disk bytes across one user's submissions. | More disk per user / users hit **409** sooner and must delete a submission. |

| Variable | Default | What it counts | Raise it → / Lower it → |
|---|---|---|---|
| `MAX_ARCHIVE_MEMBERS` | 2 000 | Entries in the zip — guards the many-tiny-files bomb. | Allows larger trees, slower extraction / rejects big repos. |
| `USER_SUBMISSION_QUOTA` | 5 | Stored submissions per user, checked before upload. | More parallel projects per user / forces cleanup sooner. |
| `RETRIEVAL_K` | 8 | Reference chunks pulled from Qdrant per analysis. | More context and cost, and can dilute the relevant chunk / cheaper and faster, risks missing the matching file. |
| `MAX_ERROR_MESSAGE_CHARS` | 8 000 | Length of the pasted error; enforced as a Pydantic `max_length`. | Accepts full tracebacks / rejects long ones with **422**. |
| `MAX_STUDENT_CONTEXT_CHARS` | 60 000 | Budget for submitted code in the prompt (≈15 000 tokens at ~4 chars each). | More of the user's code reaches the model at higher token cost / risks truncating away the buggy file. |
| `MAX_CANDIDATE_FILES` | 12 | Files considered for that budget, ranked by how strongly the traceback names them. | Broader search, budget split thinner / narrower, favours the files the error actually mentions. |

The three analysis limits interact: files are scored against the traceback, the
top `MAX_CANDIDATE_FILES` are taken, and they are packed into
`MAX_STUDENT_CONTEXT_CHARS` highest-scoring first, then shortest first — so the
budget buys the most files rather than one enormous one.
