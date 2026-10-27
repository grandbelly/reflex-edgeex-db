"""Six thin routes using the official stock template adaptation."""
import reflex as rx
from ..components.scada import template
from ..states.scada_state import ScadaState as S
from ..views.scada_view import scada_view


@rx.page(route="/", title="대시보드 · edgeEX", on_load=S.initialize)
@template("/", "대시보드", "우선 확인할 자료에서 현장·태그의 근거로 이동합니다.")
def overview():
    return scada_view("overview")


@rx.page(route="/workflow", title="워크플로우 · edgeEX", on_load=S.initialize)
@template("/workflow", "워크플로우", "측정·판단·조치·피드백의 실행 근거를 추적합니다.")
def process():
    return scada_view("process")


@rx.page(route="/trend", title="트렌드 · edgeEX", on_load=S.initialize)
@template("/trend", "트렌드", "값이 언제 변했는지, 그 표본의 품질과 처리 근거를 함께 확인합니다.")
def trend():
    return scada_view("trend")


@rx.page(route="/alarms", title="알람 · edgeEX", on_load=S.initialize)
@template("/alarms", "알람", "원천 경보 사건의 발생·복귀·확인 상태를 나란히 살펴봅니다.")
def alarms():
    return scada_view("alarms")


@rx.page(route="/edge-monitor", title="Edge 관제 · edgeEX", on_load=S.initialize)
@template("/edge-monitor", "Edge 관제", "전달 단계의 관측 범위와 실제 상위 도착 표본을 대조합니다.")
def flow():
    return scada_view("flow")


@rx.page(route="/comm", title="통신 상태 · edgeEX", on_load=S.initialize)
@template("/comm", "통신 상태", "채널이 언제 끊기고 복구됐는지 원천 연결 이력으로 확인합니다.")
def communication():
    return scada_view("communication")
