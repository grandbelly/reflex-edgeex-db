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

`scada.py` implements `designs/design_guide.md` ("Grafana in Apple Mode", Appendix A) as decided by the owner in D-1029-02: metrics-dashboard shell (header h-14, variables row, sub-nav pill tabs for the six menus, p-6 body), KPI tiles, cards, pills, search, segments and Recharts styling. Colours exist only as `--am-*` tokens in the two blocks of `assets/scada.css` (light `:root`, dark `:root:not(.light)`); components and views name no colour, and Radix variables are pointed at the tokens. Dark is the default and the header toggle flips everything; `tests/test_scada_theme.py` pins the guide values, the dark pairs and zero colour literals. Where DS-017 differs, the guide wins (quality good/uncertain/bad = success/warning/error, accent blue for selection); alarm pills stay neutral until a level→priority contract exists. Interpretations are listed in `docs/quality-rework-1028-r3/README.md`. `docs/mini_scada_component_layout_design.md` owns menu roles. The §7.4 sidebar is not used; navigation stays in the sub-nav tabs.

Follow `docs/mini_scada_visualization_contract.md`. The owner selected `stock_market_dashboard` for observation layout and `stock_graph_app` for real-time charts. Preserve their information hierarchy and controls while binding the SCADA contracts; document the actual source adaptations. Do not treat every menu as a generic KPI/table page. The first stock migration is implemented; actual browser acceptance is pending after the dedicated Edge launch was rejected by automatic approval review.

`scada.py` owns the shared template wrapper, navigation, scope form, card, `pill` (word + tone), `kpi`, `facts`, one-line `note` and the spec-driven `table`. Tables take their columns, numeric right alignment and min width from `states/scada_display.TABLES`; add a column there, never inline. Missing capability or empty data is one factual `note` line, not an icon box. Never nest `rx.text` (or a box) inside `rx.text`; React logs `<p>` inside `<p>`. `tests/test_scada_render.py` walks all six page trees for this. Upstream commit and adaptations are in `docs/reflex_template_source.md`. Keep six-page layout, spacing, typography and responsive navigation shared. Views bind only to typed State Vars; no example KPI values, DB calls or inferred healthy states. Site/tag/time form changes apply on submit. Search and table pagination are local to the completed snapshot. Preserve accessible control names and native buttons.
