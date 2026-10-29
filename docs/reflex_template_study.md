# 미니 SCADA에 사용할 공식 Reflex 템플릿 스터디
2026-10-28 후속 전수 조사: **등록 27종 + 미등록 1종 전체 비교의 정본은 [템플릿 전수 비교](reflex_template_catalog.md)**다. 최종 조합·비율·데이터/동작 계약은 [컴포넌트·레이아웃 설계](mini_scada_component_layout_design.md), 검토할 화면 배치는 [설계 보드](mini_scada_layout_board.html)에 있다. 아래는 처음 선정한 후보의 상세 관찰이며 전체 목록이 아니다.


2026-10-28 오너가 `stock_market_dashboard` 배치와 `stock_graph_app` 실시간 그래프를 직접 선택했다. 초기 Dashboard 기본형과 Company Dashboard는 비교 자료이며 최종 기준이 아니다.

## 읽은 정본

공식 저장소 [reflex-dev/templates](https://github.com/reflex-dev/templates), 확인 SHA `e56a1a065208924dada4d23c769d15114381c6b5`. 스크린샷뿐 아니라 앱 진입점·컴포넌트·State·모델·requirements·rxconfig를 읽었다. 로컬 원문은 `C:/edgeex-it/cr277/refactor-run/template-review/`에 보존했다. 브라우저 공개 데모를 실행해 금융 데이터를 조회한 검증은 아니다.

|정본|읽은 핵심 파일|배운 구조|
|---|---|---|
|[stock_market_dashboard](https://github.com/reflex-dev/templates/tree/e56a1a065208924dada4d23c769d15114381c6b5/stock_market_dashboard)|`stock_market_dashboard.py`, `components/main_header.py`, `line_chart.py`, `options_table.py`, `orders_table.py`, `positions_table.py`, `tooltip_props.py`, `states/trading_state.py`, `models/models.py`|상단 탐색, 큰 차트와 고밀도 표의 비대칭 배치, 하단 사건/상태 표, 숫자 우측 정렬·상태색·작은 헤더|
|[stock_graph_app](https://github.com/reflex-dev/templates/tree/e56a1a065208924dada4d23c769d15114381c6b5/stock_graph_app)|`stock_graph_app.py`, `components/stock_chart_display.py`, `states/stock_state.py`|선택 항목·현재값을 강조한 헤더, 실제 State에 연결된 기간 선택, 초록 선/그라데이션 영역, 얇은 수평 그리드, 정돈된 tooltip, loading/error/empty 분리, 5초 moment 갱신|
|[company_dashboard](https://github.com/reflex-dev/templates/tree/e56a1a065208924dada4d23c769d15114381c6b5/company_dashboard)|`key_metrics.py`, `visitors_chart.py`, `documents_table.py`, `header.py`, `sidebar.py`, 앱 진입점|작은 KPI, 구분선·여백·서체 위계, 차트 헤더와 표 툴바의 합성|
|[manufacturing_dashboard](https://github.com/reflex-dev/templates/tree/e56a1a065208924dada4d23c769d15114381c6b5/manufacturing_dashboard)|`metrics_summary.py`, `dashboard_header.py`, preview|공정 항목별 요약과 고밀도 상태 표시. 한계/목표값이 있어야 SPC 판정을 연결할 수 있음|

## 코드에서 확인한 것

`stock_market_dashboard`는 3열 grid에서 차트와 넓은 옵션 표를 배치하고, 아래 주문·포지션 표를 연결한다. 모든 정보를 똑같은 큰 카드로 만들지 않는다. 데이터의 역할에 따라 폭과 밀도를 달리한다. 테이블의 선택색·헤더·수치 정렬도 한 화면 규칙으로 묶여 있다.

이 템플릿의 `TradingState`는 random 시뮬레이션이다. `chart_controls()` 기간 버튼에는 이벤트가 연결되지 않았고 Buy/Sell도 예제 화면이다. SCADA의 동작 완성 근거로 삼을 수 없다. `render_option_cell()`의 truthiness 조건은 실제 0을 `-`로 바꾼다. 이것은 가져오지 않는다.

`stock_graph_app`의 기간 버튼은 `StockState.set_time_range()`에 실제 연결돼 자료를 다시 읽는다. `rx.moment(interval=5000, on_change=...temporal)`가 갱신 요청을 만든다. 별도 장치 수집 루프가 아니다. 현재가는 서버의 typed State에서 정리하고 차트는 `rx.recharts.area_chart`로 그린다.

이 템플릿 역시 금융용 보정이 있다. 자료가 없을 때 0인 가짜 차트 점을 만들고, y축 하한을 0으로 제한하며, 현재가 조회에 `a or b`를 쓴다. 실제 0·음수·결측을 다루는 PLC 화면에는 그대로 적용하지 않는다. 차트의 monotone 곡선과 수치 반올림도 측정값의 의미를 바꿀 수 있으므로 이식 대상과 분리한다.

## 적용 결정

|템플릿 요소|미니 SCADA 연결|
|---|---|
|상단 주 탐색|운전 개요·공정 감시·트렌드·경보·데이터 흐름·통신 이력|
|종목/현재가 헤더|선택 태그·FINAL·단위·품질·원천 시각|
|옵션 고밀도 표|태그별 RAW / COND / FINAL / 품질 / 현재성|
|최근 주문|원천 최근 경보 사건: 발생·복귀·확인|
|포지션/계정 상태|채널 Health·실제 품질 구성·선택 표본 상세|
|실시간 area chart|기존 VQT 이력 + NULL 공백 + 원천 시각 축, 선/그라데이션/tooltip 스타일 이식|
|기간 버튼|실제로 지원하는 5·15·60분 조회에 연결; 장기 집계는 준비 전 노출하지 않음|
|live indicator|화면 자동 조회 여부를 표시; PLC 통신 정상 표시로 사용하지 않음|

Reflex 0.10.1의 native 컴포넌트와 로컬 CSS로 이식한다. 구형 `App(theme=...)`는 RadixThemesPlugin으로 옮긴다. 템플릿 금융 State·yfinance·랜덤 생성기·외부 로고/폰트·가짜 수치는 앱에 넣지 않는다. 기존 읽기 전용 서비스, 현장 격리, 동시 조회 제한, 응답 세대 판정과 시점 고정을 유지한다.

## 화면을 검수할 기준

색상 몇 개를 바꾸는 것으로 적용 완료라고 하지 않는다. 상단 탐색, 차트/표의 폭 비율, 숫자 정렬, 헤더·필터·기간 선택의 위치, 표의 행 밀도, tooltip·축·legend·선택 상태를 원본 preview와 실제 캡처로 비교한다. 차트의 갱신·기간 선택·태그 선택도 실제 자료로 확인한다. 최종 제품 SHA에서 계약 시험·컴파일·DB 대조와 화면을 다시 연결한다. 운전 배포는 별도다.
