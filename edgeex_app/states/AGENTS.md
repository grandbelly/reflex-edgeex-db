# edgeex_app/states — Reflex State layer

## Purpose

Reactive state: single source of truth for UI data and event handlers. One State per major feature.

## Ownership

Feature State classes + a few split into subpackages when large (`training_state/`, `forecast_player_state/`).
Key files: `base_state.py` (shared base), `dashboard_realtime_grouped.py`, `trend_state*`, `alarms_enhanced.py`,
`scheduler_state.py` (scheduler lifecycle on app mount), `training_state/`, `forecast_player_state/`.

## Local Contracts

- All states inherit `BaseState(rx.State)` (polling control, loading/error, sidebar/theme).
- Naming: `<Feature>State`. Private fields use leading underscore (`_polling_active`, `_polling_task`).
- Event handlers use `@rx.event`; background polling uses `@rx.event(background=True)` + `async def`.
- States call **services** (instantiated with a DB session), get back dicts, store them on Vars.
  States do not embed raw SQL — that belongs in `queries/` behind a service.

## Work Guidance

- Large/multi-step state → split into a subpackage (`<feature>_state/{state.py, cache.py}`), not one giant file.
- Mutate state only inside event handlers; keep computed values in `@rx.var`.

## Verification

`pytest` (see `edgeex_app/tests/`). No state-specific harness beyond that.

## Child DOX Index

None. Subpackages here are implementation detail, not separate DOX boundaries.
