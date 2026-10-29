"""Purpose-specific operator views laid out like designs/metrics-dashboard (KPI row, chart card,
tables) with design_guide tokens; no colour literals here (tests/test_scada_theme.py)."""
import reflex as rx
from ..states.scada_state import ScadaState as S
from ..components.scada import (card, section_title, pill, quality_pill, kpi, note, facts, table,
                                icon_button, segment, search)

TIME_TICK = "(value) => new Date(value).toLocaleTimeString('ko-KR', {timeZone:'Asia/Seoul', hour12:false})"
TIME_LABEL = "(value) => new Date(value).toLocaleString('ko-KR', {timeZone:'Asia/Seoul', hour12:false})"
# design_guide §3/§8 series and chart chrome as tokens; assets/scada.css repeats them on the
# recharts classes so a mode change repaints without a re-render.
C = dict(final="var(--am-series-a)", uncertain="var(--am-series-amber)", cond="var(--am-series-violet)",
         raw="var(--am-muted-2)", grid="var(--am-grid)", axis="var(--am-axis)", cursor="var(--am-accent)")
AXIS_TICK = {"fill": "var(--am-axis-text)", "fontSize": 11, "fontFamily": "var(--am-font-mono)"}


def split(main, aside, wide=False):
    return rx.grid(main, aside, class_name="scada-split wide" if wide else "scada-split")


def stack(*children):
    return rx.box(*children, class_name="scada-stack")


def known(value):
    """Counts read as '—' until the first snapshot arrives."""
    return rx.cond(S.as_of == "—", "—", value.to_string())


def tag_cell(row, key, numeric):
    return rx.table.row_header_cell(
        rx.el.button(row["tag"], type="button", on_click=S.select_tag(row["tag"]), class_name="scada-row-button"),
        rx.el.span(row["channel"], class_name="scada-sub"))


def point_table():
    return card(section_title("점별 수신 근거", "선택 현장의 최신 표본"),
        rx.box(search(S.search, S.change_search, "태그·채널 검색"), rx.spacer(),
               rx.el.span(S.filtered_rows.length(), " / ", S.observed_tags, "점",
                          class_name="scada-mono scada-muted scada-small"),
               class_name="scada-toolbar"),
        rx.cond(S.visible_rows.length() > 0,
            table(S.visible_rows, "points",
                  cell={"tag": tag_cell,
                        "quality_d": lambda row, key, numeric: rx.table.cell(quality_pill(row)),
                        "unit_d": lambda row, key, numeric: rx.table.cell(row[key], class_name="scada-muted-cell")},
                  row_props=lambda row: {"class_name": rx.cond(row["tag"] == S.tag, "scada-selected", "")}),
            note(rx.cond(S.search != "", "검색어와 일치하는 태그 없음", "선택 현장의 최신 표본 없음"))),
        rx.box(rx.spacer(), icon_button("chevron-left", "이전 페이지", flat=True, on_click=S.previous_page,
                                        disabled=S.page <= 0),
               rx.el.span(S.page + 1, " / ", S.page_count, class_name="scada-mono scada-small"),
               icon_button("chevron-right", "다음 페이지", flat=True, on_click=S.next_page,
                           disabled=S.page >= S.page_count - 1),
               class_name="scada-toolbar foot"))


def latest_detail():
    return card(section_title("선택 태그", S.selected["tag"], right=quality_pill(S.selected)),
        facts(S.selected_facts),
        rx.box(rx.link("이 태그의 트렌드 열기", href="/trend", class_name="scada-link"),
               class_name="scada-note foot"))


def sample_detail():
    return card(section_title("표본 근거", "슬라이더로 선택", right=quality_pill(S.inspected_sample)),
        rx.cond(S.series.length() > 0, facts(S.sample_facts), note("선택한 표본 없음")))


def legend_item(label, series, dash=False):
    """§8.5: manual dot + label in the card footer; a dashed ring marks a dashed series."""
    return rx.el.span(rx.el.span(class_name=f"dot {series} dash" if dash else f"dot {series}"), label,
                      class_name="item")


