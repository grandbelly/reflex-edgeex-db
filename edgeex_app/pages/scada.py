"""Five thin routes using the official stock template adaptation."""
import reflex as rx
from ..components.scada import template
from ..states.scada_state import ScadaState as S
from ..views.scada_view import scada_view


@rx.page(route="/", title="대시보드 · edgeEX", on_load=S.initialize)
@template("/", "대시보드", "선택 현장의 최신 표본 품질과 확인할 태그")
def overview():
    return scada_view("overview")


@rx.page(route="/trend", title="트렌드 · edgeEX", on_load=S.initialize)
@template("/trend", "트렌드", "선택 태그의 값 변화와 표본별 품질·처리 근거")
def trend():
    return scada_view("trend")


@rx.page(route="/alarms", title="경보 · edgeEX", on_load=S.initialize)
@template("/alarms", "경보", "원천 경보 사건의 발생·복귀·확인 상태")
def alarms():
    return scada_view("alarms")


@rx.page(route="/edge-monitor", title="Edge 관제 · edgeEX", on_load=S.initialize)
@template("/edge-monitor", "Edge 관제", "전달 경로와 상위 DB에 도착한 표본")
def flow():
    return scada_view("flow")


@rx.page(route="/comm", title="통신 상태 · edgeEX", on_load=S.initialize)
@template("/comm", "통신 상태", "채널 Health와 채널별 최신 수신 시각")
def communication():
    return scada_view("communication")
