"""Core SCADA views share identity, time and nullable values."""
import reflex as rx
from ..states.scada_state import ScadaState as S


def table(rows, fields):
    return rx.box(
        rx.table.root(
            rx.table.header(rx.table.row(*[rx.table.column_header_cell(label) for _, label in fields])),
            rx.table.body(rx.foreach(rows, lambda row: rx.table.row(
                *[rx.table.cell(rx.text(row[key], white_space="nowrap")) for key, _ in fields]
            ))), width="100%",
        ), overflow_x="auto", width="100%", border="1px solid var(--ks-line)", border_radius="8px",
    )


def tile(label, value, detail):
    return rx.vstack(rx.text(label, color="var(--ks-haze)"),
                     rx.text(value, size="7", weight="bold"), rx.text(detail, size="1"),
                     padding="4", border="1px solid var(--ks-line)", border_radius="8px",
                     background="var(--ks-panel)", align="start", width="100%")


def sample_table():
    return table(S.rows, [("tag", "태그"), ("channel", "채널"), ("raw", "RAW"),
                         ("cond", "COND"), ("final", "FINAL"), ("unit", "단위"),
                         ("quality", "품질"), ("validity", "값 계약"), ("freshness", "현재성"),
                         ("observed_at", "원천 시각"), ("ingested_at", "상위 적재 시각")])


def scada_view(kind):
    titles = {"overview": "운전 개요", "process": "공정 감시", "trend": "트렌드",
              "alarms": "경보", "flow": "데이터 흐름", "communication": "통신 이력"}
    contents = []
    if kind in {"overview", "process"}:
        contents.extend([
            rx.grid(tile("관측 태그", rx.cond(S.as_of == "—", "—", S.observed_tags.to_string()), "기대 태그 수 아님 · 태그 정의 미수신"),
                    tile("현재 BAD", rx.cond(S.as_of == "—", "—", S.bad_tags.to_string()), "최신 표본의 품질"),
                    tile("오래된 표본", S.stale_label, "현재성 기준 미설정 시 —"),
                    columns=rx.breakpoints(initial="1", md="3"), width="100%", spacing="3"),
            rx.text("공정 연결 모델 미수신 · 실제 펌프/밸브 연결이나 운전 정상을 추정하지 않습니다.")
            if kind == "process" else rx.text("품질 GOOD은 공정 경보 없음이나 PLC 통신 정상을 뜻하지 않습니다."),
            sample_table(),
        ])
    elif kind == "trend":
        contents.extend([
            rx.text("RAW / COND / FINAL · NULL은 공백 · 최대 최근 2,000표본"),
            rx.cond(S.series_truncated, rx.callout("표본 상한으로 일부 이력이 잘렸습니다.", icon="info")),
            rx.recharts.line_chart(
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.x_axis(data_key="time", hide=True), rx.recharts.y_axis(),
                rx.recharts.tooltip(), rx.recharts.legend(),
                rx.recharts.line(data_key="raw", type_="linear", stroke="var(--ks-haze)",
                                 dot=False, connect_nulls=False, is_animation_active=False),
                rx.recharts.line(data_key="cond", type_="linear", stroke="var(--ks-aqua)",
                                 dot=False, connect_nulls=False, is_animation_active=False),
                rx.recharts.line(data_key="final", type_="linear", stroke="var(--ks-text)",
                                 dot=False, connect_nulls=False, is_animation_active=False),
                data=S.series, width="100%", height=360,
            ),
            rx.text("태그 종류·보간 사유의 완전한 표시는 정의 동기화 뒤 검증할 항목입니다."),
        ])
    elif kind == "alarms":
        contents.extend([
            rx.text(S.alarm_state),
            rx.text("원천의 발생/복귀와 확인 상태 · 인증된 확인 명령 계약 전까지 읽기 전용"),
            table(S.alarms, [("event", "사건"), ("time", "발생 시각"), ("message", "내용"),
                             ("level", "원천 우선순위"), ("condition", "발생/복귀"),
                             ("acknowledgement", "확인")]),
        ])
    elif kind == "flow":
        contents.extend([
            rx.text("PLC → 수집 → 전달 → Kafka → Consumer → 상위 DB"),
            rx.text("VQT 표본의 적재만 관측합니다. 각 구간의 연결/지연은 별도 근거가 필요합니다."),
            rx.heading("원천 Health", size="4"), rx.text(S.health_state),
            table(S.health_rows, [("channel", "채널"), ("state", "원천 상태"),
                                  ("time", "Health 원천 시각"), ("freshness", "현재성")]),
            sample_table(),
        ])
    else:
        contents.extend([
            rx.callout("수집 계획/시작·정지 이력 미수신 · 통신 성공률과 완전성은 —", icon="info"),
            rx.grid(tile("기간 내 저장 표본", S.received, "고유 저장 행 · 시도 횟수 아님"),
                    tile("GOOD", S.good, "기간 내 품질2"),
                    tile("UNCERTAIN", S.uncertain, "기간 내 품질1"),
                    tile("BAD", S.bad, "기간 내 품질0"),
                    columns=rx.breakpoints(initial="1", md="4"), width="100%", spacing="3"),
        ])
    return rx.vstack(
        rx.heading(titles[kind], size="6"),
        rx.text(S.source_label, size="2", color="var(--ks-haze)"),
        rx.flex(rx.input(value=S.site_id, on_blur=S.change_site, placeholder="현장 ID"),
                rx.select(S.tags, value=S.tag, on_change=S.change_tag, placeholder="태그"),
                rx.select(["5", "15", "60"], value=S.minutes, on_change=S.change_minutes),
                rx.text("분"), rx.button("지금 조회", on_click=S.refresh_now),
                rx.button(rx.cond(S.live, "5초 갱신 중 · 누르면 시점 고정", "시점 고정 · 누르면 갱신"),
                          on_click=S.toggle_live, variant="soft"),
                wrap="wrap", gap="3", align="center", width="100%"),
        rx.text(S.query_state, weight="bold"),
        rx.text("조회 기준: ", S.as_of, " / 응답: ", S.served_at, size="1"),
        rx.text("공통 기준시각은 장치별 동시 측정을 보장하지 않습니다.", size="1"),
        rx.cond(S.error_message != "", rx.callout(S.error_message, icon="triangle-alert")),
        *contents, spacing="4", width="100%", padding="4",
    )
