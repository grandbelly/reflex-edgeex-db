"""Purpose-specific operator views, adapted from the pinned stock templates."""
import reflex as rx
from ..states.scada_state import ScadaState as S
from ..components.scada import card, metric, section_title, quality_badge, empty_state

TIME_TICK = "(value) => new Date(value).toLocaleTimeString('ko-KR', {timeZone:'Asia/Seoul', hour12:false})"
TIME_LABEL = "(value) => new Date(value).toLocaleString('ko-KR', {timeZone:'Asia/Seoul', hour12:false})"


def split(main, aside, wide=False):
    return rx.grid(main, aside, class_name="scada-split wide" if wide else "scada-split")


def line_item(label, value):
    return rx.flex(rx.text(label, size="1", color="var(--scada-muted)"), rx.spacer(),
                   rx.text(value, size="2", class_name="scada-mono scada-wrap"),
                   align="start", gap="14px", width="100%")


def table(rows, columns):
    return rx.box(rx.table.root(
        rx.table.header(rx.table.row(*[rx.table.column_header_cell(label) for _, label in columns])),
        rx.table.body(rx.foreach(rows, lambda row: rx.table.row(
            *[rx.table.cell(rx.text(row[key], size="2")) for key, _ in columns]))),
        width="100%", size="2"), class_name="scada-table-scroll")


def point_table():
    def point(row):
        return rx.table.row(
            rx.table.row_header_cell(rx.button(row["tag"], on_click=S.select_tag(row["tag"]),
                                                variant="ghost", size="2", class_name="scada-tag-button"),
                                     rx.text(row["channel"], size="1", color="var(--scada-muted)")),
            *[rx.table.cell(row[key], class_name="scada-number") for key in ["raw", "cond", "final"]],
            rx.table.cell(row["unit"]), rx.table.cell(quality_badge(row["quality"])),
            rx.table.cell(row["observed_at"], class_name="scada-time"),
            background=rx.cond(row["tag"] == S.tag, "var(--scada-selected)", "transparent"))
    return card(section_title("점별 수신 근거", "선택 현장의 최신 표본"),
        rx.flex(rx.input(placeholder="태그·채널 검색", value=S.search, on_change=S.change_search,
                         aria_label="태그·채널 검색", max_width="270px"), rx.spacer(),
                rx.text("관측 ", S.observed_tags, "점", size="1", color="var(--scada-muted)"),
                class_name="scada-toolbar", align="center"),
        rx.cond(S.visible_rows.length() > 0,
            rx.box(rx.table.root(rx.table.header(rx.table.row(*[rx.table.column_header_cell(t) for t in
                          ["태그 / 채널", "원시값", "처리값", "최종값", "단위", "품질", "원천 시각"]])),
                       rx.table.body(rx.foreach(S.visible_rows, point)), width="100%", size="2"),
                   class_name="scada-table-scroll"),
            empty_state("표시할 표본이 없습니다", "현장·검색어·조회 상태를 확인하세요.")),
        rx.flex(rx.text("검색 ", S.filtered_rows.length(), "점", size="1", color="var(--scada-muted)"),
            rx.spacer(), rx.icon_button("chevron-left", on_click=S.previous_page, disabled=S.page <= 0,
                                       variant="ghost", size="1", aria_label="이전 페이지"),
            rx.text(S.page + 1, " / ", S.page_count, size="1"),
            rx.icon_button("chevron-right", on_click=S.next_page, disabled=S.page >= S.page_count - 1,
                           variant="ghost", size="1", aria_label="다음 페이지"), class_name="scada-toolbar", align="center"))


def latest_detail():
    return card(section_title("선택 태그", "최신 표본"),
        rx.vstack(rx.text(S.selected["tag"], weight="medium", class_name="scada-wrap"),
            quality_badge(S.selected["quality"]),
            *[line_item(label, S.selected[key]) for label, key in
              [("원시값", "raw"), ("처리값", "cond"), ("최종값", "final"), ("단위", "unit"),
               ("원천 시각", "observed_at"), ("적재 시각", "ingested_at"), ("현재성", "freshness")]],
            rx.separator(), rx.text(S.selected["reasons"], size="1", class_name="scada-wrap", color="var(--scada-muted)"),
            rx.link("이 태그의 트렌드 열기 ↗", href="/trend", size="2"), class_name="scada-detail-body", spacing="3"))


