"""Purpose-specific operator views: stock-template hierarchy, DS-017 semantics, designs/ craft."""
import reflex as rx
from ..states.scada_state import ScadaState as S
from ..components.scada import card, section_title, pill, quality_pill, kpi, note, facts, table

TIME_TICK = "(value) => new Date(value).toLocaleTimeString('ko-KR', {timeZone:'Asia/Seoul', hour12:false})"
TIME_LABEL = "(value) => new Date(value).toLocaleString('ko-KR', {timeZone:'Asia/Seoul', hour12:false})"
# Chart strokes mirror assets/scada.css tokens (SVG attributes do not resolve CSS variables reliably).
C = dict(leaf="#b8e35c", ink="#eaf3ee", ink2="#b9cdc2", muted="#8fa89b", raw="#5f7a6d",
         line="#24382e", raised="#1d362b", strong="#335043", well="#0a1410")


def split(main, aside, wide=False):
    return rx.grid(main, aside, class_name="scada-split wide" if wide else "scada-split")


def stack(*children):
    return rx.box(*children, class_name="scada-stack")


def known(value):
    """Counts read as '—' until the first snapshot arrives."""
    return rx.cond(S.as_of == "—", "—", value.to_string())


def tag_cell(row, key, numeric):
    return rx.table.row_header_cell(
        rx.button(row["tag"], on_click=S.select_tag(row["tag"]), variant="ghost", size="1",
                  class_name="scada-tag-button"),
        rx.text(row["channel"], size="1", color="var(--muted)"))


def point_table():
    return card(section_title("점별 수신 근거", "선택 현장의 최신 표본"),
        rx.flex(rx.input(placeholder="태그·채널 검색", value=S.search, on_change=S.change_search,
                         aria_label="태그·채널 검색", max_width="270px", size="2"), rx.spacer(),
                rx.text(S.filtered_rows.length(), " / ", S.observed_tags, "점", size="1",
                        class_name="scada-mono", color="var(--muted)"),
                class_name="scada-toolbar", align="center"),
        rx.cond(S.visible_rows.length() > 0,
            table(S.visible_rows, "points",
                  cell={"tag": tag_cell,
                        "quality_d": lambda row, key, numeric: rx.table.cell(quality_pill(row)),
                        "unit_d": lambda row, key, numeric: rx.table.cell(row[key], class_name="scada-muted-cell")},
                  row_props=lambda row: {"class_name": rx.cond(row["tag"] == S.tag, "scada-selected", "")}),
            note(rx.cond(S.search != "", "검색어와 일치하는 태그 없음", "선택 현장의 최신 표본 없음"))),
        rx.flex(rx.spacer(), rx.icon_button("chevron-left", on_click=S.previous_page, disabled=S.page <= 0,
                                            variant="ghost", size="1", aria_label="이전 페이지"),
            rx.text(S.page + 1, " / ", S.page_count, size="1", class_name="scada-mono"),
            rx.icon_button("chevron-right", on_click=S.next_page, disabled=S.page >= S.page_count - 1,
                           variant="ghost", size="1", aria_label="다음 페이지"),
            class_name="scada-toolbar", align="center", gap="8px"))


def latest_detail():
    return card(section_title("선택 태그", "최신 표본"),
        rx.flex(rx.text(S.selected["tag"], weight="bold", class_name="scada-wrap"), rx.spacer(),
                quality_pill(S.selected), class_name="scada-toolbar", align="center"),
        facts(S.selected_facts),
        rx.box(rx.link("이 태그의 트렌드 열기", href="/trend", size="2"), class_name="scada-note foot"))


def sample_detail():
    return card(section_title("표본 근거", "슬라이더로 선택"),
        rx.flex(rx.text("품질", size="1", color="var(--muted)"), rx.spacer(),
                quality_pill(S.inspected_sample), class_name="scada-toolbar", align="center"),
        rx.cond(S.series.length() > 0, facts(S.sample_facts), note("선택한 표본 없음")))


def legend_item(label, color, dash=""):
    return rx.el.span(rx.el.span(class_name="sw", style={"borderColor": color, "borderTopStyle": "dashed" if dash else "solid"}),
                      label)


