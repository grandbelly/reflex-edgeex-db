# edgeex_app — Reflex application

## Purpose

The Reflex web app for the RO/water-quality SCADA dashboard. Owns the full request path:
route → page → view → components, fed by State, fed by services/queries over TimescaleDB.

## Ownership

Owns app bootstrap and cross-layer wiring. Files at this level:
- `edgeex_app.py` — native Reflex 0.10 entry; registers only `pages/scada.py`, without import-time DB connections, environment-file loading or schedulers.
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
- **Register a page** by adding `@rx.page(...)` in its module and importing it in `edgeex_app.py`. No `app.add_page()`.
- **AI imports stay lazy** behind `ENABLE_AI_FEATURES` — never import openai/sklearn/numpy on an unconditional boot path.
- DSN helpers must never log the DSN, its prefix, or its return value through a logging decorator.

## Work Guidance

- New feature = new State (`states/`) + view (`views/`) + page (`pages/`); reuse `components/`.
- New data need = add a query fn in `queries/`, wrap business logic in a `services/` method, call from State.
- Log via `edgeex_app.utils.logger.get_logger(__name__)`; mask secrets (see `load_env` masking).
- Legacy `/edge-monitor` used the CSS tokens and reactive `page_container`, `header_bar`, `section_header`,
  `card`, `status_pill`, `pill_button`, and `kpi_tile` helpers in `design_system/am.py`.

## Verification

- `pytest` (suites in `edgeex_app/tests/` and repo `tests/`). Run inside the Docker container, not the host.
- Manual: app on `:14000`; restart container to recompile (prod mode).
- Kafka ingestion acceptance does not verify the web UI. Verify `/edge-monitor` in a browser,
  including backend events, DB connectivity, row values, and BAD/NULL chart gaps.

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

## Active SCADA profile (Reflex 0.10.1)

The owner requested distinct visualization purposes on 2026-10-28. `docs/mini_scada_visualization_contract.md` governs menu responsibilities and acceptance scenarios. Keep the original concepts: dashboard, workflow, trends, alarms, communication status and Edge monitoring. Shared data contracts do not justify repeating the same tag table in every menu. The owner's template choices and source study are in `docs/reflex_template_study.md`; the current first profile is an implementation baseline, not accepted final UX.

The owner requested latest Reflex via Context7 and an official template on 2026-10-28. `components/scada.py` now adapts the pinned stock_market layout and stock_graph chart hierarchy (source in `docs/reflex_template_source.md`); the earlier Dashboard wrapper is history. `pages/scada.py` registers the six routes. `views/scada_view.py` composes native Reflex components. `assets/scada.css` owns the `designs/design_guide.md` `--am-*` tokens (light/dark) and responsive layout; `rxconfig.py` sets dark as the default color mode and lets Radix inherit it (D-1029-02).

`SCADA_DATA_SOURCE` defaults to `edge_vqt`; the active entry rejects legacy/unknown profiles. `TS_DSN` must be provided explicitly. All DB sessions are read-only. Legacy modules remain as migration source and are not claimed to work under 0.10; do not import their State, ORM, write handlers or schedulers into the active entry.

`ScadaState(rx.State)` is independent of the old BaseState. A browser moment timer requests bounded five-second reads. No private Reflex connection map or infinite server polling loop is used. The common form applies site/tag/time together. Search/pagination use the received snapshot. Fixed mode preserves it through navigation; explicit apply/refresh requests a new snapshot. The stock-template views have different menu bodies: attention/channels, unbound workflow, numeric-time trend and sample inspector, event list/detail, connection-history capability/Health and delivery evidence. Historical samples carry their own ingestion time/reasons and an in-snapshot time key. The shared State/read snapshot remains a migration boundary; purpose-specific query separation is still pending, not claimed complete.

Verify in an isolated Windows venv: install `requirements-edge-web.txt`, `pip check`, `python -m unittest discover -s tests -p "test_scada_*.py" -v`, `reflex compile --no-rich`, preview build and orca browser checks. Set `PYTHONUTF8=1` and a separate `REFLEX_DIR`. Actual read-only SQL parity is recorded in the acceptance receipt. Container/RPI production checks are separate; this work does not change running containers.