def signal_chart():
    def line(key, name, color, series, width=2.0, dash="", fill=False, dot=False, hidden=None):
        attrs = {"fillOpacity": 1 if fill else 0}
        if dash:
            attrs["strokeDasharray"] = dash
        if hidden is not None:
            attrs["hide"] = hidden
        return rx.recharts.area(data_key=key, name=name, type_="monotone", stroke=color, stroke_width=width,
                                fill="url(#scada-final-fill)" if fill else color, custom_attrs=attrs,
                                class_name=series, dot={"r": 2, "fill": color} if dot else False,
                                connect_nulls=False, is_animation_active=False)
    compare = S.phase != "비교"
    graph = rx.recharts.area_chart(
        rx.recharts.cartesian_grid(vertical=False, stroke=C["grid"], stroke_dasharray="3 3"),
        rx.recharts.x_axis(data_key="epoch_ms", type_="number", scale="time", domain=["dataMin", "dataMax"],
            tick_formatter=TIME_TICK, axis_line=False, tick_line=False, min_tick_gap=64,
            tick=AXIS_TICK, stroke=C["axis"], dy=10, height=32),
        rx.recharts.y_axis(domain=["auto", "auto"], axis_line=False, tick_line=False,
            tick=AXIS_TICK, stroke=C["axis"], dx=-5, width=64, allow_decimals=True),
        rx.recharts.tooltip(content_style={"backgroundColor": "var(--am-card)",
            "border": "1px solid var(--am-border-strong)", "borderRadius": "var(--am-r-lg)",
            "boxShadow": "var(--am-shadow-tooltip)", "fontSize": "12px", "padding": "12px",
            "fontFamily": "var(--am-font-sans)", "color": "var(--am-text)"},
            item_style={"fontFamily": "var(--am-font-mono)", "fontWeight": 600},
            label_style={"fontFamily": "var(--am-font-mono)", "color": "var(--am-muted-2)", "marginBottom": "6px"},
            custom_attrs={"labelFormatter": rx.Var(_js_expr=TIME_LABEL)}),
        line("raw", "원시값", C["raw"], "series-raw", width=1.5, hidden=compare),
        line("cond", "처리값", C["cond"], "series-violet", dash="2 3", hidden=compare),
        line("final_good", "최종값 · 양호", C["final"], "series-a", fill=True),
        line("final_uncertain", "최종값 · 불확실", C["uncertain"], "series-amber", width=1.5, dash="5 4", dot=True),
        rx.recharts.reference_line(x=S.cursor_time, stroke=C["cursor"], stroke_dasharray="3 4"),
        rx.recharts.brush(data_key="epoch_ms", height=24, stroke="var(--am-border-strong)", fill="var(--am-row)",
                          tick_formatter=TIME_TICK, key=S.site_id + S.tag + S.minutes),
        data=S.series, height=360, margin={"top": 10, "right": 10, "left": 0, "bottom": 0})
    return card(
        rx.box(rx.box(rx.el.div(S.tag, class_name="tag scada-wrap"),
                      rx.el.div("원천 최신 ", S.selected["observed_d"], class_name="scada-mono scada-muted scada-small")),
               rx.spacer(), rx.el.span(S.selected["final_d"], class_name="scada-signal-value"),
               rx.cond(S.selected["unit_d"] != "—",
                       rx.el.span(S.selected["unit_d"], class_name="scada-muted scada-small")),
               quality_pill(S.selected), class_name="scada-signal-head"),
        rx.box(segment([(m, m + "분") for m in ["5", "15", "60"]], S.minutes, S.change_window),
               rx.spacer(),
               segment([("FINAL", "최종값"), ("비교", "원시·처리 비교")], S.phase, S.set_phase),
               class_name="scada-toolbar", flex_wrap="wrap"),
        rx.el.svg(rx.el.defs(rx.el.svg.linear_gradient(
            rx.el.svg.stop(offset="5%", stop_color=C["final"], stop_opacity=0.2),
            rx.el.svg.stop(offset="95%", stop_color=C["final"], stop_opacity=0.0),
            id="scada-final-fill", x1="0", y1="0", x2="0", y2="1", class_name="scada-grad-a")),
            width="0", height="0", position="absolute"),
        rx.cond(S.series.length() > 0,
            rx.fragment(
                rx.box(graph, class_name="scada-chart"),
                rx.box(legend_item("최종값 · 양호", "series-a"),
                       legend_item("최종값 · 불확실", "series-amber", dash=True),
                       rx.cond(S.phase == "비교", rx.fragment(legend_item("원시값", "series-raw"),
                                                              legend_item("처리값", "series-violet", dash=True))),
                       rx.el.span("불량·결측 구간은 선을 잇지 않음"),
                       rx.cond(S.series_truncated, rx.el.span("최근 2,000개 표본만 표시")),
                       class_name="scada-legend"),
                rx.box(rx.flex(rx.el.span("표본 선택", class_name="scada-var-label"), rx.spacer(),
                               rx.el.span(S.inspected_sample["time_p"], class_name="scada-mono scada-small")),
                       rx.slider(value=[S.sample_position], min=0, max=S.sample_max, step=1,
                                 on_change=S.inspect_sample, aria_label="이력 표본 선택", margin_top="12px"),
                       class_name="scada-inspection-slider")),
            note("선택 기간에 이 태그의 이력 없음 — 기간을 넓혀 지금 조회를 누르세요")),
        raised=True)


