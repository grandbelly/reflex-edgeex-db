# KSys Docker / Deployment Infrastructure Audit

- **Date**: 2026-05-21
- **Auditor**: bkit-infra-architect
- **Scope**: Dockerfile inventory, compose orchestration, multi-RPI rollout readiness, version control posture, TimescaleDB/pg_cron risks
- **Working dir**: `C:\Users\Ipeop\SynologyDrive_강민구대표\SynologyDrive\00_ServerPC\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo\`
- **Goal in scope**: deploy to N additional RPI5 (ARM64) units within ~1 month

---

## 1. Dockerfile Inventory + Analysis

### 1.1 Inventory

| Path | Purpose | Base image | Stages | Pinned? | Runs as root? | Healthcheck | Size estimate |
|------|---------|------------|--------|---------|---------------|-------------|---------------|
| `Dockerfile` | Reflex web app (frontend+backend) | `python:3.11-slim` | single | partial (tag only) | yes (no USER) | none | ~1.8–2.2 GB (Node18+npm+reflex build) |
| `Dockerfile.scheduler` | Forecasting scheduler | `python:3.11-slim` | single | partial | yes | none | ~1.2–1.6 GB (ML stack: statsforecast, xgboost, prophet) |
| `Dockerfile.pipeline` (untracked) | CSV → TimescaleDB ETL one-shot | `python:3.12-slim` | single | partial | yes | none | ~150 MB |
| `Dockerfile.data-injector` | Virtual data generator loop | `python:3.13-slim` | single | partial | yes | none | ~150 MB |
| `20251030-rpi-pgcron/Dockerfile.rpi-pgcron` | TimescaleDB17 + pg_cron (Alpine) | `timescale/timescaledb:latest-pg17` | single | **NO** (`latest`) | yes (postgres user via base) | yes | ~350–450 MB |
| `schedulers/Dockerfile` | Duplicate of `Dockerfile.scheduler` minus env vars | `python:3.11-slim` | single | partial | yes | none | identical to scheduler |

### 1.2 Findings

| # | Issue | Severity | File / Evidence | Recommendation |
|---|-------|----------|-----------------|----------------|
| D-01 | `Dockerfile.rpi-pgcron` uses `timescale/timescaledb:latest-pg17` — `latest` floating tag. New RPI built next month may pull a different upstream image than the RPI built today. Reproducibility is broken. | CRITICAL | `20251030-rpi-pgcron/Dockerfile.rpi-pgcron:6` | Pin to digest, e.g. `timescale/timescaledb:2.21.3-pg17` or `@sha256:...`. Re-pin after each verified RPI deploy. |
| D-02 | No `.dockerignore` at repo root. Every `docker build` ships `.web/` (node_modules), `agentic-runs/`, `backup/` (389 MB dump), `reports/`, `.claude/worktrees/`, `*.dump`. Massive context tarball → slow builds and bloated images if copied. | HIGH | `.dockerignore` absent; `Dockerfile:27` does `COPY . .` | Add `.dockerignore` mirroring `.gitignore` PLUS `.web/`, `.states/`, `backup/`, `reports/`, `agentic-runs/`, `.claude/`, `*.dump`, `*.csv`, `__pycache__/`. |
| D-03 | `Dockerfile` (web) and `Dockerfile.scheduler` both run as root. No `USER appuser` line. ML scheduler with pickle.loads from disk widens attack surface. | HIGH | `Dockerfile` (no USER); `Dockerfile.scheduler` (no USER) | Add `RUN useradd -m -u 1000 app && chown -R app /app` and `USER app` before CMD. |
| D-04 | No multi-stage builds. Web image keeps `build-essential`, `git`, `npm cache`, full pip cache layer in the final image. Compounding D-02. On RPI (16 GB SD/SSD) this matters. HANDOFF backlog also lists "Docker image 4.49 GB 경량화". | HIGH | `Dockerfile:11-24` | Adopt multi-stage: stage 1 builds `.web/` with Node, stage 2 is `python:3.11-slim` + only runtime deps + built `.web/`. Estimated 50–60 % size cut. |
| D-05 | Web `Dockerfile` runs `reflex init --loglevel debug \|\| true` at build time. The `\|\| true` silences any failure — a broken init ships unnoticed. | MED | `Dockerfile:30` | Either fix the underlying init issue and remove `\|\| true`, or move init to an entrypoint script that fails fast on first start. |
| D-06 | Three Python base versions span the four app images: 3.11 (web, scheduler), 3.12 (pipeline), 3.13 (data-injector). No reason for divergence — drift hazard. | MED | `Dockerfile`, `Dockerfile.scheduler`, `Dockerfile.pipeline`, `Dockerfile.data-injector` | Standardise on `python:3.11-slim-bookworm@sha256:...` across all four. |
| D-07 | Duplicate Dockerfile: `schedulers/Dockerfile` is essentially `Dockerfile.scheduler` minus the timeout/pool env vars from the H5/H7 fix. Risk: someone builds from the stale one. | MED | `schedulers/Dockerfile` vs `Dockerfile.scheduler` | Delete `schedulers/Dockerfile` (no compose references it). Add `# DO NOT USE` if deletion blocked. |
| D-08 | No image has an in-container `HEALTHCHECK` except the DB. Compose-level healthchecks also missing for app/scheduler (see §2). | MED | `Dockerfile`, `Dockerfile.scheduler` | Add `HEALTHCHECK CMD curl -fsS http://localhost:13001/ping \|\| exit 1` to web image; PID-based check for scheduler. |
| D-09 | No `--platform=linux/arm64` declared. Dockerfiles silently build for the host arch. On Windows x86_64 dev, you build x86_64 images that won't run on RPI without rebuild. No `docker buildx` workflow. | HIGH | `Dockerfile*` (no `--platform`) | Adopt `docker buildx build --platform linux/arm64,linux/amd64` so the same Dockerfile produces both arches; push to registry (see §3). |
| D-10 | `Dockerfile.rpi-pgcron` symlinks `/usr/lib/postgresql17/pg_cron.so` blindly. Alpine recently flipped default to PG18; the dev workaround in `docker-compose.dev.yml` drops `pg_cron` from `shared_preload_libraries` to sidestep ABI mismatch. RPI prod uses the same image but keeps pg_cron on — fragile. | HIGH | `20251030-rpi-pgcron/Dockerfile.rpi-pgcron:14`, `HANDOFF.md:71-75` | Pin Alpine version (`FROM timescale/timescaledb:2.21.3-pg17-oss` or similar). Detect pkglibdir with `pg_config --pkglibdir`. Verify pg_cron loads on a clean build before next RPI ship. |

