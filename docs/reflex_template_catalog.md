# 공식 Reflex 템플릿 전수 비교

2026-10-28 오너 지시: “템플릿 전체를 다 스터디해서 최적의 컴포넌트와 레이아웃을 매칭하여 설계해라.” 결과 설계는 [컴포넌트·레이아웃 설계](mini_scada_component_layout_design.md), 화면별 배치는 [오프라인 설계 보드](mini_scada_layout_board.html)에서 본다.

## 범위와 확인 방법

[공식 templates.json](https://github.com/reflex-dev/templates/blob/e56a1a065208924dada4d23c769d15114381c6b5/templates.json)의 **등록 27종 전부**와 저장소에만 남은 `dalle` 1종을 비교했다. “전체”는 이 기준 SHA의 공식 템플릿 목록이다. 커뮤니티의 모든 Reflex 앱, 공개 데모의 모든 기능을 실행했다는 뜻은 아니다.

- 본체: `reflex-dev/templates@e56a1a065208924dada4d23c769d15114381c6b5`. GitHub 재귀 트리 `truncated=false`, codeload 원본 SHA256 `935f168496373bb7b39c1002c966ecca147b30ed9b116c74cfcf222cef35800a`.
- 목록의 gitlink 두 개도 제외하지 않았다. `reflex-chat@b5c02280292a5e9550974cc242a3096ba67099b0`, `reflex-llamaindex-template@a8a4148370add7f770979af1ba974aaca08b408e`의 고정 소스를 읽었다.
- `sidebar`는 본체에 없으므로 공식 별도 저장소 `reflex-dev/sidebar-template@73b7b44a1d9aec6f1df8c93a2eedc8e5833963c5`를 확인했다. 등록은 hidden이며 현재 기본 틀로 선정하지 않았다.
- `blank`는 설치된 `reflex-base==0.10.1`의 `.templates/apps/blank/code/blank.py`를 확인했다.
- **359개 Python 파일·24,557줄을 정적으로 목록화**했다. 이는 전 행을 사람처럼 정독했다는 주장이 아니다. 각 앱의 진입 배치, 대표 컴포넌트, State 이벤트·자료 출처·의존성을 비교하고 채택 후보의 주요 함수와 위험 동작을 직접 읽었다. 본체가 제공하는 `preview.webp` 20개도 확인했다. preview가 없는 앱의 화면 실행 검증은 하지 않았다.
- 파일 해시·함수 위치·정규화한 컴포넌트·이벤트 수는 [원본 목록](template-study/inventory.json)에 있다. `import reflex.components.recharts as recharts`도 `rx.recharts`로 정규화했다. 예제 앱을 import/실행하거나 예제 의존성을 추가 설치하지 않았다.

## 28종 비교와 판정

아래 경로는 달리 적지 않으면 본체 SHA 내부 경로다. 선정은 산업 운전 질문과의 적합성, 실제 자료를 왜곡하지 않는 표현, 동작의 연결성, 정보 밀도, 0.10.1 이식 비용, 읽기 전용 제약 순으로 판단했다. 근거 없는 수치 점수는 붙이지 않았다.

|템플릿|확인한 구조·대표 소스|매칭과 채택 범위|그대로 가져오지 않는 것|
|---|---|---|---|
|`blank`|환영 화면·docs 링크·빈 State; 설치본 `code/blank.py:index`|최소 진입점 비교 기준|운전 정보 구조가 없어 화면 기준으로 제외|
|`dashboard`|`dashboard/pages/index.py`, `components/card.py`, `views/charts.py`, sidebar/template 합성|native Reflex 페이지 래퍼의 기술 기준; 공통 부품만|모든 메뉴에 같은 KPI+차트를 반복하는 구조, randomize_data, 장식 알림 수|
|`sidebar`|별도 저장소 `sidebar/templates/template.py:template`, `components/sidebar.py:sidebar_item`|반응형 탐색 대안 검토|구형 theme 래퍼·범용 설정 화면; 주 배치는 오너 선택 stock 상단 탐색으로 결정|
|`sales`|`sales/sales.py:index`, backend, table와 email 생성 분할|폼·목록 패턴 비교 후 현 범위 제외|DB CRUD·OpenAI 이메일·영업 의미|
|`ai_image_gen`|`pages/index.py`, options sidebar/mobile UI, loading/cancel/preview 분리|트렌드 고급 설정을 접는 보조 패턴만 참고|Replicate·이미지 비교/확대 래퍼·외부 API·생성기 State|
|`ci_template`|`cijob/views/table.py:main_table/_create_dialog`, status_badge·시각/기간 열|워크플로우 실행 이력·선택 실행의 메타 정보|승인/삭제 버튼은 실제 실행이 아닌 설명 대화상자; 제어·승인 기능으로 재사용 금지|
|`api_admin_panel`|`pages/dashboard.py`, query/output/drawer, QueryAPI|원문 상세를 여는 방식 비교; 도입 대신 native 읽기 전용 drawer 합성|`reflex-chakra`, 임의 URL 요청·편집·commit; 운전 쓰기 경로|
|`nba`|`components/stats_selector.py:_items_selector`, `views/stats.py`의 brush|트렌드 태그 선택 chip과 범위 축소 동작|무작위 선택, 선수·급여 집계, 범주 축 brush를 시간 축으로 그대로 전용|
|`customer_data_app`|`customer_data/customer_data.py`, backend DB CRUD, stats/table|상태 배지·표 기본형 비교 후 제외|rx.Model·DB 쓰기, 고객 수 증감 카드|
|`reflex-chat`|별도 gitlink `chat/state.py:process_question/openai_process_question`, action_bar|별도 근거 검색 도우미가 필요한 미래 범위; 현 여섯 메뉴 제외|대화 응답을 운전 사실·정상 판정으로 사용하는 것, 동기 외부 streaming 호출|
|`reflex-llamaindex-template`|gitlink `frontend/state.py:answer`, `views/templates.py:template_card`|안내 카드·설정 popover 비교 후 제외|외부 task 생성 POST, 응답 글자별 애니메이션, `session` 참조가 해결되지 않은 후반 경로; 완제품 가정 금지|
|`admin_dashboard`|`admin_dashboard.py:index`, `components/data_table.py`, `customer_details.py:customer_details_panel`|**알람 8:4 목록·상세 분할**과 선택 행 강조의 주 참조|고객 라이선스 원형 수치·증가=초록 규칙·모의 다른 메뉴|
|`retail_analytics_dashboard`|overview 소형 line chart 반복, `customize_charts_dialog`, 임시 표시 설정 apply|짧은 추이와 보조 설정의 일관된 헤더만 참고|운전 핵심 상태를 숨길 수 있는 자유 편집, 비용/매출 KPI|
|`table_dashboard`|`components/details_table.py`, `states/dashboard_state.py`의 임시/적용 필터·stable ID·pagination|**알람 이력·Edge 근거 표의 동작 기준**|전체 데이터를 State에 올리는 pandas 처리, 잘못된 숫자 필터를 조용히 무시하는 예제 예외 처리|
|`retention_dashboard`|`components/retention.py:retention_cell/retention_component`, `components/workflow.py`|**통신 시간 히트맵 셀·고정 행/열의 시각 기준**|고객 코호트 비율·임의 20/40/60/80 경계. Workflow 탭은 quota 폼+donut이며 실행 흐름도가 아님|
|`business_analytics_dashboard`|`average_salary_chart.py:average_salary_bar_chart`, department pie, 표 필터|품질/원인별 **같은 분모의 건수 비교**가 필요할 때만 보조 bar|Faker, 서로 다른 단위의 공정값을 한 bar/pie로 비교|
|`space_dashboard`|`section_wrapper`, `data_stream_section`, header와 3열 구획|Edge 상세의 구획·항목 정렬 참고|우주 속도 중심 원형 장식, 상수 상태/통신값, launch/control 버튼|
|`account_management_dashboard`|`account_section.py:account_category_section/account_row/mini_sparkline`, summary 구획|**대시보드 현장→설비 그룹의 접기·펼치기**와 작고 정렬된 상태 행|자산 합산/가치 증감 의미, 예제 수치. `graph_placeholder`는 Recharts 부재 시 안내이며 본 그래프는 실제 Recharts|
|`stock_market_dashboard`|진입 3열 grid, `main_header`, `options_table`, `orders_table`, `positions_table`|**전체 디자인의 주 기준**: 상단 탐색·비대칭 구획·고밀도 표·숫자 정렬·선택 행|TradingState random 무한 갱신, 주문/옵션 의미, 이벤트 없는 기간/Buy/Sell 버튼, truthiness로 실제 0 누락|
|`manufacturing_dashboard`|`metrics_summary.py`, `spc_chart.py:spc_chart/render_ooc_dot`의 reference area/line/dot|**트렌드의 유효한 한계선·사건 표식**; 공정 요약행 비교|임의 SPC/합격률/목표 경계. 관리 한계·규격 한계·경보 설정은 다른 정의이므로 혼합 금지|
|`company_dashboard`|`key_metrics`, `visitors_chart`, `documents_table`, header/sidebar|**대시보드의 한 줄 요약·섹션 제목/범례/도구 정렬**|Faker·방문자/문서 의미, 큰 동일 카드 반복. 초기 light 실험을 최종 디자인으로 간주하지 않음|
|`futuristic_dashboard`|`main_content`, performance chart, system status/right sidebar, clock|Edge 처리 자원 지표가 실제 수집될 때 보조 상태 행|고정 CPU/메모리 수치, 장식 LIVE/녹색 정상, 네온·그림자 장식; 가동 시간=조회 성공으로 추정 금지|
|`chat_app`|`chat_interface`, message bubble/typing/input, ChatState|입력/생성 상태 분리만 비교; 현 범위 제외|OpenAI·대화 중심 배치. 운영 핵심 화면을 채팅으로 대체하지 않음|
|`text_annotation_app`|`ner_component`, NER State의 label/class/export|원인 코드의 읽기 전용 배지/범례 참고|측정 provenance를 사용자가 임의 라벨로 덮는 기능, NER 분류를 품질 판정으로 사용|
|`stock_graph_app`|`components/stock_chart_display.py`, `states/stock_state.py`|**트렌드의 주 기준**: 태그/현재값 헤더·기간·연한 area·tooltip·loading/error/empty|yfinance·임의 0 표본·음수 절단·두 자리 일괄 반올림·`a or b`·monotone 보간. moment는 브라우저 조회 tick이며 장치 동시 측정을 뜻하지 않음|
|`admin_panel`|customer_table/customer_edit_form, 검색·stable ID·CSV·페이지|106점 읽기 전용 표 대안 비교; 더 적합한 table/admin 조합 선택|고객 편집 폼, CRUD/일괄 선택을 운전 명령으로 옮기는 것|
|`retail_dashboard`|`details_table`, `dashboard_state`의 draft/apply/reset 필터와 최근 활동|table_dashboard 선정의 반례 비교; 같은 필터 정신을 공유|별도 비슷한 표 시스템을 추가하지 않음; 비용/국가/안정성 의미|
|`dalle` (미등록)|`dalle/dalle.py:index/get_openai_client`, 이미지 생성 State|본체 잔존 예제도 누락 없이 검토, 현 범위 제외|OpenAI 이미지 생성·외부 API; SCADA 정보 표시와 무관|

## 채택할 조합을 좁힌 결과

예제 28개의 CSS·State를 모두 섞지 않는다. **stock_market_dashboard를 시각 규칙의 중심**, **stock_graph_app를 트렌드 중심**으로 두고, 독립적인 동작 패턴만 다음 다섯 군에서 가져온다: account의 그룹 행, admin의 목록·상세, table의 필터·페이지, retention의 행렬, ci의 실행 이력. company의 헤더·manufacturing의 근거 있는 표식은 같은 제품 토큰에 맞춰 합성한다.

`space`/`futuristic`은 상태 구획 비교 자료이며 별도 테마나 의존성을 추가할 이유가 없다. AI·CRUD 예제는 검토 후 제외했다. 전체를 공부한 결과가 전체를 채택한다는 뜻은 아니다.

## 0.10.1 이식과 문서 대조

Context7 공식 remote MCP의 `/websites/reflex_dev`에 grid/table/background event를 질의했다. [Grid recipe](https://reflex.dev/docs/recipes/content/grid/), [Table](https://reflex.dev/docs/library/tables-and-data-grids/table/), [Background events](https://reflex.dev/docs/events/background-events/)를 확인했다. 응답 원문은 영수증에 보존한다.

설치한 0.10.1의 `reflex_components_recharts/charts.py`에서 `sync_id`·`sync_method`, `cartesian.py`에서 `Brush`·숫자 축·`connect_nulls`를 추가 대조했다. 시계열 길이가 다를 때 기본 index 동기화는 어긋날 수 있으므로 시간 값으로 맞추는 설계다. 이 확인은 컴포넌트 API의 존재 확인이며 화면/성능 검증 통과를 뜻하지 않는다.

기존 `App(theme=...)`, 구형 Chakra, 외부 Tailwind CDN/폰트 주입, 예제 의존성을 복사하지 않는다. 새 제품은 전용 venv의 Reflex 0.10.1, native 부품, 로컬 CSS 토큰, 타입이 있는 조회 DTO를 사용한다. 원본 코드를 실제 이식할 때 저장소의 라이선스와 원저작권 고지를 함께 보존한다.

## 미검증

공개 데모의 전 기능 실행, 28개 앱의 설치/컴파일, 이식 후 실제 브라우저·다중 사용자 부하·접근성 수용은 미실행이다. 템플릿 코드의 정상 작동·산업 적합성은 보증하지 않는다. 현재 산출물은 비교와 구현 가능한 설계이며 운전 UI 배포가 아니다.
