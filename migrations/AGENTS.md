# migrations — TimescaleDB SQL

## Purpose

Schema-evolution and setup SQL for the `ecoanp` TimescaleDB. **Not auto-applied on startup** — either baked
into the DB dump (restored via `pg_restore`) or run manually on demand.

## Ownership

Hand-written `.sql` scripts. Inventory (apply in this order, not alphabetical):

| # | What |
|---|---|
| 001 | alarm query indexes (composite + partial) |
| 01–08 | virtual-tag tables, functions, pg_cron scheduler |
| 09 | continuous-aggregate refresh policies (`influx_agg_1m/10m/1h/1d`, `predictions_hourly`) |
| 010 | viewer/tag display registry |
| 011 | normalize QC-rule unit |
| 012 | AI knowledge + chat-history tables (RAG) |
| 013 | **CRITICAL** cagg refresh fix — non-null `end_offset` + real-time aggs |
| 20251014_* | `training_evaluation` offline-backtest table |
| 20251017_* | `forecast_player_cache` |

## Local Contracts

- **Apply manually**: `docker exec -i rpi-finished-pgai-db psql -U postgres -d ecoanp < migrations/NNN_*.sql`
  (README §3). Numbered files apply in numeric order, then date-stamped ones.
- **Idempotent always**: `CREATE ... IF NOT EXISTS`, `DROP ... IF EXISTS`, `create_hypertable(..., if_not_exists => true)`,
  cagg policies with `if_exists => true`. Re-running must not fail or corrupt.
- **cagg refresh gotcha (do not reintroduce)**: a continuous-aggregate refresh policy with `end_offset = NULL`
  leaves a watermark that **stalls refresh** (caused a 6-day data stall on 2026-06-24). Always set an explicit
  non-null `end_offset`; prefer `materialized_only = false` (real-time aggs) where refresh reliability matters.
  Migration `013` is the canonical fix — any new dump must include it.

## Work Guidance

- New migration: next sequential number, `NNN_shortname.sql` (e.g. `014_user_audit_logs.sql`).
- Test against a local dump restore before promoting into the production dump.
- After applying pg_cron-related migrations, verify with `SELECT * FROM cron.job`.

## Verification

Re-apply on a fresh restore (must succeed twice). For caggs, confirm a non-null `end_offset` and that the
job actually advances: `SELECT * FROM timescaledb_information.jobs` / `job_stats`.

## Child DOX Index

None.