---

## 2. Compose Orchestration

### 2.1 Three compose files, three naming conventions

| File | Container prefix | Network | Volume strategy | Notes |
|------|------------------|---------|-----------------|-------|
| `docker-compose.yml` (RPI prod) | `rpi-finished-*`, `cloudflared-tunnel` | `ksys-network` (external) | bind mounts for `./ksys_app`, named volume `pgai_data` | Cloudflare token **in plaintext**, line 130 |
| `docker-compose.local.yml` (local validation) | `ksys-local-*` | `dev_network` (alias of `reflex-rpi-local-deployment-poongdo_default`, external) | bind mounts everywhere — reuses `ksys-dev-db` from dev compose | Has `init: true` and `stop_grace_period` (best practice — only file that does) |
| `docker-compose.dev.yml` (DB only) | `ksys-dev-db` | implicit default | named volume `ksys_dev_pgdata`, read-only mounts for backup/migrations | Overrides CMD to drop pg_cron (workaround for ABI mismatch) |
| `20251030-rpi-pgcron/docker-compose.rpi-pgcron.yml` (legacy RPI DB only) | `pgai-db` | `ksys-network` (external) | named volume `pgai_data` | Yet another naming scheme |

### 2.2 Findings

| # | Issue | Severity | File / Evidence | Recommendation |
|---|-------|----------|-----------------|----------------|
| C-01 | **Cloudflare Tunnel token committed in plaintext.** Anyone with repo read access can hijack the tunnel. | CRITICAL | `docker-compose.yml:130` | Rotate the token NOW via Cloudflare Zero Trust dashboard. Move to `.env` (gitignored) and reference as `${CLOUDFLARE_TUNNEL_TOKEN}`. Consider AWS/HCP Vault when fleet grows. |
| C-02 | DB password `postgres:postgres` hardcoded in 6+ places across all three compose files. Identical on every RPI. | CRITICAL | `docker-compose.yml:9-10,40,41,78,79,114`, `docker-compose.local.yml:24-25,83-84`, `docker-compose.dev.yml:27-28` | Externalise to `.env` per RPI: `POSTGRES_PASSWORD=...`, `TS_DSN=...`. Generate per-RPI password at provisioning time. |
| C-03 | Healthcheck coverage gap: only the DB has a healthcheck. `rpi-finished-reflex-app`, `rpi-finished-forecast-scheduler`, `rpi-finished-data-injector`, `timeseries-pipeline` all lack one — `depends_on` cannot gate on their readiness. | HIGH | `docker-compose.yml:31-124` | Add HTTP healthcheck to reflex-app (`curl /ping`), liveness file or stdin probe for scheduler/injector. |
| C-04 | Production compose lacks `init: true` and `stop_grace_period`. Local compose has them because of the zombie socket incident ([[feedback_no_host_reflex_zombie]]). Same risk applies on RPI under power loss. | HIGH | `docker-compose.yml` (no `init`/`stop_grace_period`); `docker-compose.local.yml:44-45` | Copy the `init: true` + `stop_grace_period: 30s` pattern from local compose into prod compose. |
| C-05 | No memory/CPU limits anywhere. RPI5 has 8 GB shared. The scheduler holds statsforecast + XGBoost + Prophet in memory — one OOM kills the DB too. | HIGH | all compose files (no `deploy.resources` / `mem_limit`) | Set `deploy.resources.limits.memory` per service (DB 3G, reflex-app 1.5G, scheduler 2G, injector/pipeline 256M). Validate against `free -m` on RPI. |
| C-06 | Bind mount of source code (`./ksys_app:/app/ksys_app`) in **production** compose. Means RPI is doing live code reload from filesystem; image content is overridden. Intentional for hot-patch but unsafe for "ship to many RPIs" — code drift between RPIs becomes invisible. | HIGH | `docker-compose.yml:47-48,82-83` | For prod, `COPY` code in image and drop the bind mount. Keep bind mount only in local/dev compose. |
| C-07 | Network `ksys-network` is `external: true` but no script creates it on a fresh RPI. First `docker compose up` on a clean RPI errors out. | MED | `docker-compose.yml:138-139`, `20251030-rpi-pgcron/docker-compose.rpi-pgcron.yml:31-32` | Either set `external: false` (let compose create), or add a `bootstrap.sh` that runs `docker network create ksys-network` before compose up. |
| C-08 | `docker-compose.local.yml` aliases `dev_network` to literal name `reflex-rpi-local-deployment-poongdo_default`. If anyone renames the project directory, dev breaks silently. | MED | `docker-compose.local.yml:112-116` | Use `name: ksys-dev-default` (stable, independent of cwd), or define the network in both compose files identically. |
| C-09 | Three different container names for the DB across environments (`rpi-finished-pgai-db`, `ksys-dev-db`, `pgai-db`) → in-app DSNs differ per env. Source of past bugs. | MED | docker-compose.{yml, local.yml, dev.yml} | Standardise on hostname `db` (compose service name) inside the network; the app reads `TS_DSN` from env. Container names can stay different for shell ergonomics. |
| C-10 | `depends_on: condition: service_healthy` is used correctly — but only because DB has the only healthcheck. Once C-03 is fixed, add `condition: service_started` or `service_healthy` everywhere. | LOW | OK as-is | Roll up under C-03. |
| C-11 | `restart: unless-stopped` everywhere is fine, but no `restart: on-failure:5` for one-shot pipeline. `timeseries-pipeline` is a one-shot ETL — `unless-stopped` will respawn forever after it finishes. | LOW | `docker-compose.yml:124`, `docker-compose.local.yml:109` | Change pipeline to `restart: "no"` or `on-failure`. |

