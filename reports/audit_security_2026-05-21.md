# Security Audit — KSys IoT Reflex (2026-05-21)

Scope: secrets, DB credentials, OWASP Top 10 quick scan (SQLi/XSS/SSRF/auth/deserialization), container security, dependency spot-check.
Branch: `refactor/rpi-baseline-sync` @ `b6c1944`. Target: ~1 month rollout to additional RPI units.

Severity calibration: this is a LAN-attached SCADA-style IoT dashboard. "Critical" assumes the device is reachable from any user who can hit the host (RPI on plant LAN, or proxied through cloudflared/`ksys.kr`).

---

## CRITICAL

### C1. Cloudflare Tunnel token committed in plaintext
- **File:** `docker-compose.yml:130`
- **Evidence:**
  ```yaml
  cloudflared:
    command: tunnel --no-autoupdate run --token eyJhIjoiMDQwMzY4ZDNlZjZjOThjYzY1OTllMTljNGVmZDkyNDEiLCJ0IjoiMDk2NjcxNDQtZDI3NC00NzYzLTg4OWUtZjkzZmNlM2NiZDYzIiwicyI6...
  ```
- **Impact:** Anyone with read access to this repo/branch can run `cloudflared tunnel run --token <X>` on their own machine and instantly impersonate the `ksys.kr` tunnel endpoint — full traffic interception, session hijack, MitM against every RPI deployment that points to this tunnel. Token is account-bound (`a: 040368d3ef6c98cc6599e19c4efd9241`), so revoking requires Cloudflare dashboard access.
- **Fix:**
  1. Rotate the tunnel now via Cloudflare dashboard ("Networks → Tunnels → Refresh token"). Treat the existing token as compromised — it has been in git history since before this branch.
  2. Move new token to `.env` (already gitignored) and reference it via `${CF_TUNNEL_TOKEN}` in `docker-compose.yml`.
  3. `git filter-repo` or BFG to purge the token from all historical commits before any public mirroring.

### C2. Hardcoded production remote-DB credentials in source
- **File:** `ksys_app/states/sync_monitor_state.py:156-162`
- **Evidence:**
  ```python
  config = RemoteDBConfig(
      host="59.10.187.46", port=9543,
      database="iot_cloud_v2_exaxt_stp",
      username="exaxt", password="exaxt00"
  )
  ```
- **Impact:** A public-routable IPv4 (`59.10.187.46:9543`) with a real username and a guessable password is committed to git. Anyone with repo access — including any future RPI image pulled by a customer — can connect directly to the upstream IoT cloud DB and read/modify the `iot_cloud_v2_exaxt_stp` schema. The `exaxt00` pattern (username + "00") suggests this is a stable, never-rotated credential.
- **Fix:**
  1. Rotate the `exaxt` DB password immediately on `59.10.187.46`.
  2. Restrict the remote DB's `pg_hba.conf` to known RPI WAN egress IPs.
  3. Load via `os.getenv("REMOTE_DB_PASSWORD")` from container env / `.env`.
  4. Strip from git history (same `git filter-repo` pass as C1).

### C3. No authentication anywhere — 179 `@rx.event` handlers on the open backend
- **Files:** `rxconfig.py:35` (`backend_host="0.0.0.0"`), `ksys_app/ksys_app.py:161-188`, all `ksys_app/states/*`, `ksys_app/pages/*`
- **Evidence:** `grep -i "is_authenticated|current_user|require_auth|login_required|logged_in"` across `ksys_app/` returns **zero** matches. 179 `@rx.event` handlers (across 20 state files) execute on any incoming WebSocket. `add_page`/`@rx.page` routes (`/`, `/trend`, `/alarms`, `/training-wizard`, `/ai`, `/comm`, `/model-performance`, `/viewer-tag`, `/scada-alarms`, …) are all publicly reachable. The `ksys.kr` cloudflared tunnel (C1) exposes them to the public internet.
- **Impact:** Any unauthenticated visitor can:
  - Trigger `sync_tags` and force a connection to the upstream IoT DB (C2 credentials).
  - Trigger model retraining via `/training-wizard` events (CPU exhaustion DoS on Pi).
  - Read every sensor / alarm / forecast — even when the operator believes the dashboard is "internal-only" because it's behind cloudflared.