def sample_detail():
    return card(section_title("표본 근거", "선택한 원천 시각"),
        rx.vstack(quality_badge(S.inspected_sample["quality"]),
            *[line_item(label, S.inspected_sample[key]) for label, key in
              [("원천 시각", "time"), ("적재 시각", "ingested_at"), ("원시값", "raw_display"),
               ("처리값", "cond_display"), ("최종값", "final_display")]],
            rx.separator(), rx.text("처리 사유", size="1", color="var(--scada-muted)"),
            rx.text(S.inspected_sample["reasons"], size="1", class_name="scada-wrap"),
            rx.text("표본 시각키", size="1", color="var(--scada-muted)"),
            rx.text(S.inspected_sample["sample_key"], size="1", class_name="scada-wrap scada-mono"),
            spacing="3", class_name="scada-detail-body"),
        rx.box(rx.text("아래 슬라이더는 받은 표본 안에서 선택합니다. 원시 정밀도를 유지하며 새 조회를 하지 않습니다.",
                       size="1", color="var(--scada-muted)"), class_name="scada-panel-note"))


def signal_chart():
    def area(key, name, color, fill=0):
        return rx.recharts.area(data_key=key, name=name, type_="linear", stroke=color,
            stroke_width=1.8, fill="url(#scada-final-fill)" if fill else color,
            custom_attrs={"fillOpacity": 1 if fill else 0},
            dot=False, connect_nulls=False, is_animation_active=False)
    graph = rx.recharts.area_chart(
        rx.recharts.cartesian_grid(vertical=False, stroke="#2b3748", stroke_dasharray="3 5"),
        rx.recharts.x_axis(data_key="epoch_ms", type_="number", scale="time", domain=["dataMin", "dataMax"],
            tick_formatter=TIME_TICK, axis_line=False, tick_line=False, min_tick_gap=65,
            tick={"fill":"#a6b4c5", "fontSize":12}, height=30),
        rx.recharts.y_axis(domain=["auto", "auto"], axis_line=False, tick_line=False,
            tick={"fill":"#a6b4c5", "fontSize":12}, width=64, allow_decimals=True),
        rx.recharts.tooltip(content_style={"backgroundColor":"#182332", "border":"1px solid #435165",
            "fontSize":"12px", "borderRadius":"6px"}, item_style={"color":"#e6edf6"},
            label_style={"color":"#a6b4c5"},
            custom_attrs={"labelFormatter": rx.Var(_js_expr=TIME_LABEL)}),
        rx.recharts.area(data_key="raw", name="원시값", type_="linear", stroke="#8e9fb4",
            custom_attrs={"fillOpacity": 0, "hide": S.phase != "비교"},
            stroke_width=1, dot=False, connect_nulls=False, is_animation_active=False),
        rx.recharts.area(data_key="cond", name="처리값", type_="linear", stroke="#b5a0e5",
            custom_attrs={"fillOpacity": 0, "hide": S.phase != "비교"},
            stroke_width=1, dot=False, connect_nulls=False, is_animation_active=False),
        area("final_good", "최종값 · 양호", "#74cfb0", 1),
        rx.recharts.area(data_key="final_uncertain", name="최종값 · 불확실", type_="linear",
            stroke="#a6b4c5", custom_attrs={"fillOpacity": 0, "strokeDasharray": "5 4"}, dot={"r":2},
            connect_nulls=False, is_animation_active=False),
        rx.recharts.reference_line(x=S.cursor_time, stroke="#78a7ff", stroke_dasharray="3 4"),
        rx.recharts.brush(data_key="epoch_ms", height=24, stroke="#536c94", fill="#142033",
                          key=S.site_id + S.tag + S.minutes),
        data=S.series, height=370, margin={"top":12,"right":16,"left":0,"bottom":8})
    return card(
        rx.flex(rx.box(rx.text(S.tag, weight="medium", class_name="scada-wrap"),
                       rx.text("원천 최신 ", S.selected["observed_at"], size="1", color="var(--scada-muted)")),
                rx.spacer(), rx.text(S.selected["final"], class_name="scada-signal-value"),
                rx.text(S.selected["unit"], size="2", color="var(--scada-muted)"),
                quality_badge(S.selected["quality"]), class_name="scada-signal-head", align="center", wrap="wrap"),
        rx.flex(*[rx.button(m + "분", on_click=S.change_window(m), size="1", color_scheme="gray",
                       variant=rx.cond(S.minutes == m, "solid", "soft")) for m in ["5", "15", "60"]],
                rx.spacer(), rx.segmented_control.root(
                    rx.segmented_control.item("최종값", value="FINAL"),
                    rx.segmented_control.item("원시·처리 비교", value="비교"),
                    value=S.phase, on_change=S.set_phase, size="1"),
                class_name="scada-toolbar", align="center", wrap="wrap"),
        rx.el.svg(rx.el.defs(rx.el.svg.linear_gradient(
            rx.el.svg.stop(offset="5%", stop_color="#74cfb0", stop_opacity=0.25),
            rx.el.svg.stop(offset="95%", stop_color="#74cfb0", stop_opacity=0.02),
            id="scada-final-fill", x1="0", y1="0", x2="0", y2="1")), width="0", height="0"),
        rx.cond(S.series.length() > 0, rx.box(graph, class_name="scada-chart"),
                empty_state("표시할 이력이 없습니다", "태그와 기간을 선택하고 지금 조회를 누르세요.", "chart-line")),
        rx.cond(S.series.length() > 0,
            rx.box(rx.flex(rx.text("표본 선택", size="1"), rx.spacer(),
                            rx.text(S.inspected_sample["time"], size="1", class_name="scada-mono")),
                   rx.slider(value=[S.sample_position], min=0, max=S.sample_max, step=1,
                             on_change=S.inspect_sample, aria_label="이력 표본 선택", margin_top="12px"),
                   class_name="scada-inspection-slider")),
        rx.box(rx.text("KST · 선형 표시 · 결측 구간 연결 안 함 · 원천 시각 간격 유지", size="1"),
               rx.cond(S.series_truncated, rx.text("최근 2,000개 표본 표시 · 앞선 이력 생략", size="1", color="#d9b574")),
               class_name="scada-panel-note"))


