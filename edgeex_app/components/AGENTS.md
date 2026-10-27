# edgeex_app/components — reusable UI

## Purpose

Composable, function-based Reflex UI building blocks. Pure presentation — no business logic, no DB.

## Ownership

Components grouped by domain: `trends/` (with `inputs/`, `charts/`, `cards/`, `layout/`, `feedback/`),
`alarms/`, `cards/`, `charts/`, `dashboard/`. `design_system.py` holds color/typography/spacing tokens.

## Local Contracts

- Every component is a **function returning `rx.Component`** — no class-based components.
- Bind to State via Vars (`value=State.x`, `on_change=State.set_x`). **Never call services or DB here.**
- Use the active native Reflex theme tokens consistently. Legacy `design_system.py` belongs to older screens; do not mix its CSS with the active Dashboard template.
- Group by feature domain; deep feature sets get sub-dirs (see `trends/`).

## Work Guidance

- Reuse an existing component before writing one — check the domain folder and `trends/` sub-modules first.
- Keep components stateless: data and events come in as props/Var bindings from the page's State.

## Verification

Visual: render via the owning page on `:14000`. No component unit harness.

## Child DOX Index

None — sub-folders are organizational, governed by this contract.

## Active stock template

`scada.py` now implements the stock_market top navigation, dark local tokens, compact scope bar, section frame and separate quality/freshness semantics. `docs/mini_scada_component_layout_design.md` owns menu roles. Do not restore the earlier Company sidebar or repeated KPI/table layout. `assets/scada.css` owns the shared tokens; charts use the same palette with independent series and quality meanings.

Follow `docs/mini_scada_visualization_contract.md`. The owner selected `stock_market_dashboard` for observation layout and `stock_graph_app` for real-time charts. Preserve their information hierarchy and controls while binding the SCADA contracts; document the actual source adaptations. Do not treat every menu as a generic KPI/table page. The first stock migration is implemented; actual browser acceptance is pending after the dedicated Edge launch was rejected by automatic approval review.

`scada.py` owns the shared template wrapper, navigation, scope form and native card/metric/quality components. Upstream commit and adaptations are in `docs/reflex_template_source.md`. Keep six-page layout, spacing, typography and responsive navigation shared. Views bind only to typed State Vars; no example KPI values, DB calls or inferred healthy states. Site/tag/time form changes apply on submit. Search and table pagination are local to the completed snapshot. Preserve accessible control names and native buttons.
