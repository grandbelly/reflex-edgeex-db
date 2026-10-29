# 3차 재작업 캡처·측정 절차(엣지)

엣지 PC에서 실행한다. 기동·환경은 2차 재수용(`20261029T062420+0900__mini-scada-reaccept-83c4d86`)과 같게 둔다. 프런트 기동 전에 `.web/env.json`이 있는지 확인한다(1차 문서 참조).

## 캡처 24장

- 경로 6개: `/`, `/workflow`, `/trend`, `/alarms`, `/comm`, `/edge-monitor`
- 뷰포트 2개: 1920×1080, 1366×768
- 모드 2개: dark, light
- 파일명: `menu-<이름>-<폭>-<dark|light>.png`. 자동 조회 1회 완료(`조회 완료`) 뒤 찍는다.

순서:
1. **dark:** 프로필을 그대로 둔 채 처음 연다. 아무것도 누르지 않고 dark로 열려야 한다. 이전 빌드가 남긴 `theme=system`은 본문 스크립트가 고친다. dark로 열리지 않으면 그것이 FAIL이다. 이때 `localStorage.getItem('theme')` 값을 기록한다.
2. **light:** 헤더 오른쪽 밝기 버튼(달 아이콘)을 눌러 light로 바꾼다. 새로고침해도 light가 유지되는지 확인한다.
3. 다 찍은 뒤 밝기 버튼으로 dark로 되돌린다.

## 측정 스니펫(각 경로·폭·모드에서 콘솔 실행)

```js
(() => {
  const d = document.documentElement, cs = e => getComputedStyle(e);
  const mode = d.classList.contains('light') ? 'light' : 'dark';
  const tables = [...document.querySelectorAll('.scada-table-scroll')].map(b => b.scrollWidth - b.clientWidth);
  const numeric = [...document.querySelectorAll('td.scada-number, th.scada-number')]
    .filter(c => cs(c).textAlign !== 'right').length;
  // A surface from the other mode means some element did not flip.
  const other = mode === 'light'
    ? ['rgb(17, 18, 20)', 'rgb(24, 25, 27)', 'rgb(30, 32, 34)', 'rgb(21, 22, 23)', 'rgb(34, 37, 41)']
    : ['rgb(255, 255, 255)', 'rgb(250, 250, 252)', 'rgb(245, 245, 247)'];
  const unflipped = [...document.querySelectorAll('.scada-shell, .scada-shell *')]
    .filter(e => other.includes(cs(e).backgroundColor)).map(e => e.className).slice(0, 5);
  const curve = document.querySelector('.series-a .recharts-area-curve');
  const tick = document.querySelector('.recharts-cartesian-axis-tick-value');
  return {mode, page: cs(document.querySelector('.scada-shell')).backgroundColor,
          card: cs(document.querySelector('.scada-panel:not(.raised)') || d).backgroundColor,
          finalStroke: curve ? cs(curve).stroke : 'no chart', unflipped,
          axisText: tick ? [cs(tick).fill, cs(tick).fontSize] : 'no chart',
          inter: document.fonts.check('12px Inter'), jbMono: document.fonts.check('12px "JetBrains Mono"'),
          pageOverflow: d.scrollWidth - d.clientWidth, tableOverflow: Math.max(0, ...tables),
          numericNotRight: numeric,
          englishQuality: /\b(GOOD|UNCERTAIN|BAD)\b/.test(document.body.innerText),
          isoOnPage: /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(document.body.innerText)};
})()
```

기대값:

| 키 | dark | light |
|---|---|---|
| `page` | `rgb(17, 18, 20)` | `rgb(245, 245, 247)` |
| `card` | `rgb(24, 25, 27)` | `rgb(255, 255, 255)` |
| `finalStroke`(트렌드) | `rgb(41, 151, 255)` | `rgb(0, 102, 204)` |
| `axisText`(트렌드, 4차) | `["rgb(161, 161, 166)", "11px"]` | `["rgb(104, 104, 109)", "11px"]` |

brush 글자는 traveller를 끌 때만 보인다. light 트렌드에서 brush를 끄는 동안 `getComputedStyle(document.querySelector('.recharts-brush-texts text')).fill`을 읽는다. 기대값은 `axisText`와 같은 `rgb(104, 104, 109)`이다(Recharts가 `fill=stroke`를 속성으로 주지만 CSS가 이긴다).

나머지 키는 두 모드 모두 같다:
- `unflipped []`
- `pageOverflow 0`, `tableOverflow 0`, `numericNotRight 0`
- `englishQuality false`, `isoOnPage false`

`inter`·`jbMono`가 false이면 Google Fonts 차단으로 기록한다. 판정은 FAIL이 아니고 시스템 서체로 대체된 것이다. 브라우저 콘솔 오류는 0이어야 한다.

## 수용 기준 10 대응(1·2차 그대로 유지 + 테마)

1·2차의 10항목은 `docs/quality-rework-1028/CAPTURE_CHECKLIST.md` 그대로다. 이번에는 각 항목을 dark·light 두 모드에서 본다. #3 상태 색은 이번 해석을 따른다: 양호 success, 불확실 warning, 불량 error, 경보는 무채색.

테마 추가 판정(캡처·스니펫):

| 항목 | 판정 근거 |
|---|---|
| T1 dark 기본 | 1번 순서에서 누르지 않고 dark |
| T2 전 요소 전환 | `unflipped []`, 캡처에서 표·차트·검색창·알약·탭 확인 |
| T3 차트 전환 | `finalStroke` 기대값, 그리드·축 색 |
