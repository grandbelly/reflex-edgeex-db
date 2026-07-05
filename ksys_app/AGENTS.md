# ksys_app — Reflex application

## Purpose

The Reflex web app for the RO/water-quality SCADA dashboard. Owns the full request path:
route → page → view → components, fed by State, fed by services/queries over TimescaleDB.

## Ownership

Owns app bootstrap and cross-layer wiring. Files at this level:
- `ksys_app.py` — app entry: loads `.env`, inits DB pool, registers pages (by importing page modules),
  pins dark theme, starts schedulers via `SchedulerState` on mount.
- `db.py` — asyncpg singleton pool: `get_pool()`, `q(sql, params)`. Raw hot-path SQL.
- `db_orm.py` — SQLAlchemy async engine/session: `get_async_session()`. ORM/batch path. NullPool by
  default (Reflex bg events need fresh conns); `USE_DB_POOLING=true` opts schedulers into a real pool.
- `security.py` — `validate_startup_security()`, CSP headers. `middleware.py` — request middleware.

Smaller dirs owned here without their own doc: `config/`, `utils/` (incl. `logger.py` — use `get_logger`),
`models/`, `monitoring/`, `design_system/`, `alarm/`, `water_quality/`, `diagnostics/`, `maintenance/`,
`performance/`, `integration/`, `controllers/`, `resources/`, `styles/`.

## Local Contracts

- **Layering (do not skip layers):**
  `@rx.page` → `views/` (compose) → `components/` (pure UI) ← `states/` (data + `@rx.event`) ← `services/` (business logic) ← `queries/` (raw SQL) ← `db.py`/`db_orm.py`.
- **Components never call services or DB** — they only bind to State Vars. Business logic lives in State/services.
- **Services return plain dicts**, never ORM objects (greenlet-safe, serializes cleanly to State).
- **Register a page** by adding `@rx.page(...)` in its module and importing it in `ksys_app.py`. No `app.add_page()`.
- **AI imports stay lazy** behind `ENABLE_AI_FEATURES` — never import openai/sklearn/numpy on an unconditional boot path.

## Work Guidance

- New feature = new State (`states/`) + view (`views/`) + page (`pages/`); reuse `components/`.
- New data need = add a query fn in `queries/`, wrap business logic in a `services/` method, call from State.
- Log via `ksys_app.utils.logger.get_logger(__name__)`; mask secrets (see `load_env` masking).

## Verification

- `pytest` (suites in `ksys_app/tests/` and repo `tests/`). Run inside the Docker container, not the host.
- Manual: app on `:14000`; restart container to recompile (prod mode).

## Child DOX Index

- `states/AGENTS.md` — Reflex State layer (reactive data, event handlers, polling).
- `components/AGENTS.md` — reusable function-based UI components.
- `pages/AGENTS.md` — `@rx.page` route modules.
- `services/AGENTS.md` — business-logic layer over queries (session-injected, returns dicts).
- `queries/AGENTS.md` — raw async SQL, adaptive aggregation-view selection.
- `ai_engine/AGENTS.md` — RAG + multi-agent layer (guarded by `ENABLE_AI_FEATURES`).
- `ml/AGENTS.md` — time-series forecasting models (plugin architecture).
- `schedulers/AGENTS.md` — background forecast schedulers (10-minute pipeline).

`views/` (thin page↔component composition, `*_view.py`) is owned here — add a child doc only if it grows
its own contracts.
