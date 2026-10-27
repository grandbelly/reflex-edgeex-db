"""Operational views using the dashboard template's native card composition."""
import reflex as rx
from ..states.scada_state import ScadaState as S
from ..components.scada import card, metric, section_title, quality_badge


def empty_state(title, detail, icon="inbox"):
    return rx.center(rx.vstack(rx.icon(icon, size=28, color=rx.color("gray", 9)),
                               rx.text(title, weight="medium"),
                               rx.text(detail, size="2", color=rx.color("gray", 11), text_align="center"),
                               spacing="3", align="center"), padding="36px 20px", width="100%")


def fields(rows, columns):
    return rx.box(rx.table.root(
        rx.table.header(rx.table.row(*[rx.table.column_header_cell(label) for _, label in columns])),
        rx.table.body(rx.foreach(rows, lambda row: rx.table.row(
            *[rx.table.cell(rx.text(row[key], size="2")) for key, _ in columns]))),
        size="2", variant="surface", width="100%",
    ), overflow_x="auto", width="100%")


def point_table():
    def row(r):
        return rx.table.row(
            rx.table.row_header_cell(rx.button(r["tag"], on_click=S.select_tag(r["tag"]), variant="ghost", size="2"),
                                     rx.text(r["channel"], size="1", color=rx.color("gray", 10))),
            rx.table.cell(rx.text(r["final"], size="3", weight="medium", class_name="scada-mono"),
                          rx.text(r["unit"], size="1", color=rx.color("gray", 10))),
            rx.table.cell(quality_badge(r["quality"])),
            rx.table.cell(rx.text(r["freshness"], size="1")),
            class_name="scada-point-row",
            background=rx.cond(r["tag"] == S.tag, rx.color("teal", 3), "transparent"),
        )
    return card(
        rx.flex(section_title("태그 현재값", "태그를 선택하면 값의 처리 단계와 시각을 확인할 수 있습니다."),
                rx.spacer(), rx.input(placeholder="태그·채널 검색", value=S.search, on_change=S.change_search,
                                      aria_label="태그·채널 검색", width="220px"),
                align="start", spacing="3", wrap="wrap"),
        rx.cond(S.filtered_rows.length() > 0,
                rx.box(rx.table.root(
                    rx.table.header(rx.table.row(*[rx.table.column_header_cell(t) for t in
                                                   ["태그 / 채널", "최종값 / 단위", "품질", "현재성"]])),
                    rx.table.body(rx.foreach(S.visible_rows, row)),
                    size="2", width="100%",
                ), overflow_x="auto"),
                empty_state("표시할 태그가 없습니다", "현장 ID, 검색어와 조회 상태를 확인하세요.")),
        rx.flex(rx.text("검색 ", S.filtered_rows.length(), " / 관측 ", S.observed_tags, "점", size="1", color=rx.color("gray", 11)),
                rx.spacer(),
                rx.icon_button("chevron-left", on_click=S.previous_page, disabled=S.page <= 0,
                               variant="ghost", size="1", aria_label="이전 페이지"),
                rx.text(S.page + 1, " / ", S.page_count, size="1"),
                rx.icon_button("chevron-right", on_click=S.next_page, disabled=S.page >= S.page_count - 1,
                               variant="ghost", size="1", aria_label="다음 페이지"),
                align="center", spacing="2", margin_top="14px"),
    )


def detail():
    def value(label, field):
        return rx.flex(rx.text(label, size="2", color=rx.color("gray", 11)), rx.spacer(),
                       rx.text(S.selected[field], size="2", weight="medium", class_name="scada-mono"),
                       spacing="3", align="center", width="100%")
    return card(
        section_title("선택 태그", "한 표본의 처리 단계"),
        rx.text(S.selected["tag"], size="3", weight="bold", class_name="scada-detail"),
        rx.hstack(quality_badge(S.selected["quality"]), rx.text(S.selected["unit"], size="2"), margin_y="12px"),
        rx.vstack(value("RAW · 원시값", "raw"), value("COND · 보정값", "cond"), value("FINAL · 최종값", "final"),
                  spacing="3", width="100%"),
        rx.separator(margin_y="18px"),
        rx.vstack(
            rx.text(S.selected["freshness"], size="2", weight="medium"),
            rx.text("원천 시각", size="1", color=rx.color("gray", 10)),
            rx.text(S.selected["observed_at"], size="1", class_name="scada-mono"),
            rx.text("상위 적재 시각", size="1", color=rx.color("gray", 10), margin_top="8px"),
            rx.text(S.selected["ingested_at"], size="1", class_name="scada-mono"),
            rx.text(S.selected["validity"], size="1", margin_top="8px"),
            spacing="2", align="start", class_name="scada-detail",
        ),
        rx.accordion.root(rx.accordion.item(
            header="판정 근거", content=rx.text(S.selected["reasons"], size="1", class_name="scada-detail")),
            collapsible=True, margin_top="16px"),
    )