---

## 3. Multi-RPI Rollout Readiness

### 3.1 Automation inventory

| Asset | Exists? | What it does |
|-------|---------|--------------|
| `scripts/deploy_local.bat` | yes | Spins up local dev DB + builds local compose. Windows-only. Not for RPI. |
| `scripts/deploy_gcp.sh` | yes | **Empty stub** — single comment "removed per user requirement". |
| `ansible/`, `cloud-init/`, `terraform/` | NO | Nothing. |
| Per-RPI bootstrap script | NO | No `provision_rpi.sh`, no Ansible playbook. |
| DB restore script | NO | Procedure is documented in `20251030-rpi-pgcron/RPI_PGCRON_DEPLOYMENT.md` but not codified. |
| Per-RPI config layer | NO | No `.env.example`, no `config/{rpi-id}/`. Everything is hardcoded in compose. |
| Image registry | NO | Every RPI does `docker build` locally. No GHCR/ECR/Harbor. |
| CI pipeline | NO | No `.github/workflows/`. |

### 3.2 Findings

| # | Issue | Severity | Evidence | Recommendation |
|---|-------|----------|----------|----------------|
| R-01 | **No automation for bringing up a new RPI.** Procedure is tribal knowledge ("ssh in, git pull, docker compose build, restore dump"). 1-month / N-unit goal is unrealistic without scripting. | CRITICAL | `scripts/deploy_gcp.sh:1` is a removed stub | Write `scripts/bootstrap_rpi.sh` that: (a) installs docker, (b) clones repo, (c) creates `ksys-network`, (d) generates per-RPI `.env`, (e) restores DB from a known dump, (f) starts compose, (g) verifies HTTP 200 on :14000. |
| R-02 | Per-RPI config (sensor IDs, location label, hostname for Cloudflare, optional unit-specific tags) is not externalised. To deploy a second RPI you'd be editing compose YAML on each one. | CRITICAL | `docker-compose.yml` hardcodes `TS_DSN`, `APP_ENV`, `ENABLE_AI_FEATURES`. No `RPI_SITE_NAME`/`RPI_UNIT_ID` env. | Add `.env.example` listing every per-RPI variable. Add `env_file: .env` to each service. Document required keys in `README.md`. |
| R-03 | DB restore is a multi-step manual incantation (HANDOFF.md round 2 §3 documents the TimescaleDB-specific `pre_restore`/`post_restore` dance). Not scripted → easy to skip on RPI #4. | HIGH | `HANDOFF.md:77-90` | `scripts/restore_db.sh <dump_path>` that does CREATE DATABASE template0 → CREATE EXTENSION timescaledb VERSION '2.21.3' → `pre_restore` → single-thread `pg_restore` → `post_restore`. |
| R-04 | Images built per-RPI. Each RPI re-installs every pip + npm dep — slow, network-dependent, and bit-different per build. ML stack alone is ~800 MB pip download. | HIGH | No `image:` key (only `build:`) in any compose service | Push pre-built ARM64 images to GHCR (free for public repos / cheap for private). RPI just does `docker compose pull && up -d`. Build step becomes CI's job. |
| R-05 | Backups (`backup/*.dump`) are in repo path but `.gitignore`d. There's no documented "golden seed dump" location for new RPIs. Where does RPI #5 get its initial DB from? | HIGH | `.gitignore:27-28` | Decide policy: (a) seed each RPI from RPI #1's nightly dump (use S3/B2/Synology), (b) seed empty + replay from sensors. Document in `docs/rpi-provisioning.md`. |
| R-06 | No version-pinning of the `reflex-rpi-local-deployment-poongdo` repo itself — every RPI tracks `master`. A bad commit propagates fleet-wide. | MED | git config shows no per-RPI tag | Tag releases (`v1.0.0-rpi`); each RPI checks out a tag, not `master`. Promote via PR review. |
| R-07 | No fleet monitoring. With N RPIs you need to know which is unhealthy. Reflex `/ping` works for one, not for ten. | MED | nothing in compose for metrics export | Consider Uptime Kuma or a single Prometheus + node_exporter + cAdvisor on each RPI scraped by a central host. Out of scope for v1 but mention in plan. |