- **Fix (before RPI rollout):**
  1. Add a minimal `AuthState` with a shared-secret bearer (Reflex `rx.cond` gating on `AuthState.is_authenticated` for every page) or a Cloudflare Access policy in front of the tunnel.
  2. At the very least, decorate every mutating `@rx.event` with an auth precondition that returns early if the user isn't logged in.
  3. If shipping to multiple customers, per-tenant credentials (not a shared password).

---

## HIGH

### H1. Default `postgres:postgres` DB password in three compose files
- **Files:** `docker-compose.yml:9-10`, `docker-compose.dev.yml:27-28`, `docker-compose.local.yml:24,25,83,84,102`, `20251030-rpi-pgcron/docker-compose.rpi-pgcron.yml:13`
- **Evidence:** `POSTGRES_PASSWORD=postgres` plus `TS_DSN=postgresql://postgres:postgres@...` baked into env strings.
- **Impact:** On RPI deployments where port `5432` is on the LAN (it is — `ports: 5432:5432`), any LAN scanner finds an open Postgres with `postgres/postgres`. TimescaleDB instance contains operational sensor history, alarms, model registry (with pickled models — see H3).
- **Fix:**
  1. Generate a strong password per-RPI; inject via `${POSTGRES_PASSWORD}` from `.env` (already gitignored).
  2. In `docker-compose.yml`, drop the `ports: 5432:5432` host bind — only `rpi-finished-reflex-app` and the scheduler need DB access via the docker network. Use `expose: ["5432"]` instead.
  3. Same change in `docker-compose.local.yml` once local dev workflow is verified to still work via container exec.

### H2. SQL injection via `dynamic_rag_engine` and `llamaindex_rag_engine` — f-string `tag_name` interpolation
- **Files:**
  - `ksys_app/ai_engine/dynamic_rag_engine.py:183-184, 197-198`
  - `ksys_app/ai_engine/llamaindex_rag_engine.py:243-247`
- **Evidence:**
  ```python
  tag_list = ','.join([f"'{t}'" for t in detected_tags])
  tag_condition = f"WHERE tag_name IN ({tag_list})"
  sql = f"""SELECT tag_name, ... FROM {view} {tag_condition} ..."""
  ```
