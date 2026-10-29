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

Verify the six routes in isolated localhost preview (`:3101`) using orca; production/container verification is separate.

## Active routes

`scada.py` registers `/`, `/workflow`, `/trend`, `/alarms`, `/edge-monitor`, `/comm` through `@rx.page` and the stock template decorator. Preserve the six menu concepts: dashboard, workflow, trend, alarms, communication status and Edge monitoring. `on_load=ScadaState.initialize` reads only when live or not loaded. Other page files are migration history and are not imported by the active app. Do not mount their write routes or dashboard schedulers.

## Child DOX Index

None.