---

## 4. Version Control Posture

| # | Issue | Severity | Evidence | Recommendation |
|---|-------|----------|----------|----------------|
| G-01 | **Audit prompt says "no GitHub" but `.git/config` shows `origin = https://github.com/grandbelly/reflex-ksys-db.git`.** This is the DB-deployment repo, NOT the app code repo. So the *application* (ksys_app/, Dockerfile, compose files for prod) is in fact pushed to the DB repo — semantic mismatch. Verify with `git log origin/master..HEAD`. | HIGH | `.git/config:8-9`; HANDOFF.md round 2 §file table also lists `grandbelly/reflex-ksys-db` | Clarify: is `reflex-ksys-db` now the canonical repo for both? If yes, rename the repo to reflect scope. If no, split: app code in `reflex-ksys-app`, DB stuff in `reflex-ksys-db`. |
| G-02 | Single-machine git, no CI, no PR review enforced. If this Windows machine dies, recovery = whatever was last pushed. Push cadence unknown — `git status` shows uncommitted changes to `docker-compose.local.yml`, `docker-compose.yml`, plus several `.bak` / `_backup_` files at HEAD. | HIGH | Initial git status in conversation context | Immediately commit + push current `refactor/rpi-baseline-sync`. Confirm `origin/master` mirrors local. Set up branch protection on `master` (no direct push). |
| G-03 | `.gitignore` is okay but missing: `.env`, `*.dump.gz`, `.bkit/`, build artefacts `node_modules/` (covered via `.web/` only), `*.pyc` (covered), `*_backup_*.py` (visible in git status as untracked but should stay so until decided). | MED | `.gitignore:1-58` | Add explicit `.env`, `.env.*`, `!.env.example`, `dist/`, `*.dump.gz`. |
| G-04 | No CI. No automated tests on push. ML scheduler regressions ship invisibly. | MED | no `.github/workflows/` | Minimal CI: lint (`ruff check`), test (`pytest -q`), `docker buildx build --platform linux/arm64 --check` on PR. GitHub Actions free tier covers it. |
| G-05 | Cloudflare token, DB password, future API keys → no secret management plan. With multi-RPI, secrets sprawl is inevitable. | MED | C-01, C-02 | For now: per-RPI `.env` (gitignored), committed `.env.example`. Mid-term: doppler / 1Password Connect / HashiCorp Vault. |