def metrics():
    def measured(value):
        return rx.cond(S.as_of == "—", "—", value.to_string())
    return rx.grid(
        metric("관측 태그", measured(S.observed_tags), "등록 태그 전체 수와 다릅니다", "tags"),
        metric("현재 BAD", measured(S.bad_tags), "태그별 최신 표본의 품질", "shield-alert", "red"),
        metric("오래된 표본", S.stale_label, "원천 시각 기준 · 기준 없으면 —", "clock-3", "amber"),
        metric("기간 내 저장 표본", measured(S.received), "선택한 조회 기간의 실제 저장 건수", "database", "blue"),
        columns=rx.breakpoints({"0px": "1", "640px": "2", "1100px": "4"}), spacing="4", width="100%",
    )


def overview(process=False):
    return rx.vstack(
        metrics(),
        rx.callout("공정 모델이 전달되지 않았습니다. 설비 연결 상태는 현장 태그와 별도로 확인해야 합니다.",
                   icon="workflow", color_scheme="gray") if process else
        rx.callout("품질 GOOD만으로 PLC 통신과 공정 운전이 정상이라고 판단할 수 없습니다.",
                   icon="info", color_scheme="gray"),
        rx.grid(point_table(), detail(), grid_template_columns=rx.breakpoints({"0px": "1fr", "1200px": "minmax(0, 1fr) 300px"}),
                spacing="4", width="100%", align="start"), spacing="4", align="stretch",
    )


def trend():
    return rx.vstack(
        rx.grid(
            card(section_title("값의 변화", "NULL·BAD 최종값은 선으로 연결하지 않습니다."),
                 rx.text(S.tag, size="2", weight="medium", margin_bottom="16px"),
                 rx.cond(S.series.length() > 0,
                         rx.recharts.line_chart(
                             rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke=rx.color("gray", 5)),
                             rx.recharts.x_axis(data_key="time", hide=True),
                             rx.recharts.y_axis(width=60), rx.recharts.tooltip(), rx.recharts.legend(),
                             *[rx.recharts.line(data_key=key, name=name, type_="linear", stroke=color,
                                                 dot=False, connect_nulls=False, is_animation_active=False)
                               for key, name, color in [("raw", "RAW", "#8394aa"), ("cond", "COND", "#e6b35c"),
                                                        ("final", "FINAL", "#2dd4bf")]],
                             data=S.series, width="100%", height=380,
                         ), empty_state("이력 표본이 없습니다", "조회 범위와 태그를 확인한 뒤 지금 조회를 누르세요.", "chart-no-axes-combined")),
                 rx.cond(S.series_truncated, rx.callout("최근 2,000개 표본을 표시합니다. 앞선 이력은 생략됐습니다.",
                                                                      color_scheme="amber", icon="info"))),
            detail(), grid_template_columns=rx.breakpoints({"0px": "1fr", "1200px": "minmax(0, 1fr) 300px"}),
            spacing="4", width="100%", align="start"),
        card(section_title("시각과 품질", "원천 시각 기준의 이력입니다. 상위에 늦게 적재된 과거 표본도 포함될 수 있습니다."),
             rx.text("결측은 0으로 바꾸지 않습니다. 태그 종류와 장기 집계 정책은 정의 동기화 단계에서 연결합니다.",
                     size="2", color=rx.color("gray", 11))), spacing="4", align="stretch",
    )


