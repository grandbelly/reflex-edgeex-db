"""Six thin routes using the official dashboard template adaptation."""
import reflex as rx
from ..components.scada import template
from ..states.scada_state import ScadaState as S
from ..views.scada_view import scada_view


@rx.page(route="/", title="운전 개요 · edgeEX", on_load=S.initialize)
@template("/", "운전 개요", "현장 데이터의 품질과 현재성을 확인합니다.")
def overview():
    return scada_view("overview")


@rx.page(route="/workflow", title="공정 감시 · edgeEX", on_load=S.initialize)
@template("/workflow", "공정 감시", "관측 태그와 채널을 공정 정보와 함께 확인합니다.")
def process():
    return scada_view("process")


@rx.page(route="/trend", title="트렌드 · edgeEX", on_load=S.initialize)
@template("/trend", "트렌드", "선택한 태그의 원시값·보정값·최종값을 비교합니다.")
def trend():
    return scada_view("trend")


@rx.page(route="/alarms", title="경보 · edgeEX", on_load=S.initialize)
@template("/alarms", "경보", "현장 사건의 발생·복귀·확인 상태를 조회합니다.")
def alarms():
    return scada_view("alarms")


@rx.page(route="/edge-monitor", title="데이터 흐름 · edgeEX", on_load=S.initialize)
@template("/edge-monitor", "데이터 흐름", "구간별 확인 근거와 데이터 도착 상태를 살펴봅니다.")
def flow():
    return scada_view("flow")


@rx.page(route="/comm", title="통신 이력 · edgeEX", on_load=S.initialize)
@template("/comm", "통신 이력", "조회 기간에 저장된 표본과 품질을 확인합니다.")
def communication():
    return scada_view("communication")