def signal_chart():
    def line(key, name, color, width=1.0, dash="", fill=False, dot=False, hidden=None):
        attrs = {"fillOpacity": 1 if fill else 0}
        if dash:
            attrs["strokeDasharray"] = dash
        if hidden is not None:
            attrs["hide"] = hidden
        return rx.recharts.area(data_key=key, name=name, type_="linear", stroke=color, stroke_width=width,
                                fill="url(#scada-final-fill)" if fill else color, custom_attrs=attrs,
                                dot={"r": 2, "fill": color} if dot else False,
                                connect_nulls=False, is_animation_active=False)
    compare = S.phase != "비교"
    graph = rx.recharts.area_chart(
        rx.recharts.cartesian_grid(vertical=False, stroke=C["line"], stroke_dasharray="3 3"),
        rx.recharts.x_axis(data_key="epoch_ms", type_="number", scale="time", domain=["dataMin", "dataMax"],
            tick_formatter=TIME_TICK, axis_line=False, tick_line=False, min_tick_gap=64,
            tick={"fill": C["muted"], "fontSize": 12, "fontFamily": "ui-monospace,Consolas,monospace"}, height=28),
        rx.recharts.y_axis(domain=["auto", "auto"], axis_line=False, tick_line=False,
            tick={"fill": C["muted"], "fontSize": 12, "fontFamily": "ui-monospace,Consolas,monospace"},
            width=64, allow_decimals=True),
        rx.recharts.tooltip(content_style={"backgroundColor": C["raised"], "border": f"1px solid {C['strong']}",
            "fontSize": "12px", "borderRadius": "10px"}, item_style={"color": C["ink"]},
            label_style={"color": C["muted"]}, custom_attrs={"labelFormatter": rx.Var(_js_expr=TIME_LABEL)}),
        line("raw", "원시값", C["raw"], hidden=compare),
        line("cond", "처리값", C["ink2"], dash="2 3", hidden=compare),
        line("final_good", "최종값 · 양호", C["leaf"], width=2, fill=True),
        line("final_uncertain", "최종값 · 불확실", C["muted"], width=1.5, dash="5 4", dot=True),
        rx.recharts.reference_line(x=S.cursor_time, stroke=C["leaf"], stroke_dasharray="3 4"),
        rx.recharts.brush(data_key="epoch_ms", height=24, stroke=C["strong"], fill=C["well"],
                          tick_formatter=TIME_TICK, key=S.site_id + S.tag + S.minutes),
        data=S.series, height=360, margin={"top": 12, "right": 16, "left": 0, "bottom": 8})
    return card(
        rx.flex(rx.box(rx.text(S.tag, weight="bold", class_name="scada-wrap"),
                       rx.text("원천 최신 ", S.selected["observed_d"], size="1", class_name="scada-mono",
                               color="var(--muted)")),
                rx.spacer(), rx.text(S.selected["final_d"], class_name="scada-signal-value"),
                rx.cond(S.selected["unit_d"] != "—", rx.text(S.selected["unit_d"], size="2", color="var(--muted)")),
                quality_pill(S.selected), class_name="scada-signal-head", align="center", wrap="wrap"),
        rx.flex(*[rx.button(m + "분", on_click=S.change_window(m), size="1", color_scheme="gray",
                            variant=rx.cond(S.minutes == m, "solid", "soft")) for m in ["5", "15", "60"]],
                rx.spacer(), rx.segmented_control.root(
                    rx.segmented_control.item("최종값", value="FINAL"),
                    rx.segmented_control.item("원시·처리 비교", value="비교"),
                    value=S.phase, on_change=S.set_phase, size="1"),
                class_name="scada-toolbar", align="center", wrap="wrap"),
        rx.el.svg(rx.el.defs(rx.el.svg.linear_gradient(
            rx.el.svg.stop(offset="5%", stop_color=C["leaf"], stop_opacity=0.22),
            rx.el.svg.stop(offset="95%", stop_color=C["leaf"], stop_opacity=0.02),
            id="scada-final-fill", x1="0", y1="0", x2="0", y2="1")), width="0", height="0"),
        rx.cond(S.series.length() > 0,
            rx.fragment(
                rx.box(graph, class_name="scada-chart"),
                rx.box(legend_item("최종값 · 양호", C["leaf"]),
                       legend_item("최종값 · 불확실", C["muted"], "dash"),
                       rx.cond(S.phase == "비교", rx.fragment(legend_item("원시값", C["raw"]),
                                                              legend_item("처리값", C["ink2"], "dash"))),
                       rx.el.span("불량·결측 구간은 선을 잇지 않음"),
                       rx.cond(S.series_truncated, rx.el.span("최근 2,000개 표본만 표시")),
                       class_name="scada-legend"),
                rx.box(rx.flex(rx.text("표본 선택", size="1", color="var(--muted)"), rx.spacer(),
                               rx.text(S.inspected_sample["time"], size="1", class_name="scada-mono")),
                       rx.slider(value=[S.sample_position], min=0, max=S.sample_max, step=1,
                                 on_change=S.inspect_sample, aria_label="이력 표본 선택", margin_top="12px"),
                       class_name="scada-inspection-slider")),
            note("선택 기간에 이 태그의 이력 없음 — 기간을 넓혀 지금 조회를 누르세요")))