def overview():
    def attention(row):
        return rx.flex(rx.badge(row["issue"], color_scheme="gray", variant="outline"),
            rx.box(rx.button(row["tag"], on_click=[S.select_tag(row["tag"]), rx.redirect("/trend")],
                             variant="ghost", size="2"),
                   rx.text(row["channel"], size="1", color="var(--scada-muted)")),
            rx.spacer(), quality_badge(row["quality"]), class_name="scada-attention-row", align="center")
    return rx.vstack(
        rx.grid(metric("관측 태그", rx.cond(S.as_of == "—", "—", S.observed_tags.to_string()), "등록 전체 수와 구별"),
                metric("자료 확인", rx.cond(S.as_of == "—", "—", S.attention_rows.length().to_string()), "품질·값 계약·갱신 지연"),
                metric("갱신 지연", S.stale_label, "원천 시각 · 기준이 없으면 미판정"),
                metric("관측 채널", rx.cond(S.as_of == "—", "—", S.channel_rows.length().to_string()), "연결 성공 판정과 구별"),
                class_name="scada-stat-strip"),
        split(card(section_title("우선 확인할 자료", "선택하면 해당 태그의 트렌드로 이동"),
                   rx.cond(S.attention_rows.length() > 0, rx.foreach(S.attention_rows, attention),
                       empty_state("조회된 표본에 확인 대상이 없습니다", "설비·공정 경보의 정상 판정과는 구별합니다.", "list-checks"))),
              card(section_title("관측 채널", "현재값의 소속"),
                   table(S.channel_rows, [("channel","채널"),("count","관측 점"),("bad","불량")]),
                   rx.box(rx.text("설비군 연결은 현장 정의가 제공되면 표시합니다.", size="1"), class_name="scada-panel-note"))),
        split(card(section_title("최근 경보 이력", "제한된 원천 사건"),
                   rx.cond(S.alarm_state.contains("조회 실패"),
                           empty_state("경보 이력을 읽지 못했습니다", "자료 조회 상태를 확인하세요.", "bell"),
                           rx.cond(S.alarms.length() > 0, table(S.alarms[:5], [("time","발생"),("message","내용"),("condition","상태")]),
                                   empty_state("수신된 최근 사건이 없습니다", "전체 활성 경보 수를 뜻하지 않습니다.", "bell"))),
                   rx.box(rx.link("경보 이력 열기 ↗", href="/alarms", size="2"), class_name="scada-panel-note")),
              card(section_title("판단 범위", "실제 관측과 구별"),
                   rx.box(rx.text("품질과 갱신 지연은 수신 표본을 기준으로 확인합니다. 설비 운전 상태와 활성 경보 전체는 아직 연결되지 않았습니다.",
                                  size="2", color="var(--scada-muted)"), class_name="scada-detail-body"))), spacing="4", align="stretch")


