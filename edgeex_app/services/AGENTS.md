# edgeex_app/services — business logic layer

## Purpose

Business logic + TimescaleDB-aware data assembly. Wraps `queries/`, normalizes results for the UI.

## Ownership

Key services: `TrendService` (time-series by aggregation level), `AlarmService` (rule-based alerts +
pagination), `SensorService` (latest values + QC rules + status), `ForecastService` (ML predictions).

## Local Contracts

- **Session injection**: `__init__(self, session: AsyncSession)`. No global session manager.
- **`SET LOCAL statement_timeout` (5–10s)** at the start of each method — catches runaway hypertable scans.
- **Return dicts, not ORM objects.** Use `.mappings().all()` then `dict(row)`.
- **No lazy loading** — ORM relationships set `lazy="raise"`; fetch joined data eagerly in one query.
- Call `queries/` functions for raw SQL; do not inline complex SQL that belongs in a query module.
- `EdgeMonitorService` uses the shared asyncpg query functions without an ORM session.
  Its snapshot contains `db_connected`, nested `kpi`, table lists, and `chart_series` points
  with `time`, `raw`, `cond`, `final`, `quality`; preserve nullable values without substitution.
  Alarm KPI counts all stored alarms, independent of the recent-list limit. Health query failures
  appear in `db_error`; received-message counters are not a count of health sites.
  Initial chart selection uses the newest stored sample, so old smoke-test tags cannot displace
  current site data merely through alphabetical ordering.

## Work Guidance

- New business operation = a service method. Keep raw SQL in `queries/`, orchestration/shaping here.
- States instantiate the service with a pooled session, call the method, store the returned dicts.

## Verification

`pytest` (`edgeex_app/tests/`). Watch query latency in logs (queries >1s are logged by `db.q`).

## Child DOX Index

None.