### 4.1 Recommended commit-first list (before next RPI ship)

1. `docker-compose.yml` (cleaned: token externalised, healthchecks added, init+stop_grace_period)
2. `docker-compose.local.yml`, `docker-compose.dev.yml`, `Dockerfile*` (with pinned base images, .dockerignore)
3. `scripts/bootstrap_rpi.sh`, `scripts/restore_db.sh`
4. `.env.example`
5. `docs/rpi-provisioning.md`
6. `HANDOFF.md`, `README.md`

### 4.2 Aggressive .gitignore additions

```
.env
.env.*
!.env.example
*.dump
*.dump.gz
*.sql.gz
.bkit/
agentic-runs/
reports/                # or whitelist .html only
.claude/worktrees/
ksys_app/**/*_backup_*.py
ksys_app/**/*.bak
ksys_app/**/*.disabled
```

---

## 5. TimescaleDB / ARM / pg_cron Specifics

| # | Issue | Severity | Evidence | Recommendation |
|---|-------|----------|----------|----------------|
| T-01 | **pg_cron ABI mismatch between Alpine 1.6.7 build (PG18) and TimescaleDB:latest-pg17 base.** Dev workaround in compose drops pg_cron from preload; RPI prod still loads it. Risk: next `docker pull` on RPI flips the same image, pg_cron fails to load, DB won't start, all Virtual Tag calcs stop. | CRITICAL | `HANDOFF.md:71-75`, `docker-compose.dev.yml:17-25` | Pin DB image to a known-good digest. Optionally compile pg_cron from source against PG17 in the Dockerfile to bypass Alpine package version churn. |
| T-02 | Hypertable + continuous aggregate setup is **partially scripted**. `migrations/` has 13 SQL files (init virtual tags, pg_cron migration, training/forecast schema). But continuous aggregates (5 views) failed to import on the dev DB rebuild due to 2.21.3 → 2.27 catalog drift (HANDOFF.md). | HIGH | `migrations/` listing, `HANDOFF.md:88-89` | Add `migrations/000_reset_caggs.sql` that drops and recreates all CAGGs at a known TimescaleDB version. Apply automatically in `bootstrap_rpi.sh`. |
| T-03 | `migrations/` lacks a numeric ordering convention. `001_alarm_indexes.sql` and `01_init_virtual_tags.sql` mix 3-digit and 2-digit prefixes; `20251014_*` is date-prefixed. No applied/not-applied tracking. | MED | `migrations/` directory listing | Adopt either golang-migrate or alembic. Or at minimum: rename to 4-digit (`0001_*`, `0002_*`) and maintain a `schema_migrations` table that `bootstrap_rpi.sh` consults. |
| T-04 | No documented PG17 / TimescaleDB version compatibility matrix for the app. App expects `timescaledb 2.21.3` (per restore procedure). If RPI pulls a newer base image, hypertable functions may differ. | MED | `HANDOFF.md:81-82` | Document required `timescaledb` extension version in `README.md`. `bootstrap_rpi.sh` asserts version, refuses to proceed on mismatch. |
| T-05 | Backup procedure documented but not automated. No cron/systemd timer that produces `ecoanp_full_$(date).dump` on each RPI. The `backup/` volume on RPI prod will grow forever or stay empty. | MED | `docker-compose.yml:18` bind mount `./backup`; no cron entry in repo | Add a `backup-cron` service to compose: lightweight alpine image with `pg_dump` weekly via crond. Push to off-RPI store (NAS / S3) for DR. |
| T-06 | No verification that the bundled `timescale/timescaledb:latest-pg17` is multi-arch (it is, but unpinned). ARM64 manifest version may differ from amd64 dev. | LOW | `Dockerfile.rpi-pgcron:6` | Pin by digest captures the per-arch manifest. Same fix as D-01 / T-01. |

