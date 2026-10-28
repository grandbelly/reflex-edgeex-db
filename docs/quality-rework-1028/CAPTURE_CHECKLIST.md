# 품질 재작업 후 캡처·측정 절차

엣지 PC에서 실행한다(상위 `AGENTS.md`: 오너 PC에서 Reflex 실행 금지). 기동·환경은 엣지 수용 영수증
`20261028T091746+0900__d1028-06-mini-scada-edge-accept`와 같게 둔다. 실데이터 SY 현장, 읽기 전용 DSN.
`bun … dev`로 프런트를 띄우기 전에 `.web/env.json`이 있는지 확인한다. `reflex compile`만으로는 생기지 않아 10095cc 재수용 1차 기동이 실패했다. `reflex export --frontend-only --no-zip`을 실행하면 생성된다.

## 캡처

- 경로 6개 `/`, `/workflow`, `/trend`, `/alarms`, `/comm`, `/edge-monitor`
- 뷰포트 1920×1080, 1366×768 → `menu-<이름>-<폭>.png` 12장(전 캡처와 같은 이름)
- 자동 조회 1회 완료(`조회 완료`) 뒤 찍는다.

## 측정 스니펫(각 경로·각 폭에서 콘솔 실행)

```js
(() => {
  const d = document.documentElement;
  const tables = [...document.querySelectorAll('.scada-table-scroll')]
    .map(b => b.scrollWidth - b.clientWidth);
  const numeric = [...document.querySelectorAll('td.scada-number, th.scada-number')]
    .filter(c => getComputedStyle(c).textAlign !== 'right').length;
  const longText = [...document.querySelectorAll('.scada-shell *')]
    .filter(e => e.children.length === 0 && e.textContent.trim().length > 80).length;
  const english = /\b(GOOD|UNCERTAIN|BAD)\b/.test(document.body.innerText);
  const iso = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(document.body.innerText);
  return {pageOverflow: d.scrollWidth - d.clientWidth, tableOverflow: Math.max(0, ...tables),
          numericNotRight: numeric, textOver80: longText, englishQuality: english, isoOnPage: iso};
})()
```

기대값: `pageOverflow 0`, `tableOverflow 0`, `numericNotRight 0`, `textOver80 0`,
`englishQuality false`, `isoOnPage false`. 표본 검사기·선택 사건 시각은 `10-28 09:27:02.038037`처럼 원천 자릿수를 모두 유지하되 ISO `T`·오프셋은 표시하지 않는다.

## 수용 기준 10 대응

| # | 기준 | 확인 위치 |
|---|---|---|
| 1 | 자리표시 0 | 6메뉴 캡처: 아이콘 빈 상자 없음, 미연결은 사실 한 줄 |
| 2 | 말줄임 0 | 캡처 + `textOver80` |
| 3 | 상태 색 운전 의미 | 양호 무채색, 불확실 q-uncertain, 불량 q-bad, 경보색은 경보 표만 |
| 4 | 숫자 정렬 | `numericNotRight 0`, 대시보드 채널 표 캡처 |
| 5 | 가로 스크롤 0 | 1366 `pageOverflow`·`tableOverflow` 0 |
| 6 | 빈 상자 0 | 캡처 |
| 7 | Health 표 없을 때 원인 | `/comm` 캡처의 원인 한 줄 |
| 8 | 전후 캡처 | 전 12장(303c995) + 후 12장 |
| 9 | 콘솔 오류 0 | 브라우저 콘솔 |
| 10 | SQL read-only | 쿼리 계층 변경 없음(`git diff 303c995 -- edgeex_app/queries edgeex_app/services` 빈 출력) |