def overview():
    def attention(row):
        return rx.box(pill(row["issue"], row["issue_tone"]),
            rx.box(rx.el.button(row["tag"], type="button", on_click=[S.select_tag(row["tag"]), rx.redirect("/trend")],
                                class_name="scada-row-button"),
                   rx.el.span(row["channel"], class_name="scada-sub"), min_width="0"),
            rx.spacer(), rx.el.span(row["final_d"], class_name="scada-number"),
            rx.cond(row["unit_d"] != "—", rx.el.span(row["unit_d"], class_name="scada-muted scada-small")),
            class_name="scada-attention-row")

    def recent_condition(row, key, numeric):
        return rx.table.cell(pill(row["condition"], row["tone"]))

    def mix_row(m):
        return rx.box(pill(m["label"], m["tone"]), rx.el.span(m["count_d"], class_name="n"), class_name="scada-mix-row")

    return stack(
        rx.box(kpi("관측 태그", known(S.observed_tags), "선택 현장 최신 표본", icon="tags", unit="점"),
               kpi("확인 대상", known(S.attention_rows.length()), "품질·값 계약·갱신 지연", icon="list-checks", unit="건"),
               kpi("불량 태그", known(S.bad_tags), "최종 품질 불량", rx.cond(S.bad_tags > 0, "error", ""),
                   icon="shield-alert", unit="점"),
               kpi("관측 채널", known(S.channel_rows.length()), "최신 표본의 채널", icon="network", unit="개"),
               kpi("저장 표본", known(S.received), "선택 기간 저장분", icon="database", unit="건"),
               class_name="scada-kpis"),
        split(card(section_title("우선 확인할 자료", "선택하면 트렌드로 이동"),
                   rx.cond(S.attention_rows.length() > 0, rx.foreach(S.attention_rows, attention),
                           note("확인 대상 없음 — 품질 불량·값 계약 오류·갱신 지연 0건")), raised=True),
              card(section_title("관측 채널", "최신 표본 기준"),
                   rx.cond(S.channel_rows.length() > 0, table(S.channel_rows, "channels"),
                           note("관측된 채널 없음")))),
        split(card(section_title("최근 경보 사건", "최대 5건"),
                   rx.cond(S.alarm_state.contains("조회 실패"),
                           note("경보 이력을 읽지 못했습니다 — 지금 조회를 누르세요"),
                           rx.cond(S.alarms.length() > 0,
                                   table(S.recent_alarms, "recent_alarms", cell={"condition": recent_condition}),
                                   note("선택 현장의 최근 경보 사건 없음"))),
                   rx.box(rx.link("경보 화면 열기", href="/alarms", class_name="scada-link"),
                          class_name="scada-note foot")),
              card(section_title("저장 표본 품질", rx.el.span("선택 기간 ", S.received, "건", class_name="scada-mono")),
                   rx.cond(S.good + S.uncertain + S.bad > 0,
                           rx.box(rx.box(rx.foreach(S.quality_mix, lambda m: rx.box(
                                         class_name=m["tone"].to(str), width=m["width"])), class_name="scada-mix-bar"),
                                  rx.foreach(S.quality_mix, mix_row), class_name="scada-mix"),
                           note("선택 기간 저장 표본 없음")))))


