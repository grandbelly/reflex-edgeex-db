# D-1029-02 3차 재작업 — design_guide.md(부록 A) Reflex 적용

오너 판정(83c4d86 화면): "reflex를 쓴 게 맞나? reflex 컴포넌트를 하나도 안 쓴 것 같다". 기능 수용은 10/10이었다. 그러나 Radix 기본 외관 그대로였고, 기준 문서 `designs/design_guide.md`("Grafana in Apple Mode")와 참조 구현 `designs/metrics-dashboard`의 디자인 시스템이 적용되지 않았다.

이번에도 화면 계층만 바꿨다. 서비스·쿼리·DB·Kafka 계약은 바꾸지 않았다(`git diff 54028ff -- edgeex_app/queries edgeex_app/services migrations` 빈 출력).

## 절별 적용

| 가이드 절 | 구현 |
|---|---|
| §0 테마 모델 | 기본은 dark, 헤더 버튼(해·달 아이콘)으로 light 전환. `rxconfig.py`에 `default_color_mode="dark"`와 Radix `appearance="inherit"`를 둔다. 토큰은 `<html>` 클래스 하나로 모두 뒤집힌다. 컴포넌트는 색을 모른다 |
| §1.1–1.4 표면·텍스트·강조·경계 | `assets/scada.css`의 두 토큰 블록. 부록 A.1 값 그대로이고, 시험이 문서 값과 글자 단위로 대조한다 |
| §2 상태 | 알약 = 500 레벨 색 + 채움 10% + 테두리 20%, `color-mix`. 10 px bold uppercase, 앞에 점 |
| §3·§8 차트 | 그리드 `3 3` 점선(가로만), 축 10 px mono(축선·눈금선 없음), 사용자 정의 툴팁 상자, 최종값 면적 그라데이션(5%→95%, 0.2→0), `monotone` 2 px, 범례는 카드 하단 수동 점 |
| §4 서체 | Inter + JetBrains Mono(Google Fonts `@import`). 숫자·시각·ID는 mono `tabular-nums` |
| §5 지오메트리 | 카드 18 px, 단계 카드 16, 툴팁 8, 입력 6, 알약 9999. 본문 `p-6`, 카드 간격 24, KPI 간격 20, KPI 높이 185 |
| §6 모션 | `apple-transition`(0.3 s `cubic-bezier(.25,1,.5,1)`), 누르면 `scale(.95)`. `prefers-reduced-motion`이면 끈다 |
| §7.1 KPI | mono 대문자 라벨 + 아이콘, 34 px 값 + 단위, 하단 설명. 불량 태그가 있으면 error 변형(값 빨강, spike 그림자) |
| §7.2 입력 | 검색은 알약형(돋보기, mono), 셀렉트는 네이티브 `select` + chevron. 포커스 시 `#0066cc` 링 |
| §7.3 버튼 | Primary CTA("지금 조회"), Secondary("적용"), 아이콘 버튼, 알약 세그먼트(5/15/60분, 최종값/비교) |
| §9 상태 | hover `--am-hover`, 선택 행은 강조색 10% + 안쪽 선, 포커스 링 공통 |
| App.tsx 구성 | 헤더 h-14(로고·위치·조회 상태·실시간·밝기) → 변수 행(현장·태그·범위) → 서브내비 탭(6메뉴 + CTA) → 본문(제목, KPI 행, 차트·표 카드) |

Radix 컴포넌트(표·슬라이더·링크)는 Radix 변수(`--accent-*`, `--gray-*`, `--color-panel-solid`, 반경, 서체)를 `--am-*`로 다시 가리키는 블록 하나로 같이 뒤집힌다.

## 설계 해석(CM 기록 대상) — DS-017과 충돌 시 design_guide 우선

