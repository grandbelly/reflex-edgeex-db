# Reflex 0.10 기술 기반과 템플릿 전환

화면 설계의 현재 정본은 [메뉴별 시각화 계약](mini_scada_visualization_contract.md) → [28종 전수 비교](reflex_template_catalog.md) → [컴포넌트·레이아웃 설계](mini_scada_component_layout_design.md)다. stock_market 상단 탐색/고밀도 표와 stock_graph 헤더/기간/연한 area/tooltip을 실제 Reflex 화면으로 이식했다. 아래 Dashboard 기록은 초기 기술 기반의 이력이다. 여섯 메뉴의 실제 브라우저 UX 수용은 아직 완료되지 않았다.

## stock 이식의 실제 범위

공통 외형은 상단 여섯 메뉴, dark 토큰, 작은 context bar와 section frame이다. 대시보드는 실제 자료 확인 대상/관측 채널/최근 경보, 워크플로우는 정본 모델 미연결 구획, 트렌드는 numeric source-time 축·실제 기간 선택·불확실 점선·받은 표본 선택/근거, 알람은 사건 ID 목록·상세, 통신 상태는 연결 이력 미연결/Health 구획, Edge 관제는 다섯 전달 단계의 관측 범위와 실제 최신 표본이다. 다른 메뉴에 전체 태그 표를 반복하지 않는다.

트렌드 슬라이더는 새 DB 조회 없이 원래 표본의 source/ingestion·값·사유를 고른다. brush는 받은 범위의 로컬 확대다. 템플릿의 random/yfinance·금융 손익 색·0 대체/음수 절단·이벤트 없는 버튼은 복사하지 않았다. 이력 query는 ingested_at/reasons를 읽고 서비스에서 표본별로 보존한다. 실제 모델/시도 분모/전달 지표가 없는 메뉴는 근거 없는 상태나 성공률을 만들지 않는다.

설치된 0.10.1 Recharts `Area`의 필드와 생성 JSX를 대조했다. `hide`, `fillOpacity`, `strokeDasharray`는 이 버전의 Python 선언 필드가 아니므로 `custom_attrs`로 전달한다. 일반 키워드는 CSS `wrapperStyle`로 들어가 비교 계열 표시 전환·점선이 작동하지 않을 수 있다. 숫자 시간 축과 tooltip formatter도 생성 JSX에서 확인하며, 실제 동작 수용과 구별한다.

최종 번들은 Reflex의 frontend export 경로를 사용한다. `bun run export`만 부르면 Reflex가 만드는 SPA `404.html` 후처리를 건너뛰어 하위 URL 직접 접속이 404가 됐다. 원시 실패를 보존하고 공식 export로 다시 만든다. 설정의 loglevel도 문자열 대신 `rx.constants.LogLevel.WARNING`을 사용하여 CLI 밖의 설정 import에서 발생한 0.10.1 타입 오류를 해소했다.

전용 Edge 프로필을 셸에서 기동하려던 명령이 자동 승인 검토에서 `rejected: blocked by policy`로 거절됐다. 오너 열람 창이나 Chrome9333으로 우회하지 않았다. 실제 새 화면 GUI/키보드/반응형 수용은 NOT RUN이며, compile/계약 시험/독립 SQL/HTTP 확인과 구별한다. 이 제한이 해소되기 전 UI 합격·운전 배포 완료로 보고하지 않는다.

오너 지시(2026-10-28): Context7으로 최신 Reflex 사용법을 읽고 업그레이드하며, 미니 SCADA 전체에 템플릿을 활용한다.

## 정본과 적용

- 공식 템플릿: https://github.com/reflex-dev/templates/tree/e56a1a065208924dada4d23c769d15114381c6b5/dashboard
- 참조 파일: `dashboard/templates/template.py`, `components/sidebar.py`, `components/navbar.py`, `components/card.py`, `views/stats_cards.py`, `styles.py`.
- 초기 `edgeex_app/components/scada.py`는 공통 페이지 래퍼·사이드바·native `rx.card` 합성 구조를 Dashboard에서 가져왔다. 현재 stock 이식은 사이드바를 상단 탐색으로 바꾸고, 카드 대신 메뉴별 section/grid/표/차트의 위계를 적용했다. 수치와 내용은 실제 VQT 조회에 연결한다.
- 초기 래퍼는 Dashboard 템플릿을 따랐다. 최종 배치는 메뉴별 설계의 비율과 역할을 따른다. 현장·태그·시간·시점 고정, 품질/현재성 분리, 읽기 전용 표출은 이 프로젝트 계약이다. 수익·증감률 예제와 설정 편집 페이지는 가져오지 않는다.

