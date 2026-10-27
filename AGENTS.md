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

- 미니 SCADA는 메뉴별 판단 목적을 먼저 정하고 공식 Reflex 템플릿과 컴포넌트를 매칭한다. 전체 비교는 `docs/reflex_template_catalog.md`, 화면/동작/자료/수용 설계는 `docs/mini_scada_component_layout_design.md`, 오프라인 배치 보드는 `docs/mini_scada_layout_board.html`이 소유한다. stock_market_dashboard의 공통 외형과 stock_graph_app의 실시간 그래프를 기준으로 삼되 여섯 메뉴를 같은 KPI·태그 표로 반복하지 않는다. 예제 State·가짜 수치·정상 애니메이션을 운전 근거로 이식하지 않는다.

- 상위 앱의 엣지 연동 시연은 엣지 PC에서 실행하고, 오너 PC에서는 원격 화면 또는 터널을 통한 브라우저 접속으로 확인한다.
- 오너 PC의 앱 직접 실행이나 DB 미연결 화면을 엣지 연동 시연으로 대체하지 않는다. 시연 요청을 로컬 실행 허가로 해석하지 않는다.
- 엣지 셸·GUI·설치본 조작은 전담 엣지 Codex 세션이 수행한다. 터널은 프런트엔드와 백엔드 WebSocket 경로를 함께 제공해야 한다.

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
- **Never run Reflex on the owner Windows PC.** Run on the deployment/edge host under that host's operating rules; the owner browser connects remotely or through a tunnel. Host Python kills can leak zombie LISTEN sockets.

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