1. **강조색.** leaf(`#b8e35c`)를 쓰지 않는다. 선택·포커스·활성 탭·최종값 계열은 accent(dark `#2997ff` / light `#0066cc`)다.
2. **품질 색.** 양호=success, 불확실=warning, 불량=error(§2). DS-017의 "정상 무채색"과 q-bad·q-uncertain 보라는 쓰지 않는다.
3. **경보 알약은 무채색.** 원천 `level`→P1–P3 대응 계약이 아직 없다. 경보색은 운전 우선순위를 단정하므로 neutral 토큰으로 둔다(2차와 같음).
4. **트렌드 계열.** 최종값 양호는 Series A 면적. 불확실은 amber 점선과 점, 범례에 따로 표시. 비교 모드의 처리값은 violet 점선, 원시값은 muted-2 실선이다. 불량·결측은 선을 잇지 않는다.
5. **사이드바 생략.** §7.4 사이드바 대신 App.tsx의 서브내비 탭에 6메뉴를 둔다. 이전 오너 결정(상단 탐색, components AGENTS)과 1366 폭을 지키기 위해서다. 배정 (2)의 구성 목록(헤더·KPI 행·차트 카드·표)에도 사이드바는 없다.
6. **dark 선택자.** 부록 A.1은 `[data-theme="dark"]`인데, Reflex는 `<html>`에 `dark`/`light` 클래스를 붙인다. 그래서 `:root:not(.light),[data-theme="dark"]`로 둔다. 하이드레이션 전에도 dark라 흰 화면이 번쩍이지 않는다.
7. **A.1 밖의 짝 토큰.** 가이드 본문에 짝이 적힌 색만 추가했다: selection(§1.3), scrollbar(§1.4), shadow(§6.1), CTA·on-accent(§7.3), hover(§9), 서브내비 배경(App.tsx). 짝이 같은 값(테마 중립)인 토큰은 시험의 `NEUTRAL` 목록에 고정했다.
8. **KPI 값 서체.** §7.1 레시피는 font-sans지만 §4 숫자 규칙("반드시 JetBrains Mono")을 따른다.
9. **스파크라인 생략.** KPI 하단 스파크라인은 넣지 않았다. 집계값(관측 태그 수 등)의 이력이 상태에 없어서, 그리면 지어낸 선이 된다.
10. **해·달 아이콘 색.** 가이드 참조의 `text-yellow-400`는 토큰 짝이 없어 text 색으로 둔다.
11. **라이트 보조 글자색: 가이드 이탈(PL D-1029-02 결정).** 가이드 A.1의 light `muted #7a7a7a`·`muted-2 #86868b`가 WCAG AA 4.5:1에 못 미쳐, 같은 색조에서 어둡게 한 `#636366`·`#68686d`로 바꿨다. 순서(muted가 muted-2보다 진함)는 유지했다. 토큰 값만 바꿨고 dark 값은 그대로다(dark muted는 흰 60%로 충분).

| 바탕(light) | 가이드 `#7a7a7a` | 가이드 `#86868b` | 적용 `#636366`(muted) | 적용 `#68686d`(muted-2) |
|---|---|---|---|---|
| 카드 `#ffffff` | 4.29 | 3.62 | 5.99 | 5.54 |
| 헤더·행 `#fafafc` | 4.12 | 3.48 | 5.74 | 5.32 |
| 페이지·서브내비 `#f5f5f7` | 3.94 | 3.33 | 5.50 | 5.09 |
| 행 hover `#f2f2f2` | 3.83 | 3.24 | 5.35 | 4.95 |
| 헤더 행 hover `#eeeeef` | — | — | 5.16 | 4.78 |
| 선택 행 `#e6f0fa` | — | — | 5.19 | 4.81 |

WCAG 2.x 상대 휘도 공식으로 계산했다. hover·선택 바탕은 반투명 토큰을 흰색(또는 `#fafafc`) 위에 합성한 값이다. 후보 `#6e6e73`은 선택 행에서 4.40이라 쓰지 않았다. `LightContrast` 시험이 6개 바탕 모두에서 4.5 이상을 고정한다(변이 M10).

12. **차트 축·brush 글자색: 가이드 §8 이탈(엣지 031faff FAIL 1, PL 4차 지시).** 가이드는 축을 `--am-axis`(light 검정 45%, dark 흰 30%)로 둔다. SVG 글자로 쓰면 알파 합성 값이 되어 엣지 실측 light 2.84:1(10 px)이었다. 글자 전용 불투명 토큰 `--am-axis-text`를 두 모드에 짝으로 추가했다. light는 `#68686d`(muted-2와 같은 값), dark는 `#a1a1a6`이다. 축 선 획은 가이드 `--am-axis` 그대로다. 글자 크기는 10 → 11 px(축 tick·brush 글자 모두)로 올렸다.