## 확인한 버전과 문서

공식 PyPI·변경 기록에서 확인한 최신 안정 버전은 `reflex==0.10.1`(2026-10-26)이다. 전용 Windows Python 3.12 venv와 전용 `REFLEX_DIR`에 설치한다. 기존 운전 venv와 전역 Bun을 업그레이드하지 않는다.

Context7 공식 remote MCP `https://mcp.context7.com/mcp`의 `resolve-library-id`, `query-docs`로 `/reflex-dev/reflex/v0.10.0`과 `/websites/reflex_dev`를 읽었다. 질문/응답 원문은 별도 수용 영수증에 보존한다.

- https://reflex.dev/docs/changelog/
- https://reflex.dev/docs/changelog/upgrading/upgrading-to-0-10/
- https://reflex.dev/blog/upgrading-reflex-0-8-to-0-9/
- https://reflex.dev/docs/library/layout/card/
- https://reflex.dev/docs/library/layout/grid/
- https://reflex.dev/docs/library/other/theme/
- https://reflex.dev/docs/library/data-display/moment/
- https://reflex.dev/docs/advanced-onboarding/code-structure/

## 코드 적용 기준

`edgeex_app.py`는 새 `pages/scada.py`만 등록한다. 구형 Chakra 레이아웃, ORM 모델, AI·Consumer·스케줄러와 기존 수정 이벤트는 이 진입점에서 import하지 않는다. 기존 소스는 단계적 이관을 위해 남아 있으며 0.10 호환을 주장하지 않는다.

`SCADA_DATA_SOURCE` 기본값은 `edge_vqt`이고, 다른 프로필로 앱을 실행하면 명시적으로 실패한다. DB 연결은 환경 `TS_DSN`으로만 받는다. 앱 import/compile 시 DB를 열거나 `.env`를 자동 검색하지 않는다. ORM용 `db_url`을 억지로 설정하지 않는다.

State는 `rx.State`를 직접 상속하고 이벤트와 타입을 명시한다. 자동 setter, 구형 State class 내부 속성, private `token_to_sid`에 의존하지 않는다. 브라우저 `rx.moment`의 5초 이벤트가 유한 조회를 요청한다. 탭이 사라진 뒤 무한 백엔드 루프가 남지 않는다. 같은 브라우저의 중복 조회는 합치고 이전 조건의 응답을 버린다.

고정 모드는 마지막 완료 응답을 유지한다. 고정 중 태그 클릭은 그 응답 안의 상세만 선택하고 이력을 비운다. 새 이력은 명시적인 ‘지금 조회’ 또는 실시간 재개로 읽는다. 조건 ‘적용’과 ‘지금 조회’는 고정 모드에서도 새 응답을 읽는 사용자 행동이다.

반응형 grid와 같은 카드 크기·간격·색상 토큰을 사용한다. 검색/페이지 이동은 이미 받은 최신 태그 집합에 적용하고 DB를 다시 읽지 않는다. 오류·빈 자료·미수신 정의는 분리한다. Health 실패를 정상으로 숨기거나 NULL을 0으로 채우지 않는다.

## 실행과 검증

`python -m pip install -r requirements-edge-web.txt`, `python -m pip check`, `python -m unittest discover -s tests -p test_scada_contract.py -v`, `reflex compile --no-rich` 순서로 확인한다. Windows는 `PYTHONUTF8=1`을 설정한다. UTF-8 `.gitignore`를 cp949로 읽는 프레임워크 초기화 오류가 있어 필요하다.

별도 localhost에서 `reflex run --env preview --backend-host 127.0.0.1 --backend-port 3101`로 실행한다. 0.10 state는 `memory`를 사용해 구형 Redis/disk state와 섞지 않는다. 운영 전환, RPI, 재기동·부하·쓰기 기능은 별도 검증이다.

실제 0.10.1 컴파일의 deprecation 안내와 설치된 공식 패키지 소스를 추가 대조하여, 구형 `App(theme=...)` 대신 `rx.plugins.RadixThemesPlugin(theme=rx.theme(...))`를 사용한다. Context7 문서에 남은 구형 예시를 그대로 적용하지 않는다.
