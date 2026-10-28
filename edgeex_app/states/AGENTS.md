# edgeex_app/states — Reflex State layer

## Purpose

Reactive state: single source of truth for UI data and event handlers. One State per major feature.

## Ownership

Feature State classes + a few split into subpackages when large (`training_state/`, `forecast_player_state/`).
Key files: `base_state.py` (shared base), `dashboard_realtime_grouped.py`, `trend_state*`, `alarms_enhanced.py`,
`scheduler_state.py` (scheduler lifecycle on app mount), `training_state/`, `forecast_player_state/`.

## Local Contracts

- The active `ScadaState` inherits `rx.State` directly. Legacy State classes use `BaseState`; do not mix their lifecycle/private connection helpers into the active profile.
- Naming: `<Feature>State`. Private fields use leading underscore (`_polling_active`, `_polling_task`).
- Event handlers use `@rx.event`; background polling uses `@rx.event(background=True)` + `async def`.
- States call **services** (instantiated with a DB session), get back dicts, store them on Vars.
  States do not embed raw SQL — that belongs in `queries/` behind a service.
- `EdgeMonitorState` instantiates `EdgeMonitorService` (uses the shared asyncpg query pool),
  reads KPI fields from `snapshot["kpi"]`, and chart points from `snapshot["chart_series"]`.
  A failed DB summary query must display a connection error, not a successful empty result.
  The initial quality ratio is 0 until measured data arrive.
  BAD/NULL chart indicators use paper-coordinate annotations, never invented numeric samples.

## Work Guidance

- Large/multi-step state → split into a subpackage (`<feature>_state/{state.py, cache.py}`), not one giant file.
- Mutate state only inside event handlers; keep computed values in `@rx.var`.

## Verification

`pytest` (see `edgeex_app/tests/`). No state-specific harness beyond that.

## Child DOX Index

None. Subpackages here are implementation detail, not separate DOX boundaries.

## Shared SCADA context

`scada_display.py` is pure display shaping (no Reflex import): State adds `*_d` keys (short KST time, padded decimals, Korean quality terms, tone) beside the unchanged service fields, and `facts()` omits unknown values. It also owns the table spec and the 1366/1920 width model tested in `tests/test_scada_display.py`.

`ScadaState` owns site/tag/5-15-60-minute context, snapshot, local search and 12-row pagination across the six routes. A native browser `rx.moment` timer calls finite background events; it stops producing requests when the component/tab disappears. Single-flight reads coalesce; obsolete scope responses cannot overwrite new scope. Every mutation in a background event occurs under `async with self`.

Fixed mode invalidates in-flight reads and preserves the completed snapshot across navigation. Tag selection in fixed mode only selects that snapshot's detail and clears history; explicit refresh/apply or live resume gets new data. All controls have explicit events; no automatic setters or inherited mutable fields. There are no command/write events.

The stock UI adds phase selection, explicit 5/15/60-minute reads, in-snapshot historical-sample selection and stable event-ID selection. Historical inspection uses its own source/ingestion time and reason, never the latest-row detail. Source time is numeric on the plot; ReferenceLine rounds only its drawing position to integer milliseconds while the inspector retains the full ISO microseconds. Grouped channel counts are observed-tag membership, not connectivity. Attention rows use observed quality/value-contract/freshness only, not inferred process alarms.