| 바탕 | 이전 `--am-axis` | 적용 `--am-axis-text` |
|---|---|---|
| light 카드 `#ffffff` | 2.84(엣지 실측) | 5.54 |
| light 헤더·행 `#fafafc` | — | 5.32 |
| light 페이지 `#f5f5f7` | — | 5.09 |
| light 행 hover `#f2f2f2` | — | 4.95 |
| light 헤더 행 hover `#eeeeef` | — | 4.78 |
| light 선택 행 `#e6f0fa` | — | 4.81 |
| dark 카드 `#18191b` | 2.71(계산) | 6.84 |
| dark 카드-2 `#1e2022` | — | 6.35 |
| dark 행 `#151617` | — | 7.04 |
| dark 페이지 `#111214` | — | 7.29 |

`ChartText` 시험이 CSS의 축 tick·brush 글자 규칙 2개와 뷰의 `AXIS_TICK`가 이 토큰을 쓰는지, 토큰이 불투명 6자리 hex인지, 두 모드의 모든 바탕에서 4.5 이상인지, 크기가 11 px 이상인지 고정한다(변이 M11–M14).

## 이전 브라우저의 `theme=system`

이전 빌드는 브라우저 `localStorage`에 `theme=system`을 남겼다. 그러면 OS가 라이트일 때 dark 기본이 깨진다. 오너 브라우저도 해당된다.

별도 코드는 넣지 않았다. 이유는 셋이다.

- **dev 모드(엣지 3100 운전 방식):** Reflex 0.10.1 테마 제공자에 이미 처리가 있다. 컴파일된 기본값이 바뀌면(`last_compiled_theme` `system` → `dark`) 처음 한 번 dark로 덮어쓴다. 소스는 `react-theme.js`의 `isDevMode` 분기다.
- **페이지 안 `<script>`:** React 19 dev가 클라이언트 렌더 때 `console.error("Encountered a script tag …")`를 낸다. 수용 #9(콘솔 오류 0)를 깨므로 시도했다가 뺐다. 시험이 페이지 트리의 `<script>` 0을 고정한다(M9).
- **`head_components`:** Helmet이 마운트 뒤에 넣어서 테마 제공자보다 늦다.

prod 빌드로 띄울 때만 남은 `system`이 그대로 쓰인다. 캡처 절차 1번에서 `localStorage.getItem('theme')` 값을 기록해 확인한다.

## 감사 전후(dashboard-ui-audit, 정적)

**전체:** before 21/6/8 → after 20/6/9(pass/partial/fail).

| 검사 | 전 | 후 | 판단 |
|---|---|---|---|
| views VIS-02 | FAIL(HEX 9) | PASS(HEX 0) | 개선 |
| components VIS-02 | PASS | FAIL("토큰 참조 없음") | 컴포넌트가 색을 전혀 이름 붙이지 않고 클래스만 쓴 결과다. 감사 규칙이 이를 FAIL로 읽는다 |
| components IA-02 | PASS | FAIL(14·16 반복) | 아이콘 크기 반복을 데이터 중복으로 센 것이다 |
| css VIS-02 | FAIL(HEX) | FAIL(HEX 43) | 모두 부록 A.1 토큰 블록 안의 값이다. 블록 밖 색 0건은 시험이 고정한다 |
| css VIS-04 | 7종 | 8종 | §4 글자 단계(10·11·12·13·14·16·21·34) 그대로 |

감사 수치를 맞추려고 코드를 바꾸지는 않았다. 원본: `audit-before.json`, `audit-after.json`.

## design-review 자체 점검(정적, 라이브 미실행)

오너 PC 실행 금지로 체크리스트만 소스에 적용했다. 라이브 판정은 엣지 재수용 캡처로 넘긴다.

- 보라 그라데이션 없음. 브랜드 그라데이션은 가이드 §7.4 로고 하나다.
- 이모지 없음. 카드 왼쪽 색 테두리 없음(선택 행 안쪽 선은 선택 표시).
- 카드는 표·목록·차트를 담을 때만 쓴다.
- 숫자 열은 우정렬·고정폭. 빈 상태는 사실 한 줄.
- 포커스 링 2 px. 버튼은 모두 네이티브 `button`이고 이름이 있다.
- 남은 확인(라이브): 글자 10–12 px 가독성, 차트 `var()` 획 적용, Google Fonts 접근 가능 여부(엣지망 차단 시 시스템 서체로 대체).

## 시험