def workflow():
    return rx.vstack(
        split(card(section_title("업무·제어 흐름", "개념 단계 · 실행 상태 아님"),
                   rx.flex(*[rx.box(rx.icon(icon, size=20, color="var(--scada-muted)"),
                                    rx.text(name, weight="medium"), class_name="scada-workflow-step")
                             for name, icon in [("측정","gauge"),("판단","git-branch"),("시뮬레이션·승인","clipboard-check"),("조치·피드백","repeat")]],
                           class_name="scada-workflow-graph"),
                   rx.box(rx.text("이 현장의 업무 흐름이 등록되지 않았습니다. 단계별 실행 상태는 표시하지 않습니다.", size="2"),
                          class_name="scada-panel-note")),
              card(section_title("선택 실행", "실행 기록"),
                   empty_state("연결된 실행이 없습니다", "업무 모델과 실행 기록이 연결되면 입력·판단·조치 결과를 확인할 수 있습니다.", "workflow"))),
        card(section_title("실행 이력", "실행 ID · 시작/종료 · 상태 · 정체 단계"),
             empty_state("아직 표시할 실행 이력이 없습니다", "현재 도착한 신호는 Edge 관제에서 확인할 수 있습니다."),
             rx.box(rx.link("수신 자료 확인 ↗", href="/edge-monitor", size="2"), class_name="scada-panel-note")),
        spacing="4", align="stretch")


def trend():
    return split(signal_chart(), sample_detail(), wide=True)


def alarms():
    def event(row):
        return rx.table.row(
            rx.table.row_header_cell(rx.button(row["message"], on_click=S.select_alarm(row["event"]),
                                                variant="ghost", size="2", class_name="scada-alarm-button")),
            rx.table.cell(row["level"]), rx.table.cell(row["time"], class_name="scada-time"),
            rx.table.cell(row["condition"]), rx.table.cell(row["acknowledgement"]),
            background=rx.cond(row["event"] == S.selected_alarm["event"], "var(--scada-selected)", "transparent"))
    listing = card(section_title("최근 발생 이력", "최대 100건 · 전체 활성 건수와 구별"),
        rx.cond(S.alarm_state.contains("조회 실패"), empty_state("경보 이력을 읽지 못했습니다", "잠시 뒤 지금 조회를 눌러 주세요.", "bell"),
                rx.cond(S.alarms.length() > 0,
                    rx.box(rx.table.root(rx.table.header(rx.table.row(*[rx.table.column_header_cell(t) for t in
                            ["사건", "원천 우선순위", "발생 시각", "발생/복귀", "확인"]])),
                            rx.table.body(rx.foreach(S.alarms, event)), width="100%", size="2"), class_name="scada-table-scroll"),
                    empty_state("표시할 최근 사건이 없습니다", "선택 현장의 수신된 이력입니다.", "bell"))),
        rx.box(rx.text("새 사건을 받아도 선택 사건을 유지합니다. 이 화면은 조회 전용입니다.", size="1"), class_name="scada-panel-note"))
    details = card(section_title("선택 사건", "발생·복귀·확인"),
        rx.vstack(*[line_item(label, S.selected_alarm[key]) for label,key in
                    [("사건 ID","event"),("발생 시각","time"),("원천 우선순위","level"),
                     ("현재 원천 상태","condition"),("확인 상태","acknowledgement")]],
                  rx.separator(), rx.text(S.selected_alarm["message"], size="2", class_name="scada-wrap"),
                  rx.text("복귀·확인 시각과 주체는 수신된 사건에 없습니다.", size="1", color="var(--scada-muted)"),
                  spacing="3", class_name="scada-detail-body"))
    return split(listing, details)