def alarms():
    return card(
        section_title("현장 경보 사건", "최근 100건 · 전체 활성 경보 수와 다릅니다."),
        rx.callout("확인 상태는 원천에서 읽습니다. 이 화면은 경보 확인 명령을 전송하지 않습니다.",
                   icon="eye", color_scheme="gray", margin_bottom="16px"),
        rx.cond(S.alarm_state.contains("조회 실패"),
                empty_state("경보 이력을 읽지 못했습니다", "조회 실패는 경보가 없다는 뜻이 아닙니다.", "triangle-alert"),
                rx.cond(S.alarms.length() > 0,
                        fields(S.alarms, [("time", "발생 시각"), ("message", "내용"), ("level", "원천 우선순위"),
                                          ("condition", "발생 / 복귀"), ("acknowledgement", "확인")]),
                        empty_state("표시할 최근 사건이 없습니다", "현장 선택과 조회 상태를 확인하세요.", "bell"))),
        rx.text(S.alarm_state, size="1", color=rx.color("gray", 10), margin_top="16px"),
    )


def flow():
    def step(name, icon, detail_text, observed=False):
        return card(rx.vstack(rx.hstack(rx.icon(icon, size=20), rx.spacer(),
                                         rx.badge("저장 관측" if observed else "상태 미확인",
                                                  color_scheme="teal" if observed else "gray"), width="100%"),
                               rx.text(name, weight="medium"), rx.text(detail_text, size="1", color=rx.color("gray", 11)),
                               spacing="3", align="start"))
    return rx.vstack(
        rx.grid(step("PLC / 현장", "cpu", "원천 Health 근거 필요"),
                step("수집 / 전달", "radio-tower", "시도·응답 이력 근거 필요"),
                step("Kafka", "network", "브로커·토픽 지표 근거 필요"),
                step("상위 저장소", "database", "선택 현장의 VQT를 조회합니다"),
                columns=rx.breakpoints({"0px": "1", "640px": "2", "1100px": "4"}), spacing="4"),
        card(section_title("상위 도착 표본", "표본의 도착만으로 앞선 구간의 현재 연결 상태를 추정하지 않습니다."),
             rx.flex(rx.text("선택 기간 저장 표본", size="2"), rx.spacer(),
                     rx.heading(S.received, size="6"), align="center")),
        card(section_title("원천 Health", "채널별 상태와 원천 시각"),
             rx.cond(S.health_state.contains("조회 실패"),
                     rx.callout("Health 수신 상태를 확인할 수 없습니다. VQT 조회는 계속 제공됩니다.",
                                icon="triangle-alert", color_scheme="amber"),
                     rx.cond(S.health_rows.length() > 0,
                             fields(S.health_rows, [("channel", "채널"), ("state", "원천 상태"),
                                                    ("time", "Health 원천 시각"), ("freshness", "현재성")]),
                             empty_state("Health 표본이 없습니다", "원천 상태가 정상인 것으로 해석하지 않습니다."))),
             rx.accordion.root(rx.accordion.item(header="조회 진단", content=rx.text(S.health_state, size="2")),
                               collapsible=True, margin_top="16px")), spacing="4", align="stretch",
    )


def communication():
    return rx.vstack(
        rx.grid(*[metric(name, rx.cond(S.as_of == "—", "—", value.to_string()), note, icon, color)
                  for name, value, note, icon, color in [
                      ("저장 표본", S.received, "선택 기간 · 실제 저장 건수", "database", "blue"),
                      ("GOOD", S.good, "원천 품질 2", "shield-check", "teal"),
                      ("UNCERTAIN", S.uncertain, "원천 품질 1", "shield-question", "amber"),
                      ("BAD", S.bad, "원천 품질 0 · NULL 보존", "shield-alert", "red")]],
                columns=rx.breakpoints({"0px": "1", "640px": "2", "1100px": "4"}), spacing="4"),
        card(section_title("통신 완전성", "저장 표본과 통신 시도는 서로 다른 지표입니다."),
             rx.callout("수집 계획과 시도·응답 이력이 아직 연결되지 않았습니다. 통신 성공률과 무손실 여부는 판정할 수 없습니다.",
                        icon="info", color_scheme="gray")),
        point_table(), spacing="4", align="stretch",
    )


def scada_view(kind):
    return {"overview": overview, "process": lambda: overview(True), "trend": trend,
            "alarms": alarms, "flow": flow, "communication": communication}[kind]()