- **Impact:** `detected_tags` ultimately traces back to the user's chat query (`/ai` page → `AIState` → `query` text → tag extractor). A natural-language query like `';DROP TABLE alarm_history;--` becomes a tag candidate and is concatenated unescaped. Combined with C3 (no auth), this is a one-step DB compromise from the public web. The view name (`{view}`) is also interpolated unsanitized.
- **Fix:**
  1. Use bind parameters: build a `tuple(detected_tags)` and call `text("... WHERE tag_name = ANY(:tags)").bindparams(tags=detected_tags)`.
  2. Whitelist `view` against a fixed set (`{"influx_latest","influx_agg_1m","influx_agg_5m",...}`) before interpolation.

### H3. Pickle deserialization of DB-stored model artifacts
- **Files:**
  - `ksys_app/schedulers/forecast_scheduler.py:109,140`
  - `ksys_app/ml/training_pipeline.py:681,693`
  - `ksys_app/ml/prediction_model.py:269`
  - `ksys_app/ml/forecast_pipeline.py:501` (`joblib.load` — uses pickle internally)
- **Evidence:** `pickle.loads(metadata['model_pickle'])` where `model_pickle` is a BYTEA column read from `model_registry`. If an attacker reaches the DB (H1 default password or SQLi via H2), they can INSERT a malicious pickle into `model_registry.model_pickle`; the scheduler will then execute arbitrary code as root inside `rpi-finished-forecast-scheduler` on its next training cycle.
- **Impact:** Container-root RCE on every RPI on the next scheduled run after a DB compromise. The 15s `FORECAST_PICKLE_LOAD_TIMEOUT` bound is a liveness fix, not a security control — `pickle.loads` executes attacker code during the load itself.
- **Fix:**
  1. Sign model blobs with HMAC (`cryptography` is already in `requirements.txt`). Verify signature before `pickle.loads`.
  2. Switch to safer serialization for trained models (`skops`, ONNX) where the model type allows; pickle remains only for legitimate StatsForecast/Prophet objects, gated by the HMAC check.
  3. Run schedulers as non-root (see H4) so a successful exploit doesn't get container-root.

### H4. All containers run as root (no `USER` directive)
- **Files:** `Dockerfile`, `Dockerfile.scheduler`, `Dockerfile.data-injector`, `Dockerfile.pipeline`, `20251030-rpi-pgcron/Dockerfile.rpi-pgcron`, `schedulers/Dockerfile`
- **Evidence:** `grep "USER " Dockerfile*` returns 0 matches.
- **Impact:** Combined with the `./ksys_app:/app/ksys_app` bind mount in `docker-compose.local.yml:35` and `docker-compose.yml:47`, an RCE inside the container (e.g., via H3) gets write access to the host project tree as UID 0. Even without the bind mount, container-escape primitives become more dangerous.
- **Fix:** Add `RUN useradd -m -u 1000 app && chown -R app /app` and `USER app` to all four runtime Dockerfiles. Update the bind-mount permissions accordingly.

### H5. NOTIFY channel + identifier interpolation (lower-severity SQLi)
- **Files:** `ksys_app/monitoring/alarm_monitor.py:142`, `ksys_app/monitoring/alarm_monitor_fixed.py:170`, `ksys_app/utils/db_events.py:36,79`
- **Evidence:** `await conn.execute(f"NOTIFY alarm_event, '{event_id}'")` and `await conn.execute(f"LISTEN {self.channel}")`. `event_id` is `f"ALM-...-{tag_name}"`; `tag_name` ultimately originates from sensor config (low-trust if anyone can write to `virtual_tag_config` via H1/H2).
- **Impact:** Single-quote in a tag name (`O'Brien`) closes the literal and concatenates additional SQL into the NOTIFY payload. Less severe than H2 because reaching `tag_name` requires DB-write or admin event access, but compounds with C3.
- **Fix:** Use parameter binding (`text("NOTIFY alarm_event, :ev").bindparams(ev=event_id)` — note: PG NOTIFY doesn't accept positional params, so the safe pattern is `pg_notify('alarm_event', :payload)`).

---

## MEDIUM

### M1. `INTERVAL '{hours} hours'` f-string in sensor_service
- **File:** `ksys_app/services/sensor_service.py:210-218`
- **Evidence:** `WHERE bucket >= NOW() - INTERVAL '{hours} hours'`. `hours` parameter on `get_sensor_chart_data` is typed `int = None` but Python doesn't enforce — if a state file passes a `str` from a query param the f-string injects directly.
- **Impact:** Latent injection. Currently the only callers pass int literals, but the type system isn't enforcing.
- **Fix:** `hours_int = int(hours)` before interpolation, or use `make_interval(hours => :h)` with bind param.

### M2. Volume bind-mount of source into prod container
- **File:** `docker-compose.yml:47-49` — `./ksys_app:/app/ksys_app`, `./rxconfig.py:/app/rxconfig.py`
- **Impact:** Production deployment uses the same dev-style bind mount as `docker-compose.local.yml`. A container compromise (H3/H4) gets write access to the host's `ksys_app/` — persistent backdoor across container restarts. Defeats the purpose of an immutable image.
- **Fix:** For RPI production, bake source into the image (`COPY . .` already in `Dockerfile:27`) and drop the bind mount. Keep bind mount only in `docker-compose.local.yml` for hot-reload dev.

### M3. `--loglevel debug` in production compose
- **File:** `docker-compose.yml:67-68`
- **Impact:** Reflex debug mode logs full DSN strings, state diffs, and stack traces. Combined with H1 (default DB password in DSN), every `docker logs` invocation prints `postgresql://postgres:postgres@...` and any exception that wraps user input leaks query content.
- **Fix:** `--loglevel info` (or `warn`) for `docker-compose.yml`. `docker-compose.local.yml` already uses `info` (good).

### M4. `sentence-transformers==2.2.2` pinned — old release with pickle-based model loading
- **File:** `requirements.txt:13`
- **Impact:** Version 2.2.2 is from 2023 and predates HuggingFace's safe-serialization defaults. Loading a model via `SentenceTransformer("name")` will pickle.load weights if the upstream HF repo ships pytorch_model.bin instead of safetensors — combined with H3 this is another deserialization route.
- **Fix:** Bump to `sentence-transformers>=3.0.0` (which prefers safetensors) or pass `use_safetensors=True` explicitly at load sites in `ksys_app/ai_engine/`.

### M5. `psql -U postgres -c "CREATE DATABASE ecoanp;" >nul 2>&1`
- **File:** `scripts/deploy_local.bat:21`
- **Impact:** Local dev only, but mirrors the H1 default-credential assumption into operations scripts. Promote-to-RPI risk.
- **Fix:** Pull from `.env` once H1 is fixed.

---

## LOW

- **L1.** `ksys_app/ai_engine/rag_engine_pgvector.py:380` — literal `"your-api-key-here"` placeholder. Not a real secret but flagged by basic scanners; replace with `os.getenv` lookup that raises if missing.
- **L2.** No `init: true` / `stop_grace_period` in `docker-compose.yml` (RPI prod) — only `docker-compose.local.yml` has them. Container SIGKILL behaviour can leak ports (already documented in `feedback_no_host_reflex_zombie.md`), making forensic post-mortem after a security incident harder.
- **L3.** `ksys_app/integration/external_systems.py:90` — `WeatherAPIConnector` `base_url` hardcoded to `https://api.openweathermap.org` (good — fixed URL is anti-SSRF). No SSRF surface found in the codebase (no user-controlled URLs flow to `aiohttp.get`).
- **L4.** Healthcheck endpoint exposed publicly: `pg_isready` is a `CMD-SHELL` inside the container, so this is fine — no HTTP probe surface added.
- **L5.** Missing security headers (CSP, HSTS, X-Frame-Options). Reflex doesn't set these by default. Add via a reverse proxy (cloudflared can inject HSTS) or a Reflex middleware once auth is in place.

---

## Top 3 Must-Fix-Before-RPI-Rollout

| # | Severity | Finding | One-line fix | Owner ETA |
|---|----------|---------|--------------|-----------|
| 1 | CRITICAL | C1 Cloudflare tunnel token in `docker-compose.yml:130` | Rotate token in CF dashboard, move to `.env`, purge from git history | DevOps, < 1 day |
| 2 | CRITICAL | C3 Zero authentication on 179 `@rx.event` handlers across all pages | Add Cloudflare Access policy in front of tunnel OR ship a minimal `AuthState` shared-secret gate | Backend, < 1 week |
| 3 | HIGH | H2 SQLi via chat-query `tag_name` interpolation in `dynamic_rag_engine.py:184` and `llamaindex_rag_engine.py:247` | Replace `f"WHERE tag_name IN ({tag_list})"` with `WHERE tag_name = ANY(:tags)` bind param | AI/Backend, < 2 days |

Bonus must-do (paired with #2): rotate `exaxt00` upstream-DB password (C2) before the next RPI image build, otherwise C2 + C3 = trivial public-internet pivot to the IoT cloud.
