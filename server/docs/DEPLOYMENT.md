# Deploying the API to a VPS (nginx + GitHub Actions CI/CD)

A step-by-step guide for putting the **FastAPI server** (`server/`) on a Linux VPS
behind nginx with HTTPS, and wiring up a pipeline so every push to the
`production` branch is tested and deployed automatically.

The Next.js client (`client/`) is **not** covered here. Where the client's
location changes a server setting, that is called out
(see [Where the client runs](#where-the-client-runs--forwarded_allow_ips)).

> Written for a first deployment. Every step says **what** to run, **why**, and
> **how to check it worked**. Do the steps in order; do not skip the checks.

---

## Contents

1. [How it fits together](#1-how-it-fits-together)
2. [What you need before starting](#2-what-you-need-before-starting)
3. [Prepare the VPS (one time)](#3-prepare-the-vps-one-time)
4. [Install the software (one time)](#4-install-the-software-one-time)
5. [Get the code onto the VPS (one time)](#5-get-the-code-onto-the-vps-one-time)
6. [Write the production `.env`](#6-write-the-production-env)
7. [Start Postgres and Qdrant](#7-start-postgres-and-qdrant)
8. [Install dependencies, migrate, create the admin](#8-install-dependencies-migrate-create-the-admin)
9. [Run the API as a systemd service](#9-run-the-api-as-a-systemd-service)
10. [Put nginx in front](#10-put-nginx-in-front)
11. [Point the domain and turn on HTTPS](#11-point-the-domain-and-turn-on-https)
12. [The deploy script](#12-the-deploy-script)
13. [The CI/CD pipeline (GitHub Actions)](#13-the-cicd-pipeline-github-actions)
14. [Your first automatic deploy](#14-your-first-automatic-deploy)
15. [Day-to-day operations](#15-day-to-day-operations)
16. [Rollback](#16-rollback)
17. [Backups](#17-backups)
18. [Troubleshooting](#18-troubleshooting)
19. [Go-live checklist](#19-go-live-checklist)

Placeholders used throughout. Replace them with your own values:

| Placeholder | Meaning | Example |
|---|---|---|
| `203.0.113.10` | Your VPS public IP | from your VPS provider's dashboard |
| `api.example.com` | The domain the API will live on | `api.error-navigator.com` |
| `deploy` | The Linux user that owns and runs the app | keep as is |
| `/srv/error-solver` | Where the repo is cloned on the VPS | keep as is |

---

## 1. How it fits together

```
                       Internet
                          │  HTTPS :443 (HTTP :80 only redirects)
                          ▼
┌─────────────────────────── VPS (Ubuntu 24.04) ───────────────────────────┐
│                                                                          │
│   ufw firewall: only 22 (SSH), 80, 443 are open                           │
│                          │                                               │
│                    ┌─────▼─────┐   TLS certificate from Let's Encrypt    │
│                    │   nginx   │   (certbot renews it automatically)     │
│                    └─────┬─────┘                                         │
│                          │ http://127.0.0.1:8000                         │
│                 ┌────────▼─────────┐                                     │
│                 │ uvicorn main:app │  systemd service "error-solver-api" │
│                 │   (1 worker)     │  runs as user "deploy"              │
│                 └──┬────────────┬──┘                                     │
│     127.0.0.1:5432 │            │ 127.0.0.1:6333                         │
│             ┌──────▼───┐   ┌────▼─────┐                                  │
│             │ Postgres │   │  Qdrant  │   Docker containers from         │
│             └──────────┘   └──────────┘   server/docker-compose.yml      │
└──────────────────────────────────────────────────────────────────────────┘

    GitHub  ── push to "production" ──►  GitHub Actions
                                          1. run tests (real Postgres)
                                          2. check migrations apply cleanly
                                          3. SSH into the VPS → scripts/deploy.sh
                                          4. smoke-test https://api.example.com/
```

**Why this shape?**

- `docker-compose.yml` already runs only Postgres and Qdrant and binds them to
  `127.0.0.1`, with the app on the host. Production uses the same layout, so
  there are no new Dockerfiles to maintain and dev matches prod.
- **nginx** terminates HTTPS, enforces the upload size limit early, and keeps
  uvicorn off the public internet.
- **systemd** starts the API on boot, restarts it if it crashes, and collects its logs.
- **Exactly one uvicorn worker.** This is required, not a tuning choice:
  - The rate limiter (`app/core/limiter.py`) keeps its counters **in process
    memory**. With 4 workers, every user would get 4× the limits, including
    the login-attempt cap and the paid `/analyze` budget.
  - Indexing runs in `BackgroundTasks` inside the process, and the startup hook
    marks any branch still at `indexing` as failed. If a second worker
    restarted, it would fail jobs that another worker was still running.

  If you outgrow one worker, first move the limiter to Redis storage and
  indexing to a real job queue. Adding workers before that breaks both.

---

## 2. What you need before starting

- **A VPS** running **Ubuntu 24.04 LTS**, with at least 2 vCPU, 4 GB RAM, and
  40 GB disk. Qdrant, Postgres, and zip extraction all use memory and disk.
  Any provider works (Hetzner, DigitalOcean, Vultr, Linode, and so on).
- **A domain** you control, so you can add a DNS record (for example `api.example.com`).
- **Admin access to the GitHub repo**, so you can add secrets and deploy keys.
- **API keys** for OpenRouter and Voyage.
- On **your laptop**: an SSH key. Check with `ls ~/.ssh/id_ed25519.pub`. If it
  is missing, create one with `ssh-keygen -t ed25519`.

### The three SSH keys (read this first, it's the #1 source of confusion)

| # | Key | Private half lives in | Public half goes in | Used for |
|---|---|---|---|---|
| 1 | Your personal key | your laptop `~/.ssh/id_ed25519` | VPS `~deploy/.ssh/authorized_keys` | You logging in to the VPS |
| 2 | **CI key** | GitHub secret `SSH_PRIVATE_KEY` | VPS `~deploy/.ssh/authorized_keys` | GitHub Actions logging in to deploy |
| 3 | **Repo deploy key** | VPS `~deploy/.ssh/github_deploy` | GitHub → repo → Settings → Deploy keys | The VPS running `git fetch` |

Keep them separate. If one leaks, you revoke only that one.

---

## 3. Prepare the VPS (one time)

### 3.1 First login as root

```bash
# on your laptop
ssh root@203.0.113.10
```

### 3.2 Update the system

```bash
apt update && apt -y upgrade
apt -y install unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades   # choose "Yes": automatic security patches
timedatectl set-timezone UTC                 # logs and JWT expiry in one timezone
```

### 3.3 Create the `deploy` user

```bash
adduser --disabled-password --gecos "" deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys   # key #1
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh && chmod 600 /home/deploy/.ssh/authorized_keys
```

`deploy` gets **no** general sudo. Later it gets permission to restart exactly
one service ([§9.3](#93-let-deploy-restart-only-this-service)).

**Check.** Open a **new** terminal on your laptop and keep the root session
open until this works:

```bash
ssh deploy@203.0.113.10     # must log in without a password
```

### 3.4 Lock down SSH

Only do this after the check above passes. Otherwise you can lock yourself out.

```bash
# as root
cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
sshd -t && systemctl reload ssh     # sshd -t validates first; a typo would kill SSH
```

### 3.5 Firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status            # should list 22, 80, 443 only
```

> **Docker and ufw.** Docker publishes ports by writing its own iptables rules,
> which **bypass ufw**. That is why `docker-compose.yml` binds Postgres and
> Qdrant to `127.0.0.1:...`. **Never** change those to `"5432:5432"` or
> `0.0.0.0`. Doing so would put your database on the internet even with ufw on.

Optional but recommended: `apt -y install fail2ban`. The default config bans
IPs that brute-force SSH.

---

## 4. Install the software (one time)

Run as **root** (or with `sudo`).

### 4.1 Base packages, nginx, certbot

```bash
apt -y install git curl ca-certificates nginx certbot python3-certbot-nginx
```

`git` is **required at runtime**, not just for deploying. Reference
repositories are fetched with `git ls-remote` and `git clone`
(`app/services/reference_service.py`).

### 4.2 Docker Engine + Compose plugin

Follow Docker's official Ubuntu instructions (apt repository method), then:

```bash
usermod -aG docker deploy     # let deploy run `docker compose` without sudo
```

> Membership in the `docker` group is effectively root on this machine. That is
> acceptable here because `deploy` is the only app user, but don't add other
> users to it.

### 4.3 uv (as `deploy`, not root)

```bash
su - deploy
curl -LsSf https://astral.sh/uv/install.sh | sh
exit
```

uv installs into `/home/deploy/.local/bin/uv`. It downloads the Python version
pinned in `server/.python-version` (3.12) by itself, so you do **not** need to
install Python with apt.

**Check:**

```bash
su - deploy -c '~/.local/bin/uv --version && docker ps && git --version'
```

---

## 5. Get the code onto the VPS (one time)

### 5.1 Create the repo deploy key (key #3)

```bash
# as deploy
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N "" -C "vps-deploy-key"
cat ~/.ssh/github_deploy.pub
```

In GitHub, go to **repo → Settings → Deploy keys → Add deploy key**. Paste the
public key and leave **"Allow write access" unticked**. The VPS only needs to
read the code.

Tell SSH to use that key for GitHub:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github.com
  IdentityFile ~/.ssh/github_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
ssh -T git@github.com     # answer "yes"; expect "...successfully authenticated..."
```

### 5.2 Clone

```bash
# as root
mkdir -p /srv/error-solver && chown deploy:deploy /srv/error-solver

# as deploy
git clone --branch production git@github.com:rakibh3/ai-error-solver-backend.git /srv/error-solver
```

The API lives in `/srv/error-solver/server`. Every command from here on runs
from that directory unless stated otherwise.

### 5.3 Storage directories outside the repo

Uploaded submissions and cloned reference repos should **not** live inside the
git checkout. Keeping them out means a deploy can never touch user data.

```bash
# as root
mkdir -p /var/lib/error-solver/{reference_projects,submissions}
chown -R deploy:deploy /var/lib/error-solver
chmod 750 /var/lib/error-solver
```

---

## 6. Write the production `.env`

```bash
# as deploy
cd /srv/error-solver/server
cp .env.example .env
chmod 600 .env          # only deploy can read the secrets
nano .env
```

`.env` is gitignored and **never** leaves the server. CI does not need it.
Every variable is documented in [`ENV.md`](ENV.md). These are the values that
**must differ from development**:

```dotenv
# Generate: python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# The server refuses to start with the placeholder or anything under 32 bytes.
JWT_SECRET_KEY=<paste generated value>

POSTGRES_USER=error_solver
# Generate: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
POSTGRES_PASSWORD=<paste generated value>
POSTGRES_DB=error_solver
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

OPENROUTER_API_KEY=<real key>
VOYAGE_API_KEY=<real key>
OPENROUTER_SITE_URL=https://api.example.com

ANALYSIS_MODEL=google/gemini-2.5-flash
EMBEDDING_MODEL=voyage-code-3

# Public API: hide /docs, /redoc and the OpenAPI schema (they map the admin surface).
ENABLE_API_DOCS=false

# Absolute paths, outside the git checkout (§5.3).
REFERENCE_PROJECTS_DIR=/var/lib/error-solver/reference_projects
SUBMISSIONS_DIR=/var/lib/error-solver/submissions

# Who may set X-Forwarded-For. See the next section. NEVER "*".
FORWARDED_ALLOW_IPS=127.0.0.1

# Used once by the seed script (§8.3). Delete ADMIN_PASSWORD from this file afterwards.
ADMIN_EMAIL=you@example.com
ADMIN_PASSWORD=<long unique password, 12+ chars>
ADMIN_FULLNAME=Your Name
```

> **Changing `EMBEDDING_MODEL` later** invalidates every Qdrant collection, so
> every reference branch must be re-indexed. Pick the model before go-live.

### Where the client runs → `FORWARDED_ALLOW_IPS`

Rate limits for logged-out requests are keyed by client IP. The Next.js BFF
passes the browser's IP in `X-Forwarded-For`. uvicorn only believes that header
from the peers listed in `FORWARDED_ALLOW_IPS`. Pick the row that matches your
setup:

| Client (Next.js) runs… | Client's `BACKEND_URL` | Server's `FORWARDED_ALLOW_IPS` |
|---|---|---|
| **On this same VPS** (recommended) | `http://127.0.0.1:8000` (skips nginx) | `127.0.0.1` |
| On another server with a **fixed IP** | `https://api.example.com` | `127.0.0.1,<that server's IP>` |
| On serverless/Vercel (no fixed IP) | `https://api.example.com` | `127.0.0.1` and accept that anonymous per-IP limits see the platform's egress IP. Per-user and per-account login limits still work. |

Why this is safe: nginx **appends** the real peer IP to `X-Forwarded-For`.
uvicorn reads the list from the right and stops at the first address it does
not trust. Someone calling the API directly with a forged header therefore
still gets their real IP as their rate-limit key.

---

## 7. Start Postgres and Qdrant

```bash
# as deploy, in /srv/error-solver/server
docker compose up -d
docker compose ps        # both should show "healthy" after ~10 s
```

Both containers use `restart: unless-stopped`, so they come back after a reboot
on their own. Their data lives in the named volumes `pgdata` and
`qdrant_storage`, which survive `docker compose down` but **not**
`docker compose down -v`. Never run `down -v` in production.

> Optional hardening: Qdrant is only reachable on loopback, so auth is not
> required. For defence in depth, set `QDRANT_API_KEY` in `.env`, uncomment
> `QDRANT__SERVICE__API_KEY` in `docker-compose.yml`, and run
> `docker compose up -d` again.

---

## 8. Install dependencies, migrate, create the admin

### 8.1 Install

```bash
~/.local/bin/uv sync --frozen --no-dev
```

- `--frozen` installs exactly what `uv.lock` says and fails if the lock is out
  of date, so production can never quietly resolve different versions from CI.
- `--no-dev` skips pytest and httpx.

### 8.2 Migrate

```bash
~/.local/bin/uv run --no-sync alembic upgrade head
```

Alembic owns the schema. Never use `create_all` in production.

### 8.3 Create the first admin

```bash
~/.local/bin/uv run --no-sync python -m scripts.seed_admin
```

This is the **only** way an admin account comes into existence, because public
registration always creates a normal user. After it succeeds, remove
`ADMIN_PASSWORD` from `.env`. The API never reads it, and leaving it there only
adds exposure.

### 8.4 Smoke test by hand

```bash
~/.local/bin/uv run --no-sync uvicorn main:app --host 127.0.0.1 --port 8000
# in a second SSH session:
curl http://127.0.0.1:8000/        # {"message":"Server is running"}
```

Stop it with `Ctrl+C`. systemd takes over next.

---

## 9. Run the API as a systemd service

### 9.1 The unit file

```bash
# as root
cat > /etc/systemd/system/error-solver-api.service <<'EOF'
[Unit]
Description=Error Navigator API (FastAPI / uvicorn)
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/srv/error-solver/server
EnvironmentFile=/srv/error-solver/server/.env
Environment=PYTHONUNBUFFERED=1

# One worker on purpose; see §1. 127.0.0.1 only: nginx is the public face.
ExecStart=/srv/error-solver/server/.venv/bin/uvicorn main:app \
    --host 127.0.0.1 --port 8000 --workers 1 \
    --proxy-headers --forwarded-allow-ips ${FORWARDED_ALLOW_IPS} \
    --no-server-header

Restart=always
RestartSec=3
# Let in-flight requests (e.g. a 60 s analysis) finish on restart.
TimeoutStopSec=90

# Hardening: the app can only write to its storage dirs and /tmp.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
# read-only, not "true": the venv's Python lives in ~deploy/.local/share/uv.
ProtectHome=read-only
ReadWritePaths=/var/lib/error-solver
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
EOF
```

`EnvironmentFile` loads `.env` into the process environment. This matters
because uvicorn reads `FORWARDED_ALLOW_IPS` **before** the app's `load_dotenv()`
runs.

### 9.2 Start it

```bash
systemctl daemon-reload
systemctl enable --now error-solver-api
systemctl status error-solver-api          # "active (running)"
curl http://127.0.0.1:8000/                # {"message":"Server is running"}
journalctl -u error-solver-api -n 50       # recent logs
```

### 9.3 Let `deploy` restart only this service

The CI deploy logs in as `deploy` and needs to restart the API. Grant exactly
that and nothing more:

```bash
# as root
cat > /etc/sudoers.d/error-solver-deploy <<'EOF'
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart error-solver-api
EOF
chmod 440 /etc/sudoers.d/error-solver-deploy
visudo -cf /etc/sudoers.d/error-solver-deploy     # must print "parsed OK"
```

**Check (as deploy):** `sudo systemctl restart error-solver-api` works without
a password prompt, and `sudo ls /root` is refused.

---

## 10. Put nginx in front

```bash
# as root
cat > /etc/nginx/sites-available/error-solver-api <<'EOF'
upstream error_solver_api {
    server 127.0.0.1:8000;
    keepalive 16;
}

server {
    listen 80;
    listen [::]:80;
    server_name api.example.com;

    server_tokens off;

    # MAX_UPLOAD_MB is 25; allow a little multipart overhead. Bigger bodies are
    # rejected here with 413 before they ever reach Python.
    client_max_body_size 26m;

    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "no-referrer" always;

    location / {
        proxy_pass http://error_solver_api;
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        # Appends the real peer IP; see "Where the client runs" in §6.
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Analysis can take up to ANALYSIS_TIMEOUT_SECONDS (60) plus retrieval.
        proxy_connect_timeout 10s;
        proxy_send_timeout    120s;
        proxy_read_timeout    120s;
    }
}
EOF

ln -s /etc/nginx/sites-available/error-solver-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx          # always run nginx -t before reload
```

If you raise `MAX_UPLOAD_MB` in `.env`, raise `client_max_body_size` here too.
Otherwise nginx returns 413 first. If you raise `ANALYSIS_TIMEOUT_SECONDS`,
raise `proxy_read_timeout` too, or nginx returns 504.

---

## 11. Point the domain and turn on HTTPS

### 11.1 DNS

At your DNS provider, create an **A record**: `api` → `203.0.113.10`. Add an
**AAAA** record too if the VPS has IPv6. Wait until it resolves:

```bash
# on your laptop
dig +short api.example.com      # must print 203.0.113.10
```

### 11.2 Certificate

```bash
# as root
certbot --nginx -d api.example.com --redirect -m you@example.com --agree-tos --no-eff-email
```

certbot gets a Let's Encrypt certificate, adds the `listen 443 ssl` block to
your nginx file, and makes port 80 redirect to HTTPS. It also installs a timer
that renews the certificate automatically.

**Check:**

```bash
curl -I http://api.example.com/        # 301 → https
curl https://api.example.com/          # {"message":"Server is running"}
certbot renew --dry-run                # renewal works
```

Optional, once HTTPS works: add HSTS inside the `listen 443` server block
certbot created, then `nginx -t && systemctl reload nginx`:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

**Manual deployment is now complete.** The rest of this guide automates future
updates.

---

## 12. The deploy script

CI deploys by SSH-ing in and running one script that lives in the repo. Create
`server/scripts/deploy.sh`:

```bash
#!/usr/bin/env bash
# Deploy a specific commit of the API on this VPS.
#
#   scripts/deploy.sh <commit-sha>
#
# Called by .github/workflows/server-ci-cd.yml over SSH. Safe to run by hand.
# Rolls the code back automatically if the new version fails its health check.
# It does NOT roll back database migrations; keep migrations backward-compatible.
set -euo pipefail

REPO_DIR=/srv/error-solver
APP_DIR="$REPO_DIR/server"
SERVICE=error-solver-api
HEALTH_URL=http://127.0.0.1:8000/
UV="$HOME/.local/bin/uv"

log() { printf '\n==> %s\n' "$*"; }

healthy() {
    for _ in $(seq 1 30); do
        curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1 && return 0
        sleep 1
    done
    return 1
}

install_and_restart() {
    cd "$APP_DIR"
    "$UV" sync --frozen --no-dev
    sudo systemctl restart "$SERVICE"
}

# Everything runs inside main(), which is called on the last line. This makes
# bash read the whole file before executing it. Without that, `git reset` below
# would rewrite this script while bash is still reading it.
main() {
    local target="${1:?usage: deploy.sh <commit-sha>}"
    cd "$REPO_DIR"

    local previous
    previous="$(git rev-parse HEAD)"

    log "Fetching $target"
    git fetch --prune origin production
    git cat-file -e "${target}^{commit}"       # fail fast on an unknown sha
    git reset --hard "$target"

    log "Installing dependencies"
    cd "$APP_DIR"
    "$UV" sync --frozen --no-dev

    log "Ensuring Postgres and Qdrant are up"
    docker compose up -d --wait

    log "Running migrations"
    "$UV" run --no-sync alembic upgrade head

    log "Restarting $SERVICE"
    sudo systemctl restart "$SERVICE"

    if healthy; then
        echo "$previous" > "$REPO_DIR/.previous_deploy"
        log "Deployed $(git -C "$REPO_DIR" rev-parse --short HEAD)"
        return 0
    fi

    log "Health check FAILED. Recent logs:"
    journalctl -u "$SERVICE" -n 60 --no-pager || true

    log "Rolling code back to $previous"
    git -C "$REPO_DIR" reset --hard "$previous"
    install_and_restart
    healthy && log "Rollback healthy" || log "Rollback ALSO unhealthy: investigate now"
    return 1
}

main "$@"
```

Make it executable and commit it:

```bash
# on your laptop, in the repo
chmod +x server/scripts/deploy.sh
git add server/scripts/deploy.sh
git commit -m "chore(deploy): add VPS deploy script"
```

**Why deploy an exact SHA instead of "latest"?** The pipeline tests one commit.
Passing that commit's SHA guarantees the VPS runs exactly what was tested, even
if someone pushes again while the pipeline is running.

---

## 13. The CI/CD pipeline (GitHub Actions)

### 13.1 Create the CI SSH key (key #2)

On **your laptop** (not the VPS):

```bash
ssh-keygen -t ed25519 -f ./ci_deploy_key -N "" -C "github-actions-deploy"
```

Put the **public** half on the VPS:

```bash
ssh deploy@203.0.113.10 "cat >> ~/.ssh/authorized_keys" < ./ci_deploy_key.pub
```

Capture the VPS host key so CI can verify it's talking to *your* server:

```bash
ssh-keyscan -t ed25519 203.0.113.10 > ./known_hosts_entry
```

### 13.2 Add GitHub secrets and variables

In GitHub, go to **repo → Settings → Environments → New environment**, name it
**`production`**, and add these to it:

| Kind | Name | Value |
|---|---|---|
| Secret | `SSH_PRIVATE_KEY` | full contents of `./ci_deploy_key`, including the `BEGIN`/`END` lines |
| Secret | `SSH_KNOWN_HOSTS` | contents of `./known_hosts_entry` |
| Secret | `SSH_HOST` | `203.0.113.10` |
| Secret | `SSH_USER` | `deploy` |
| Variable | `API_URL` | `https://api.example.com` |

Then **delete the key files from your laptop**:
`rm ci_deploy_key ci_deploy_key.pub known_hosts_entry`.

Optional: in the same environment, add yourself under **Required reviewers**.
Each deploy then waits for your click, which gives you a manual gate.

Also, under **Settings → Branches**, add a branch protection rule for
`production`: require pull requests and require the `test` and `migrations`
checks to pass before merging.

### 13.3 The workflow file

Create `.github/workflows/server-ci-cd.yml` at the **repository root** (not
inside `server/`). GitHub only reads workflows from the root.

```yaml
name: Server CI/CD

on:
  push:
    branches: [production]
    paths:
      - "server/**"
      - ".github/workflows/server-ci-cd.yml"
  pull_request:
    branches: [production]
    paths:
      - "server/**"
      - ".github/workflows/server-ci-cd.yml"
  workflow_dispatch: {}          # "Run workflow" button for manual redeploys

# Never run two deploys at once; queue them instead of cancelling mid-deploy.
concurrency:
  group: server-${{ github.ref }}
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  test:
    name: test
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: server
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U test -d test"
          --health-interval 5s --health-timeout 3s --health-retries 10
    env:
      # Real Postgres: SQLite misses enum, JSONB and server_default bugs.
      TEST_DATABASE_URL: postgresql://test:test@localhost:5432/test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: server/uv.lock
      - run: uv sync --frozen
      - run: uv run pytest -q

  migrations:
    name: migrations
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: server
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: ci
          POSTGRES_PASSWORD: ci
          POSTGRES_DB: ci
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U ci -d ci"
          --health-interval 5s --health-timeout 3s --health-retries 10
    env:
      POSTGRES_USER: ci
      POSTGRES_PASSWORD: ci
      POSTGRES_DB: ci
      POSTGRES_HOST: localhost
      # config.py refuses to import without a 32+ byte key; this one is CI-only.
      JWT_SECRET_KEY: ci-only-secret-key-not-used-anywhere-else-000
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: server/uv.lock
      - run: uv sync --frozen --no-dev
      # Proves the migration chain applies to an empty database, exactly as prod runs it.
      - run: uv run --no-sync alembic upgrade head
      # Fails if a model changed without a migration.
      - run: uv run --no-sync alembic check

  deploy:
    name: deploy
    needs: [test, migrations]
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/production'
    runs-on: ubuntu-24.04
    environment:
      name: production
      url: ${{ vars.API_URL }}
    steps:
      - name: Configure SSH
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
          SSH_KNOWN_HOSTS: ${{ secrets.SSH_KNOWN_HOSTS }}
        run: |
          install -m 700 -d ~/.ssh
          printf '%s\n' "$SSH_PRIVATE_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          printf '%s\n' "$SSH_KNOWN_HOSTS" > ~/.ssh/known_hosts

      - name: Deploy ${{ github.sha }}
        env:
          SSH_HOST: ${{ secrets.SSH_HOST }}
          SSH_USER: ${{ secrets.SSH_USER }}
        run: |
          ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=yes \
            "$SSH_USER@$SSH_HOST" \
            "bash /srv/error-solver/server/scripts/deploy.sh '${GITHUB_SHA}'"

      - name: Public smoke test
        env:
          API_URL: ${{ vars.API_URL }}
        run: |
          for i in $(seq 1 10); do
            curl -fsS --max-time 5 "$API_URL/" && exit 0
            sleep 3
          done
          echo "Smoke test failed: $API_URL/ is not answering" >&2
          exit 1
```

What each job protects you from:

| Job | Runs on | Catches |
|---|---|---|
| `test` | every PR and push | broken code, broken auth rules, Postgres-only schema bugs |
| `migrations` | every PR and push | a migration that doesn't apply, or a model change with no migration |
| `deploy` | push to `production` only, after both pass | nothing: it ships. The deploy script's health check and the smoke test catch a bad start. |

Secrets are passed through `env:` and never pasted inline into `run:` lines.
That is GitHub's recommended pattern, because inline `${{ }}` expressions in
shell commands are an injection risk.

> **Note on `alembic check`.** If the first run fails there, your models and
> migrations have already drifted. Generate the missing migration with
> `uv run alembic revision --autogenerate -m "..."`, review it, and commit it.
> Don't delete the check.

---

## 14. Your first automatic deploy

1. Commit `server/scripts/deploy.sh` and `.github/workflows/server-ci-cd.yml`,
   and push the branch.
2. Open a PR into `production`. You should see **test** and **migrations** run
   and go green, and **deploy** should *not* run on a PR.
3. Merge. On the push to `production`, all three jobs run. Watch the
   **Actions** tab. The deploy job's log shows each `==>` step from the script.
4. Verify:
   ```bash
   curl https://api.example.com/                                 # 200
   ssh deploy@203.0.113.10 'git -C /srv/error-solver log -1 --oneline'   # the merged commit
   ```

To redeploy without a code change (for example after editing `.env`), use
**Actions → Server CI/CD → Run workflow** on `production`. If you only changed
`.env`, `sudo systemctl restart error-solver-api` on the VPS is enough.

---

## 15. Day-to-day operations

| Task | Command (on the VPS as `deploy`, in `/srv/error-solver/server`) |
|---|---|
| Live API logs | `journalctl -u error-solver-api -f` |
| API status | `systemctl status error-solver-api` |
| Restart API | `sudo systemctl restart error-solver-api` |
| DB / Qdrant status | `docker compose ps` |
| DB / Qdrant logs | `docker compose logs -f --tail=100 postgres` (or `qdrant`) |
| Postgres shell | `docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"` (after `set -a; . ./.env; set +a`) |
| nginx logs | `sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log` |
| Disk usage | `df -h; du -sh /var/lib/error-solver/*; docker system df` |
| Change a setting | edit `.env`, then `sudo systemctl restart error-solver-api` |
| Upgrade Postgres/Qdrant image | bump the tag in `docker-compose.yml` via a PR. Deploy runs `docker compose up -d`. **Back up first** (§17). Major Postgres versions need a dump/restore. |

Keep an eye on disk usage. Submissions (up to `USER_STORAGE_QUOTA_MB` per user),
reference clones, and Qdrant collections all grow over time.

Set up a free external uptime monitor (UptimeRobot, Better Stack, and so on)
on `https://api.example.com/` so you hear about an outage before your users do.

---

## 16. Rollback

**Automatic.** If the new version fails its health check, `deploy.sh` already
put the previous code back.

**Manual, bad code that passed its health check.** The preferred way is to
revert on GitHub, which leaves an audit trail and redeploys through the
pipeline:

```bash
# on your laptop
git revert <bad-sha> && git push origin production
```

**Emergency, straight on the VPS.** This skips CI:

```bash
ssh deploy@203.0.113.10
bash /srv/error-solver/server/scripts/deploy.sh "$(cat /srv/error-solver/.previous_deploy)"
```

**Database migrations are not rolled back automatically.** Code rolls back
cleanly only if the schema change was **additive**. For example, add a column
as nullable, ship code that uses it, and drop old columns in a *later* release.
If a destructive migration must be undone, restore from backup (§17) or run
`uv run alembic downgrade -1` deliberately, knowing what it drops.

---

## 17. Backups

What holds state, and what losing it costs:

| Data | Where | If lost |
|---|---|---|
| Postgres (users, submissions metadata, analyses) | Docker volume `pgdata` | **Unrecoverable.** Back this up. |
| Uploaded submissions | `/var/lib/error-solver/submissions` | Users must re-upload |
| Reference clones | `/var/lib/error-solver/reference_projects` | Re-cloned by re-indexing |
| Qdrant vectors | Docker volume `qdrant_storage` | Rebuilt by re-indexing each branch from the admin API (costs Voyage credits) |
| `.env` | `/srv/error-solver/server/.env` | Keep a copy in a password manager |

Nightly Postgres dump, keeping 14 days:

```bash
# as root
mkdir -p /var/backups/error-solver && chown deploy:deploy /var/backups/error-solver

cat > /etc/cron.d/error-solver-backup <<'EOF'
# m h dom mon dow user command
15 3 * * * deploy cd /srv/error-solver/server && set -a && . ./.env && set +a && docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > /var/backups/error-solver/db-$(date +\%F).dump && find /var/backups/error-solver -name 'db-*.dump' -mtime +14 -delete
EOF
```

A backup that only lives on the same VPS is **not** a backup. Copy
`/var/backups/error-solver` off the machine (provider snapshots, `rclone` to
object storage, and so on).

**Test the restore once**, before you need it:

```bash
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < /var/backups/error-solver/db-YYYY-MM-DD.dump
```

---

## 18. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Service won't start; log says `JWT_SECRET_KEY must be a random secret…` | Placeholder or short key in `.env` | Generate a real one (§6), then restart |
| Log says `QDRANT_API_KEY is required when Qdrant is not on localhost` | `QDRANT_HOST`/`QDRANT_URL` points off-host | Keep `localhost` for the compose container, or supply https + key |
| `502 Bad Gateway` from nginx | uvicorn not running or not on 127.0.0.1:8000 | `systemctl status error-solver-api`, `journalctl -u error-solver-api -n 100` |
| `504 Gateway Timeout` on `/analyze` | Model slower than `proxy_read_timeout` | Raise `proxy_read_timeout` (and check `ANALYSIS_TIMEOUT_SECONDS`) |
| `413 Request Entity Too Large` from nginx | Upload > `client_max_body_size` | Keep it just above `MAX_UPLOAD_MB` |
| Everyone hits the rate limit together | `FORWARDED_ALLOW_IPS` wrong, so all traffic keys on one IP | See [Where the client runs](#where-the-client-runs--forwarded_allow_ips) |
| Rate limits seem N× too loose | More than one worker | `--workers 1` (§1) |
| Admin ingest fails with a git error | `git` missing, or repo host not in `REPO_ALLOWED_HOSTS` | `apt install git`, or add the host |
| Writing to submissions fails with `Read-only file system` | Storage path not in `ReadWritePaths` | Use the `/var/lib/error-solver/...` paths from §6, or add the path to the unit file |
| CI: `Permission denied (publickey)` | Wrong key in `SSH_PRIVATE_KEY`, or public half missing from `authorized_keys` | Recheck §13.1; the secret must include the `BEGIN`/`END` lines |
| CI: `Host key verification failed` | `SSH_KNOWN_HOSTS` empty or VPS rebuilt | Re-run `ssh-keyscan` and update the secret |
| CI: `sudo: a password is required` | sudoers rule missing or path differs | Check `which systemctl` is `/usr/bin/systemctl`; redo §9.3 |
| CI: `uv: command not found` over SSH | Non-interactive shells skip `~/.bashrc` | The script uses `$HOME/.local/bin/uv` explicitly. Don't change that to `uv`. |
| `uv sync --frozen` fails in deploy | `uv.lock` out of date with `pyproject.toml` | Run `uv lock` locally, commit the lock |
| CI `alembic check` fails | Model changed without a migration | `uv run alembic revision --autogenerate -m "..."`, review, commit |
| Certificate expired | Renewal timer broken, or port 80 blocked | `certbot renew --dry-run`; keep `ufw allow 80/tcp` |

---

## 19. Go-live checklist

**Server**
- [ ] Root login and password SSH disabled; `ufw` allows only 22/80/443
- [ ] Unattended security upgrades on
- [ ] Postgres and Qdrant ports bound to `127.0.0.1` only (`ss -tlnp | grep -E '5432|6333'`)

**App config**
- [ ] `JWT_SECRET_KEY` and `POSTGRES_PASSWORD` freshly generated, not reused from dev
- [ ] `ENABLE_API_DOCS=false`
- [ ] `FORWARDED_ALLOW_IPS` matches where the client runs, and is **not** `*`
- [ ] Storage dirs point to `/var/lib/error-solver/...`
- [ ] `ADMIN_PASSWORD` removed from `.env` after seeding; `.env` is `chmod 600`
- [ ] uvicorn runs with `--workers 1`

**Web**
- [ ] `https://api.example.com/` returns 200; `http://` redirects to https
- [ ] `https://api.example.com/docs` returns **404**
- [ ] `certbot renew --dry-run` succeeds

**Pipeline**
- [ ] PRs run `test` + `migrations` but not `deploy`
- [ ] Merge to `production` deploys and the smoke test passes
- [ ] Branch protection requires the checks; CI key files deleted from your laptop

**Operations**
- [ ] Nightly DB dump runs, is copied off the VPS, and a restore has been tested
- [ ] External uptime monitor on `https://api.example.com/`
