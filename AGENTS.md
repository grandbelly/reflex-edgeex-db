# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## User Preferences

When the user requests a durable behavior change, record it here or in the relevant child AGENTS.md

---

# Project: Reflex-edgeEX (풍도 RO/수질 모니터링 SCADA)

A Reflex (Python) web dashboard for reverse-osmosis water-quality monitoring, backed by
TimescaleDB 17 (PostgreSQL 17) + pgai + pg_cron. Deployed to a Raspberry Pi 5 in Docker.

## Runtime & Ports

- **Framework**: Reflex, `app_name="edgeex_app"`. Frontend `:14000`, backend `:14001` (see `rxconfig.py`).
- **DB**: TimescaleDB, database `ecoanp`. DSN from env var `TS_DSN` (never hardcode).
- **Theme**: pinned dark ("RO control-room"); no light/dark toggle. Tailwind V3 plugin + `assets/styles.css`.
- **AI features**: gated by env `ENABLE_AI_FEATURES` (default true). `/ai` page and the `ai_engine`
  layer import openai/sklearn/numpy lazily — never import them at module top-level on a path that
  boots unconditionally, or a slim image without those deps crashes the whole app.

## Deployment & Sync (CRITICAL — read before any RPI work)

| | |
|---|---|
| RPI server | `ssh tion@192.168.0.80` |
| RPI app path | `/home/tion/deployment/20251030-rpi-finished/` |
| Local (this repo) | `C:\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo` |
| Containers | `rpi-finished-reflex-app`, `rpi-finished-pgai-db` |
| Web port | 14000 |

- Sync local↔RPI with `scp` (see `CLAUDE.md` for exact paths). This is **not** the `reflex-edgeex-refactor` folder.
- Restart app: `docker restart rpi-finished-reflex-app`. DB: `docker exec -it rpi-finished-pgai-db psql -U postgres -d ecoanp`.
- **Never run Reflex on the Windows host** — Docker container only. Host Python kills leak zombie LISTEN sockets.

## Global Conventions

- **DB access has two sanctioned paths — never open ad-hoc connections.** Raw hot-path: `edgeex_app/db.py`
  asyncpg singleton pool (`get_pool()` / `q(sql, params)`, positional `$1,$2`). ORM/batch path: `edgeex_app/db_orm.py`
  SQLAlchemy async session (`get_async_session()`). Services return plain dicts to State, never ORM objects.
- **Pages register via `@rx.page` decorator** inside their module; importing the module in `edgeex_app/edgeex_app.py`
  is what activates the route. No `app.add_page()` calls.
- Korean Windows: this repo's dev host defaults to cp949 — read/write files as UTF-8 (`PYTHONUTF8=1`).
- See `CLAUDE.md` for the agentic-pipeline workflow and `HANDOFF.md` for in-flight session state.

## Child DOX Index

- `migrations/AGENTS.md` — TimescaleDB SQL migrations: schema, hypertables, continuous-aggregate refresh policies.
- `edgeex_app/AGENTS.md` — the Reflex application (UI, state, data, AI, schedulers). Owns its own child index.

Other repo dirs owned directly by this root (no child doc): `docs/` (PDCA plan/design/report),
`tests/` & `edgeex_app/tests/` (pytest), `scripts/` & `schedulers/` (ops helpers), `backup/` (DB dumps),
`assets/` (static + `styles.css`), `saved_models/` (trained model artifacts).
