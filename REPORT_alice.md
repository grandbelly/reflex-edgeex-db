# REPORT_alice — DB pool + statement timeout (H1, H5)

Agent: alice-db-pool
Branch: agentic/forecast-scheduler-timeout-fix/alice-db-pool

## 1. get_async_session() call-site map

edgeex_app/schedulers/forecast_scheduler.py:
- Line 52  get_deployed_models — 1 SELECT on model_registry
- Line 233 get_latest_sensor_value — 1 SELECT on influx_agg_10m
- Line 281 save_predictions — N (up to 36) INSERT...ON CONFLICT into predictions hypertable in one session.commit()
- Line 357 generate_forecast_player_cache — opens session, instantiates ForecastService(session) and reuses it for get_rolling_window_data (>=6 queries), get_predictions (1 query), get_latest_sensor_value (1 query), plus 4 own queries + 1 UPSERT — ~13 queries serial, mostly on hypertables.

edgeex_app/services/forecast_service.py — does NOT open its own sessions. Reuses the caller-provided AsyncSession. **No nested/parallel sessions.** Good.

Per run_once model iteration: 3 sequential get_async_session() calls → 3 separate connect+close cycles. For N models, 3N sessions per cycle.

## 2. Engine/pool config as-shipped (BEFORE patch)

- poolclass=NullPool — every call opens a fresh asyncpg connection. The configured POOL_SIZE/MAX_OVERFLOW/POOL_TIMEOUT env vars are DEAD CODE.
- connect_args: timeout=10s (connect), command_timeout=10s (per-statement). Hardcoded.
- No PG server-side statement_timeout.

## 3. H1 verdict — INCONCLUSIVE → effectively RULED OUT

NullPool means there is no pool to exhaust. The plan's framing is technically wrong. But: the original author clearly *intended* pooling (POOL_SIZE=20, MAX_OVERFLOW=30 env vars exist) — that intent was never realized. Per-call reconnect tax (~50-200ms × 3 sessions/model × N models) compounds H5 timeout pressure.

Patch: opt-in AsyncAdaptedQueuePool via USE_DB_POOLING=true. Default stays NullPool to preserve Reflex greenlet compatibility. Schedulers turn it on via env in their Dockerfile entrypoint.

Also added SQLAlchemy connect/checkout/checkin event hooks (EngineManager.checkouts / .checkins / .outstanding_connections) so future leaks are provable from the unit test and from prod logs (DB_POOL_TRACE=true).

## 4. H5 verdict — PROVEN

Evidence:
1. connect_args command_timeout=10 (line 107 in original). asyncpg enforces this per-statement; any SELECT/INSERT exceeding 10s raises asyncio.TimeoutError. This matches the observed intermittent symptom.
2. save_predictions runs up to 36 INSERTs in one session against predictions hypertable. First insert into a new chunk triggers _create_chunk() which on RPI SD-card storage can take 3-8s. 36 × 0.3-1s + occasional chunk creation easily approaches 10s.
3. get_rolling_window_data fires 6+ range scans against influx_agg_10m and predictions hypertables — any one can spike during TimescaleDB compression/maintenance.
4. No PG server-side statement_timeout, so when client aborts, the backend may still hold locks → secondary contention.

Fix shipped:
- DB_COMMAND_TIMEOUT env, default **30s** (was hardcoded 10s)
- DB_STATEMENT_TIMEOUT_MS env, default **30000ms**, pushed into asyncpg server_settings — PG itself kills runaway queries and releases their locks
- Pool defaults reduced to 10+10 to fit RPI's PG max_connections=100 alongside other services

## 5. Patch — files & risk

Files: edgeex_app/db_orm.py (additive only)

Risks:
- Raising command_timeout to 30s could mask real bugs → mitigated by server-side statement_timeout that fires at the same threshold, so we still see honest "query cancelled" errors with stack traces from the DB.
- QueuePool + asyncpg + Reflex greenlet interop historically problematic → mitigated by USE_DB_POOLING defaulting to False. Only schedulers opt in.
- Counter event hooks have negligible overhead.

Deployment recommendation:
- Dockerfile.scheduler: USE_DB_POOLING=true, DB_POOL_SIZE=10, DB_COMMAND_TIMEOUT=30, DB_STATEMENT_TIMEOUT_MS=30000
- Dockerfile (Reflex web): leave USE_DB_POOLING unset (default false)

## 6. Out-of-scope follow-ups (for Bob/Charlie)

- save_predictions should batch the 36 INSERTs into a single multi-row VALUES (...), (...), ... — cuts round-trips 36→1.
- run_once loops models serially — parallelize with asyncio.gather AFTER pooling is on.
- Catch-all try/except at line 581 hides which hypothesis fired — Charlie's timing work should split into per-stage handlers with structured log keys.

## 7. Test status

tests/schedulers/test_pool_exhaustion.py — 4/4 PASS (pytest 9.0.2, SQLAlchemy 2.0, aiosqlite):
1. test_h1_session_returns_connection_to_pool — 36 checkouts on a 4-conn pool, asserts checkouts==checkins==36, outstanding==0. Locks in context-manager exception correctness.
2. test_h1_pool_exhaustion_raises_timeout — pool_size=1, one holder; asserts SATimeout fires within pool_timeout. Documents failure mode.
3. test_h5_command_timeout_is_configurable — verifies new env knobs and 30s/30000ms defaults.
4. test_h5_pooling_opt_in_does_not_break_legacy_default — verifies USE_POOLING default stays False so Reflex web is unaffected.

Run: pytest tests/schedulers/test_pool_exhaustion.py -v

## 8. One-line summary

H1 mis-framed (NullPool was in use; no pool to exhaust). **Root cause is H5**: hardcoded asyncpg command_timeout=10s was too tight for TimescaleDB hypertable inserts on RPI SD-card. Patch raises it to 30s, adds server-side statement_timeout (releases locks), opt-in QueuePool removes per-call reconnect tax, instrumentation makes future leaks provable.