def communication():
    return rx.vstack(
        split(card(section_title("채널 × 시간", "연결 이력"),
                   empty_state("채널의 연결 이력이 연결되지 않았습니다", "시도·응답 기록이 있어야 끊김과 복구 구간을 확인할 수 있습니다.", "radio-tower"),
                   rx.box(rx.text("저장된 값의 품질을 통신 성공률로 바꾸지 않습니다.", size="1"), class_name="scada-panel-note")),
              card(section_title("선택 구간", "마지막 정상 · 첫 오류 · 복구"),
                   empty_state("아직 선택할 구간이 없습니다", "미관측은 정상 또는 실패와 구별합니다.", "clock-3"))),
        card(section_title("수신된 채널 Health", "원천 상태"),
             rx.cond(S.health_state.contains("조회 실패"),
                 empty_state("채널 Health를 확인할 수 없습니다", "상위 VQT 자료는 계속 조회할 수 있습니다.", "circle-help"),
                 rx.cond(S.health_rows.length() > 0,
                     table(S.health_rows, [("channel","채널"),("state","원천 상태"),("time","원천 시각"),("freshness","현재성")]),
                     empty_state("수신된 Health가 없습니다", "현재 연결 상태를 추정하지 않습니다.", "radio-tower")))),
        spacing="4", align="stretch")


def flow():
    return rx.vstack(
        rx.grid(*[rx.box(rx.text(f"0{i+1}", size="1", color="var(--scada-muted)"),
                         rx.text(name, weight="medium"),
                         rx.text("저장 표본 조회" if name == "상위 DB" else "관측 지표 미연결", size="1", color="var(--scada-muted)"),
                         class_name="scada-delivery-step")
                   for i,name in enumerate(["Edge", "전달기", "Kafka", "Consumer", "상위 DB"])],
                class_name="scada-delivery-strip"),
        split(card(section_title("전달 지연 · 보충 범위", "같은 표본 집합을 기준으로 대조"),
                   empty_state("전달 단계의 지표가 연결되지 않았습니다", "cursor·offset·확정 시각이 있어야 지연과 보충을 확인할 수 있습니다.", "route"),
                   rx.box(rx.text("상위 저장 건수 증가는 전체 구간의 무손실 근거가 아닙니다.", size="1"), class_name="scada-panel-note")),
              card(section_title("수신 관측", "선택 기간"),
                   rx.vstack(line_item("저장 표본", rx.cond(S.as_of == "—", "—", S.received.to_string())),
                             line_item("관측 태그", rx.cond(S.as_of == "—", "—", S.observed_tags.to_string())),
                             line_item("조회 기준", S.as_of), spacing="3", class_name="scada-detail-body"))),
        split(point_table(), latest_detail()), spacing="4", align="stretch")


def scada_view(kind):
    return {"overview":overview, "process":workflow, "trend":trend,
            "alarms":alarms, "flow":flow, "communication":communication}[kind]()
