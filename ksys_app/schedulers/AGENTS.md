# ksys_app/schedulers — background forecast pipeline

## Purpose

Async background schedulers running synchronized 10-minute windows to generate, backfill, and score
forecasts without blocking the web UI.

## Ownership

Schedulers: **ForecastScheduler** (x:00/x:10/… loads models, predicts, inserts), **ActualValueUpdater**
(x:01/x:11/… backfills measured actuals), **PerformanceAggregator** (x:03/x:13/… computes MAE/RMSE vs actual).
VirtualTagScheduler is **migrated to PostgreSQL `pg_cron`** — not Python here.

## Local Contracts

- **Singletons**: `get_forecast_scheduler()`, `get_actual_value_updater()`, `get_performance_aggregator()`.
- **Lifecycle**: `SchedulerManager.start_all()` spawns one `asyncio.create_task` per scheduler with
  delay-aligned timing; started from `SchedulerState` on app mount. `stop_all()` cancels + `.stop()`s each.
- Each cycle logs start/end and catches its own errors; `_ModelSkipped` marks a per-model skip
  (`outcome=skipped` in DB) without failing the cycle.
- Writes: `predictions`, `sensors_actual`, `model_performance_metrics`.

## Work Guidance

- New scheduler = singleton getter + register in `SchedulerManager.start_all()` with aligned timing.
- Respect the ML-layer timeout guards; never let a hung model stall the window.
- Ref: `docs/forecast_result/ONLINE_FORECAST_REDESIGN_20251014.md`.

## Verification

Check container logs for cycle start/end lines; confirm rows land in `predictions` / `model_performance_metrics`.

## Child DOX Index

None.