def overview():
    def attention(row):
        return rx.flex(pill(row["issue"], row["issue_tone"]),
            rx.box(rx.button(row["tag"], on_click=[S.select_tag(row["tag"]), rx.redirect("/trend")],
                             variant="ghost", size="1", class_name="scada-tag-button"),
                   rx.text(row["channel"], size="1", color="var(--muted)"), min_width="0"),
            rx.spacer(), rx.text(row["final_d"], class_name="scada-number"),
            rx.cond(row["unit_d"] != "—", rx.text(row["unit_d"], size="1", color="var(--muted)")),
            class_name="scada-attention-row", align="center")

    def recent_condition(row, key, numeric):
        return rx.table.cell(pill(row["condition"], row["tone"]))

    def mix_row(m):
        return rx.box(pill(m["label"], m["tone"]), rx.text(m["count_d"], class_name="n"), class_name="scada-mix-row")

    return stack(
        rx.box(kpi("관측 태그", known(S.observed_tags), "선택 현장 최신 표본"),
               kpi("확인 대상", known(S.attention_rows.length()), "품질·값 계약·갱신 지연"),
               kpi("불량 태그", known(S.bad_tags), "최종 품질 불량", "bad"),
               kpi("관측 채널", known(S.channel_rows.length()), "최신 표본의 채널"),
               class_name="scada-kpis"),
        split(card(section_title("우선 확인할 자료", "선택하면 트렌드로 이동"),
                   rx.cond(S.attention_rows.length() > 0, rx.foreach(S.attention_rows, attention),
                           note("확인 대상 없음 — 품질 불량·값 계약 오류·갱신 지연 0건"))),
              card(section_title("관측 채널", "최신 표본 기준"),
                   rx.cond(S.channel_rows.length() > 0, table(S.channel_rows, "channels"),
                           note("관측된 채널 없음")))),
        split(card(section_title("최근 경보 사건", "최대 5건"),
                   rx.cond(S.alarm_state.contains("조회 실패"),
                           note("경보 이력을 읽지 못했습니다 — 지금 조회를 누르세요"),
                           rx.cond(S.alarms.length() > 0,
                                   table(S.recent_alarms, "recent_alarms", cell={"condition": recent_condition}),
                                   note("선택 현장의 최근 경보 사건 없음"))),
                   rx.box(rx.link("경보 화면 열기", href="/alarms", size="2"), class_name="scada-note foot")),
              card(section_title("저장 표본 품질", rx.text("선택 기간 ", S.received, "건", class_name="scada-mono")),
                   rx.cond(S.good + S.uncertain + S.bad > 0,
                           rx.box(rx.box(rx.foreach(S.quality_mix, lambda m: rx.box(
                                         class_name=m["tone"], width=m["width"])), class_name="scada-mix-bar"),
                                  rx.foreach(S.quality_mix, mix_row), class_name="scada-mix"),
                           note("선택 기간 저장 표본 없음")))))


def workflow():
    def step(idx, name, value, sub, off=False):
        return rx.box(rx.text(idx, class_name="idx"), rx.text(name, class_name="name"),
                      rx.text(value, class_name="val"), rx.text(sub, class_name="sub"),
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
        return rx.table.row_header_cell(rx.button(row["message_d"], on_click=S.select_alarm(row["event"]),
                                                  variant="ghost", size="1", class_name="scada-alarm-button"))

    def condition_cell(row, key, numeric):
        return rx.table.cell(pill(row["condition"], row["tone"]))

    listing = card(section_title("최근 발생 이력", "최대 100건"),
        rx.cond(S.alarm_state.contains("조회 실패"), note("경보 이력을 읽지 못했습니다 — 지금 조회를 누르세요"),
                rx.cond(S.alarms.length() > 0,
                        table(S.alarms, "alarms", cell={"message_d": message_cell, "condition": condition_cell},
                              row_props=lambda row: {"class_name": rx.cond(
                                  row["event"] == S.selected_alarm["event"], "scada-selected", "")}),
                        note("선택 현장의 경보 사건 없음"))))
    details = card(section_title("선택 사건"),
        rx.cond(S.alarms.length() > 0,
                rx.fragment(rx.box(rx.text(S.selected_alarm["message_d"], weight="bold", class_name="scada-wrap"),
                                   class_name="scada-toolbar"),
                            facts(S.alarm_facts)),
                note("선택할 사건 없음")))
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
            path.append(rx.el.span("→", aria_hidden="true"))
    return stack(
        card(section_title("전달 경로", "상위 DB 저장분만 관측"),
             rx.box(*path, class_name="scada-path"),
             rx.box(kpi("저장 표본", known(S.received), "선택 기간"),
                    kpi("관측 태그", known(S.observed_tags), "최신 표본"),
                    kpi("조회 기준", S.as_of_d, "KST"),
                    class_name="scada-kpis", style={"gridTemplateColumns": "repeat(3,minmax(0,1fr))",
                                                    "padding": "0 16px 16px"}),
             note("단계별 지연·보충 지표 미연결 — cursor·offset 기록 연결 뒤 표시", foot=True)),
        split(point_table(), latest_detail()))


def scada_view(kind):
    return {"overview": overview, "process": workflow, "trend": trend,
            "alarms": alarms, "flow": flow, "communication": communication}[kind]()
