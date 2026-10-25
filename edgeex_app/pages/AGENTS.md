# edgeex_app/pages — route modules

## Purpose

URL route handlers. Each module registers one route and returns the page's component tree.

## Ownership

One module per route; multi-step flows become subpackages (e.g. `training_wizard/` with step + result modules).

## Local Contracts

- Register with `@rx.page(route="/path", title="...", on_load=[...])` in the module.
- **A page is active only if its module is imported in `edgeex_app/edgeex_app.py`** — add the import there too.
- Page fn returns one `rx.Component`, usually wrapped in the shared layout shell.
- `on_load` triggers State event handlers (e.g. start streaming/polling).

## Work Guidance

- Keep pages thin: compose `views/` + `components/`; data/logic lives in the page's State.
- AI page (`ai_insights.py`, `/ai`) is imported under the `ENABLE_AI_FEATURES` guard — keep it there.

## Verification

Navigate the route on `:14000` after a container restart (prod recompile).

## Routes (current)

`/` dashboard · `/trend` trend_enhanced_v2 · `/alarms` + `/alarms_rt` + `/alarms_hist` (+ `_new` variants) ·
`/forecast` · `/model-performance` · `/comm` · `/training-wizard` · `/viewer-tag` · `/workflow` ·
`/scada-alarms` + `/scada-alarm-comparison` · `/ai` (guarded).

## Child DOX Index

None.