- 47건 OK(`tests.txt`): 기존 36 + 테마 10 + 배치 모델-CSS 일치 1.
- `tests/test_scada_theme.py`:
  1. 부록 A.1 값 대조(light muted·muted-2는 해석 11의 값).
  2. 사용 토큰은 모두 정의돼 있다.
  3. 테마 토큰은 모두 dark 짝이 있다.
  4. 토큰 블록 밖 CSS, 화면 Python, 렌더 결과에 색 리터럴 0.
  5. `color_scheme` 0.
  6. dark 기본 + Radix inherit.
  7. 6메뉴 모두 토글.
  8. 페이지 트리에 `<script>` 0.
  9. light 글자 토큰(text·muted·muted-2)이 6개 바탕에서 대비 4.5 이상, muted가 muted-2보다 진함.
- 변이(`mutants.txt`)는 모두 시험이 잡고, 원복 뒤 47 OK:

| 변이 | 바꾼 것 |
|---|---|
| M6 | 사용 중인 토큰 제거 |
| M7 | dark 짝 제거(라이트 전환 누락) |
| M7b | Radix를 dark로 고정 |
| M7c | 토글 제거 |
| M8 | 뷰에 색 리터럴 |
| M9 | 페이지 트리에 `<script>` |
| M10 | light muted를 가이드 `#7a7a7a`로 되돌림 |

- **빌드:**
  - `reflex compile`은 exit 0(최종 코드).
  - `reflex export --frontend-only`(본문 스크립트가 있던 중간 코드)는 첫 시도에 `/` 사전 렌더링이 시간 초과로 끝났다(exit 1, 2차와 같은 증상). 재시도는 exit 0이었다.
  - 빌드된 HTML 6개 모두 `<p>` 안 블록 요소 0.
  - 빌드 CSS 첫 문장이 Google Fonts `@import`임을 확인했다. 뒤에 오면 무시된다.
- 검색창은 `rx.debounce_input`(300 ms)으로 감쌌다. Radix `rx.input`에서 바꾸면서 debounce가 빠져 글자마다 서버를 왕복하던 것을 되돌린 것이다. `reflex.lock`은 생성 파일이라 커밋하지 않는다.

## 4차 수정(엣지 031faff 재수용 FAIL 2·PARTIAL 1)

영수증: edgeex `fable/receipts/acceptance/20261029T122549+0900__mini-scada-reaccept-031faff/`.

| 지적 | 원인 | 수정 | 시험·변이 |
|---|---|---|---|
| FAIL 13: light SVG 축·brush 글자 2.84:1 | `--am-axis` 알파 토큰을 글자에 씀, 10 px | 불투명 `--am-axis-text` 짝 추가, 11 px(해석 12) | `ChartText` 2건, M11–M14 |
| FAIL 9: `Select` key 경고 console.error 1 | `select()`가 정적 option 목록을 자식 하나(배열)로 넘겨 키 없는 `[jsx(option)…]`로 컴파일됨 | 목록을 풀어(`*items`) 자식으로 넘김. `rx.foreach` 경로는 Reflex가 index 키를 붙인다 | `Markup.test_no_unkeyed_array_children`(6메뉴 렌더 트리에 `[(jsx(` 0), M15 |
| PARTIAL 8: 자동 이벤트가 textbox로 검색창을 못 찾음 | `type="search"`의 역할은 searchbox | `type="text"`로 두어 역할 textbox, 이름 "태그·채널 검색" 유지 | `Markup.test_search_box_has_the_textbox_role`, M16 |

- 시험 51건 OK(`tests-r4.txt`): 47 + `ChartText` 2 + `Markup` 2.
- 변이 6건 모두 잡힘(`mutants-r4.txt`). M15는 정적 목록 페이지 4곳 FAIL, `rx.foreach`를 쓰는 트렌드·흐름은 생성 단계 ERROR로 잡힌다.
- 빌드: `reflex compile` exit 0. `reflex export --frontend-only`는 첫 시도에 `/` 사전 렌더 시간 초과(exit 1, 2·3차와 같은 증상), 재시도 exit 0. 빌드 CSS에 `--am-axis-text`가 있고 빌드 결과에 `type="search"` 0.
- key 경고가 정적 검사로 잡히는 범위는 "목록을 자식 하나로 넘기는" 형태다. 다른 React 콘솔 경고는 엣지 실측으로 확인한다.

## 미검증(엣지 재수용으로 넘김)

- 6경로 × 1920·1366 × dark·light 캡처 24장과 수용 기준 10 판정. 절차는 `CAPTURE_CHECKLIST.md`.
- 콘솔 오류 0, 숫자 열 우정렬, 넘침 0의 실측(1·2차 FAIL 회귀 확인).
- 차트 획·그라데이션이 모드에 따라 바뀌는지.
- Google Fonts 로드.
