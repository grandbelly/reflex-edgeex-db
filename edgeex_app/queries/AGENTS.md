# edgeex_app/queries — raw SQL data access

## Purpose

Thin SQL wrappers over TimescaleDB. Pure data access — no business logic.

## Ownership

Query modules, e.g.: `latest.py` (latest snapshot), `metrics.py` (timeseries from agg views),
`realtime.py` (raw bucketed `influx_hist`), `tags.py` (tag list), `qc.py` (QC rules).

## Local Contracts

- **Raw SQL only**, positional params (`$1, $2`) via `db.q()` — asyncpg, not the ORM.
- **Adaptive view selection**: pick the aggregation table by time window — 1m <1h, 10m <24h, 1h <7d,
  1d beyond (`_auto_view()`-style pickers). Never scan raw hypertable for wide windows.
- Hot reads may use a short in-memory TTL cache (`cachetools.TTLCache`, ~10s) — keep TTLs small.
- No business logic, no cross-query orchestration — that lives in `services/`.
- The edge health query propagates failures to the service for explicit UI error reporting.

## Work Guidance

- New query = a function taking explicit params, returning list[dict]. Choose the aggregation view by window.
- Continuous-aggregate view names are the source of truth — see `migrations/AGENTS.md` for the cagg setup.

## Verification

`pytest`; confirm the right aggregation view is chosen for the requested window.

## Child DOX Index

None.