def workflow():
    def step(idx, name, value, sub, off=False):
        return rx.box(rx.el.span(idx, class_name="idx"), rx.el.span(name, class_name="name"),
                      rx.el.span(value, class_name="val"), rx.el.span(sub, class_name="sub"),
                      class_name="scada-step off" if off else "scada-step")
    return stack(card(section_title("업무·제어 흐름", "현장 업무 모델 미등록"),
        rx.box(step("01", "측정", known(S.observed_tags), "관측 태그"),
               step("02", "판단", known(S.attention_rows.length()), "확인 대상"),
               step("03", "시뮬레이션·승인", "미연결", "승인 기록 없음", True),
               step("04", "조치·피드백", "미연결", "조치 기록 없음", True),
               class_name="scada-steps"),
        note("실행 이력은 업무 모델과 실행 기록이 연결된 뒤 표시됩니다", foot=True)))


def trend():
    return split(signal_chart(), sample_detail(), wide=True)


def alarms():
    def message_cell(row, key, numeric):
        return rx.table.row_header_cell(rx.el.button(row["message_d"], type="button",
                                                     on_click=S.select_alarm(row["event"]),
                                                     class_name="scada-row-button wrap"))

    def condition_cell(row, key, numeric):
        return rx.table.cell(pill(row["condition"], row["tone"]))

    listing = card(section_title("최근 발생 이력", "최대 100건"),
        rx.cond(S.alarm_state.contains("조회 실패"), note("경보 이력을 읽지 못했습니다 — 지금 조회를 누르세요"),
                rx.cond(S.alarms.length() > 0,
                        table(S.alarms, "alarms", cell={"message_d": message_cell, "condition": condition_cell},
                              row_props=lambda row: {"class_name": rx.cond(
                                  row["event"] == S.selected_alarm["event"], "scada-selected", "")}),
                        note("선택 현장의 경보 사건 없음"))))
    details = card(section_title("선택 사건", rx.cond(S.alarms.length() > 0, S.selected_alarm["message_d"], "")),
        rx.cond(S.alarms.length() > 0, facts(S.alarm_facts), note("선택할 사건 없음")))
    return split(listing, details)


def communication():
    return split(
        card(section_title("채널 Health", "원천 상태"),
             rx.cond(S.health_note != "", note(S.health_note),
                     rx.cond(S.health_rows.length() > 0, table(S.health_rows, "health"),
                             note("수신된 Health 없음 — 연결 상태를 추정하지 않음"))),
             note("채널 시도·응답 기록 미연결 — 끊김·복구 구간은 기록 연결 뒤 표시", foot=True)),
        card(section_title("채널별 최신 수신", "저장 표본 기준"),
             rx.cond(S.channel_rows.length() > 0, table(S.channel_rows, "channel_latest"),
                     note("관측된 채널 없음"))))


def flow():
    hops = ["Edge", "전달기", "Kafka", "Consumer", "상위 DB"]
    path = []
    for i, name in enumerate(hops):
        path.append(rx.el.span(name, class_name="hop on" if name == "상위 DB" else "hop"))
        if i < len(hops) - 1:
            path.append(rx.icon("chevron-right", size=14, aria_hidden="true"))
    return stack(
        card(section_title("전달 경로", "상위 DB 저장분만 관측"),
             rx.box(*path, class_name="scada-path"),
             rx.box(kpi("저장 표본", known(S.received), "선택 기간", icon="database", unit="건"),
                    kpi("조회 기준", S.as_of_d, "KST", icon="clock"),
                    class_name="scada-kpis pair"),
             note("단계별 지연·보충 지표 미연결 — cursor·offset 기록 연결 뒤 표시", foot=True)),
        split(point_table(), latest_detail()))


def scada_view(kind):
    return {"overview": overview, "process": workflow, "trend": trend,
            "alarms": alarms, "flow": flow, "communication": communication}[kind]()