---

## A. Top 3 Ship-Blockers Before Next RPI

| Rank | Blocker | Owner action | Eta |
|------|---------|--------------|-----|
| 1 | Cloudflare Tunnel token in plaintext at `docker-compose.yml:130` + `postgres:postgres` everywhere | Rotate token in CF dashboard. Move to `.env`. Generate per-RPI DB password. Update all compose `${VAR}` references. | 0.5 day |
| 2 | No `bootstrap_rpi.sh` + `restore_db.sh` → every new RPI is manual SSH + tribal knowledge | Write both scripts (Bash). Test on a wiped RPI (or VM with ARM64 qemu). Land in `scripts/`. | 2 days |
| 3 | DB image pinned to `latest-pg17` + pg_cron ABI fragility | Pin image to digest; verify pg_cron loads on a clean rebuild; document the version-lock in README. | 1 day |

If any of those three slip, sending a second RPI is rolling dice.

## B. Multi-RPI Rollout Readiness Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| Fresh-RPI bootstrap script | **No** | `scripts/deploy_gcp.sh` is empty; only Windows `.bat` exists |
| Per-RPI config externalised (`.env`) | **No** | All values hardcoded in compose |
| Secrets removed from repo (token, DB pwd) | **No** | CF token + DB password committed plaintext |
| DB restore scripted (TimescaleDB-aware) | **No** | Procedure exists in HANDOFF + RPI_PGCRON_DEPLOYMENT.md, not codified |
| Golden DB seed defined and stored off-host | Partial | Dumps in `backup/`, gitignored, no off-RPI mirror documented |
| Image registry (pull instead of build) | **No** | Every RPI runs `docker build` |
| Multi-arch build / `buildx` workflow | **No** | No `--platform`; builds whatever host arch is |
| Healthchecks on all services | Partial | DB only |
| Resource limits (RPI is 8 GB shared) | **No** | Risk of scheduler OOM killing DB |
| `init: true` + `stop_grace_period` in prod compose | **No** | Only in local compose, after the zombie-socket incident |
| Per-RPI hostname / Cloudflare hostname strategy | **No** | Single tunnel token = single hostname; collision if N>1 |
| Git remote verified + push cadence enforced | Partial | Remote exists; uncommitted prod-compose changes at HEAD |
| Branch protection / PR review on `master` | **No** | Single-machine push |
| CI (lint + test + build) on PR | **No** | No `.github/workflows/` |
| Automated DB backup cron on RPI | **No** | Bind mount exists, nothing writes to it on a schedule |
| Centralised log/metrics for fleet | **No** | Acceptable for N=1, blocker for N>3 |
| Migration tracking (which RPI ran which SQL) | **No** | No `schema_migrations` table |
| TimescaleDB extension version assertion | **No** | Restore docs say 2.21.3 — not enforced at runtime |
| pg_cron extension confirmed loadable on pinned image | Partial | Works on current RPI; fragile vs Alpine upstream churn |
| Documented rollback procedure per RPI | Partial | RPI_PGCRON_DEPLOYMENT.md §rollback exists, but pre-pg_cron only |

**Score**: 0 fully-met / 4 partial / 16 not-met out of 20.

**Bottom line**: at current readiness, deploying RPI #2 will be a manual repeat of RPI #1, taking ~half a day per unit and accumulating drift. With the three blockers fixed and items R-01 / R-02 / R-04 in place, per-RPI deploy time drops to ~30 minutes and fleet drift becomes detectable.

---

_End of audit._
