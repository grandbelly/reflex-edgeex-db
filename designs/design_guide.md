# Design System Specification — Grafana in Apple Mode

> 시스템 모니터링 도구(Grafana)의 **정보 집약도**와 애플(Apple) 특유의 **절제된 타이포그래피·
> 우아한 여백·고대비 미니멀리즘**을 융합하는 프리미엄 하이브리드 대시보드 설계 사양.
>
> 이 문서의 모든 토큰 값은 참조 구현 `designs/metrics-dashboard/`
> (React 19 · TypeScript · Tailwind v4.1 · Recharts 3.9 · motion 12.23 · lucide 0.546)에서
> **그대로 추출**한 것입니다. 추측값 없음 — 가이드가 곧 구현입니다.
> Reflex(실제 앱) 적용은 **부록 A**를 참조.

---

## 0. 철학 & 테마 모델 (Theme Model)

**대원칙**: 기본 제공되는 보라/푸른 그라데이션이나 탁한 회색을 절대 쓰지 않는다. 극도로 계산된
on/off-white와 deep-black 배색만 사용한다. **다크·라이트 전환 시 배경·카드·차트·그리드·검색창·
배지 등 모든 요소가 빠짐없이 자연스럽게 뒤집혀야 한다.**

참조 구현의 테마 전환 방식(`src/App.tsx:50`):

```tsx
const [theme, setTheme] = useState<'light' | 'dark'>('dark');   // 기본 = dark
const isDark = theme === 'dark';
// 모든 컴포넌트에 theme prop 전달 → isDark 삼항으로 클래스 분기
className={isDark ? 'bg-[#18191b] border-white/5' : 'bg-white border-[#e0e0e0]'}
```

> 규칙: 색을 하드코딩하지 말고 **토큰**(§1~§4)으로 사고하라. 한 요소를 칠할 때마다 "이 토큰의
> 다크/라이트 짝은 무엇인가"를 함께 정한다. 토큰 짝이 없으면 그 색은 시스템에 없는 색이다.

---

## 1. 색상 토큰 — Surfaces / Text / Accent / Border

### 1.1 표면 (Surfaces) — 깊이 5단계

| 토큰 | 용도 | Dark | Light |
| :--- | :--- | :--- | :--- |
| **page** | 전체 배경 (밤하늘) | `#111214` | `#f5f5f7` |
| **card** | 기본 카드 본문 | `#18191b` | `#ffffff` |
| **card-raised** | 지표/차트 카드 (한 단 올림) | `#1e2022` | `#ffffff` |
| **header** | 상단 헤더·사이드바·서브내비 | `#18191b` | `#fafafc` |
| **row** | 변수(데이터소스) 바·쿼리 에디터 | `#151617` | `#fafafc` |
| **select** | 셀렉트/드롭다운 입력 | `#222529` | `#ffffff` |
| **console** | 로그 터미널 배경 | `rgba(0,0,0,.45)` | `#fafafc` |

> 다크는 `#111214 → #151617 → #18191b → #1e2022`로 **올라갈수록 밝아지는** 4-tier 깊이감.
> 라이트는 `#f5f5f7`(page) 위에 순백 카드(`#ffffff`)와 `#fafafc`(헤더/행)로 미세 대비.

### 1.2 텍스트 (Text) — 4단계 명도 사다리

| 토큰 | 용도 | Dark | Light |
| :--- | :--- | :--- | :--- |
| **text** | 핵심 텍스트 | `#ffffff` | `#1d1d1f` (차콜, 순흑 금지) |
| **muted** | 보조 라벨 | `rgba(255,255,255,.6)` | `#7a7a7a` |
| **muted-2** | 약한 보조 | `rgba(255,255,255,.4)` | `#86868b` |
| **faint** | 최약 (placeholder/아이콘) | `rgba(255,255,255,.3)` | `rgba(0,0,0,.3)` |

### 1.3 시그니처 액센트 (Accent Blue)

| 토큰 | 용도 | Dark | Light |
| :--- | :--- | :--- | :--- |
| **accent** | 액티브·라인·아이콘·CTA | `#2997ff` (SF Blue) | `#0066cc` (Link Blue) |
| **accent-press** | 버튼 hover/press | `#0071e3` | `#0071e3` |
| **focus** | 포커스 링 | `#0066cc` | `#0066cc` |
| **selection-bg** | 텍스트 선택 배경 | `rgba(0,102,204,.4)` | `rgba(0,102,204,.2)` |

> 다크 UI 표면색은 `#2997ff`, 포커스 링은 양 테마 공통 `#0066cc`. CTA 버튼 배경은 `#0066cc`,
> hover 시 `#0071e3`.

### 1.4 보더 & 스크롤바

| 토큰 | 용도 | Dark | Light |
| :--- | :--- | :--- | :--- |
| **border** | 표준 카드 보더 | `rgba(255,255,255,.05)` | `#e0e0e0` |
| **border-strong** | 입력/툴팁 보더 | `rgba(255,255,255,.1)` | `#e0e0e0` |
| **hairline** | 미세 분할선 | `rgba(255,255,255,.05)` | `#f0f0f0` |
| **scrollbar-thumb** | 6px 트랙 thumb | `rgba(255,255,255,.16)` | `rgba(0,0,0,.12)` |
| **scrollbar-hover** | thumb hover | — | `rgba(0,0,0,.24)` |

---

## 2. 시맨틱 상태 색상 (Status / Semantic)

500-레벨 색상 1개 + 투명도 패턴으로 **fill/border/text를 한 세트로** 운용한다. 양 테마 공통.

| 상태 | Text/Dot | Fill | Border |
| :--- | :--- | :--- | :--- |
| **Error / Critical** | `#ef4444` (red-500) | `red-500/10` | `red-500/20` |
| **Warning / Pending** | `#f59e0b` (amber-500) | `amber-500/10` | `amber-500/20` |
| **Success / Healthy** | `#10b981` (emerald-500) | `emerald-500/10` | `emerald-500/20` |
| **Info** | `#2997ff` (dark) / `#0066cc` (light) | `*/10` | `*/20` |

**상태 배지(pill) 표준형**:
```
inline-flex items-center space-x-1.5  px-2.5 py-1  rounded-full
text-[10px] font-bold uppercase tracking-wider
bg-{c}-500/10  text-{c}-500  border border-{c}-500/20
```
- **Firing(발화) 상태에만** `animate-pulse` + 앞에 ping 도트(`h-2 w-2 rounded-full bg-{c}-500 animate-ping`).
- 심각도 태그(Crit/Warn/Info)는 더 작게: `text-[10px] uppercase font-mono font-bold px-1.5 py-0.5 rounded`
  (다크 fill은 `bg-{c}-950/45`, 라이트는 `bg-{c}-100`).

---

## 3. 데이터 시리즈 팔레트 (Chart Series)

차트 라인/면적·KPI 스파크라인에 쓰는 고정 색. 시리즈별 의미를 고정해 일관성을 유지한다.

| 시리즈 | 색 | 의미(참조) |
| :--- | :--- | :--- |
| **Series A (accent)** | `#2997ff` / `#0066cc` | HTTP requests, CPU, Response time(정상) |
| **Series B (violet)** | `#a855f7` | DB latency, Memory |
| **Series C (emerald)** | `#10b981` | Network-in, Request rate, Error rate(정상) |
| **Series D (amber)** | `#f59e0b` | Network-out, Response time(경고) |
| **Series E (alarm)** | `#ef4444` | 이상치(anomaly) 발화 시 빨강으로 시프트 |

> violet/emerald/amber는 테마 중립(다크·라이트 동일). accent 계열만 테마별로 분기.

---

## 4. 타이포그래피 (Typography)

```
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
--font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
--font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, monospace;
-webkit-font-smoothing: antialiased;  -moz-osx-font-smoothing: grayscale;
```

| 역할 | 크기 | 굵기 | 추가 |
| :--- | :--- | :--- | :--- |
| 페이지 타이틀 | `text-[21px]` / `text-lg` | semibold | `tracking-tight` |
| 카드 타이틀(h3) | `text-base` | semibold | `tracking-tight` |
| 지표 값(metric) | `text-[34px]` | semibold (이상치 시 bold) | `leading-none`, **mono** |
| KPI 라벨(대문자) | `text-[11px]` | bold | `uppercase tracking-tight font-mono` |
| 표준 라벨 | `text-xs` | medium/semibold | — |
| 메타/배지 | `text-[10px]` | bold | 자주 `font-mono` |
| 헬퍼/타임스탬프 | `text-[9px]` | — | `font-mono` |

**숫자 규칙**: 지표 값·타임스탬프·쿼리·ID는 반드시 **JetBrains Mono**(`font-mono`)로 자릿수
정렬. 대문자 라벨은 `tracking-wider`, 제목은 `tracking-tight`.

---

## 5. 지오메트리 (Radius · Spacing · Layout)

### 5.1 반경 스케일 (Radius)

| 토큰 | 값 | 용도 |
| :--- | :--- | :--- |
| **r-card** | `18px` (`rounded-[18px]`) | 1차 카드/패널/다이얼로그/이상치 배너 |
| **r-card-2** | `16px` (`rounded-2xl`) | 알림 규칙·커넥션 카드 |
| **r-lg** | `8px` (`rounded-lg`) | 툴팁·콘솔·작은 컨테이너 |
| **r-input** | `6px` (`rounded-md`) | 셀렉트·입력 |
| **r-sm** | `2px` (`rounded-sm`) | 인라인 배지 |
| **r-pill** | `9999px` (`rounded-full`) | 알약 버튼·검색창·상태 배지·아바타 |

### 5.2 여백 스케일 (Spacing)

- 카드 패딩: KPI = `p-5`, 패널 = `p-6`, 토폴로지 노드 = `p-4`.
- 본문: `p-6 space-y-6`. 헤더/행 가로: `px-6`.
- 그리드 간격: KPI = `gap-5`, 차트/패널 = `gap-6`, 노드 = `gap-4`.
- 아이콘+텍스트: `space-x-1.5` ~ `space-x-3.5`.

> "여백의 미": 정밀한 시스템 정보 사이에 숨 쉴 공간(negative space)을 확보한다. 패딩은 최소
> `p-5` 이상을 기본으로 한다.

### 5.3 레이아웃 그리드 (Layout)

| 영역 | 사양 |
| :--- | :--- |
| **사이드바** | 펼침 `w-64`(256px) ↔ 접힘 `w-16`(64px), `border-r`, 접힘 시 아이콘 툴팁 |
| **상단 헤더** | `h-14`(56px), `px-6 border-b`, `flex justify-between` |
| **변수 바 / 서브내비** | `px-6 py-3` / `px-6 py-2` |
| **본문** | `flex-1 overflow-y-auto p-6 space-y-6` |
| **KPI 그리드** | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5`, 카드 `h-[185px]` |
| **차트 그리드** | `grid-cols-1 lg:grid-cols-3 gap-6`, 메인 `lg:col-span-2`, `min-h-[380px]` |
| **로그+토폴로지** | `grid-cols-1 xl:grid-cols-5 gap-6` → 로그 `col-span-3` / 토폴로지 `col-span-2` |

---

## 6. 엘리베이션 & 모션 (Elevation & Motion)

### 6.1 그림자 (Shadow)

| 토큰 | Tailwind | 용도 |
| :--- | :--- | :--- |
| **shadow-card** | `shadow-2xl` | 다크 카드(고대비 띄움) |
| **shadow-soft** | `shadow-sm` | 라이트 카드(은은) |
| **shadow-tooltip** | `shadow-xl` | 툴팁·사이드바 collapsed 툴팁 |
| **shadow-alarm** | `shadow-lg shadow-red-500/20` | 이상치 인시던트 버튼 |
| **shadow-spike** | `rgba(239,68,68,.1) 0 10px 30px` | 이상치 발화 카드(인라인 style) |

### 6.2 모션 (Motion)

```css
/* 애플 시그니처 ease — 모든 카드/버튼/사이드바 전환 */
.apple-transition { transition: all .3s cubic-bezier(.25, 1, .5, 1); }
```
- 엔트런스(Framer/motion): `initial={{opacity:0, y:20}} → animate={{opacity:1, y:0}}` `duration: .4`.
- 스태거: 리스트/그리드는 `delay: idx * 0.05`.
- 카드 등장(다이얼로그): `scale:.95 → 1` + `backdrop-blur-sm` 오버레이.
- 떠 있는 인시던트 바: `backdrop-blur-md` + `bg-[#18191b]/95`.
- 버튼 press: `transform active:scale-95`.

---

## 7. 컴포넌트 카탈로그 (verbatim recipes)

### 7.1 KPI 카드 (Metric Card)
```
컨테이너: rounded-[18px] p-5 h-[185px] border flex flex-col justify-between overflow-hidden
          (dark) bg-[#1e2022] border-white/5   (light) bg-white border-[#e0e0e0]
상단 메타: flex items-center justify-between mb-2
  라벨:   text-[11px] font-bold tracking-tight uppercase font-mono   (muted)
  아이콘: h-4 w-4 opacity-80
값:       flex items-baseline space-x-1
  숫자:   text-[34px] font-semibold tracking-tight font-sans leading-none
          (이상치) text-red-500 font-bold
  단위:   text-xs font-semibold
델타 행:  mt-2 flex items-center justify-between z-10
  설명:   text-[10px] font-mono truncate max-w-[110px]
스파크라인: absolute bottom-0 left-0 right-0 h-11 opacity-40 pointer-events-none
이상치 카드 box-shadow: rgba(239,68,68,.1) 0px 10px 30px
```

### 7.2 검색창 / 입력 (Search · Select · Textarea)
**검색창(알약)** — 기본 + 포커스, 양 테마:
```
공통: w-full rounded-full py-2.5 pl-10 pr-4 text-xs font-mono outline-none apple-transition border
Dark  기본:   bg-white/5  border-white/10  text-white  placeholder-white/20
Dark  포커스: focus:border-[#2997ff] focus:ring-1 focus:ring-[#2997ff]
Light 기본:   bg-[#f5f5f7] border-[#e0e0e0] text-[#1d1d1f] placeholder-black/30
Light 포커스: focus:bg-white focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc]
```
**셀렉트**: `text-xs font-semibold py-1 pl-2.5 pr-8 rounded-md border appearance-none outline-none
focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc]` + chevron 오버레이 `opacity-60`.
(dark `bg-[#222529] border-white/10` · light `bg-white border-[#e0e0e0]`)
**쿼리 텍스트에어리어**: `rounded-lg font-mono text-xs`, 다크 `bg-[#151617] text-teal-400`,
라이트 `bg-[#fafafc] text-[#0066cc]`.

### 7.3 버튼 (Buttons)
```
Primary(CTA):  bg-[#0066cc] text-white px-4 py-2 rounded-full text-xs font-semibold
               hover:bg-[#0071e3] transition-colors transform active:scale-95
Secondary:     px-4 py-2 rounded-full text-xs font-semibold
               (dark) bg-white/5 border-white/10 text-white hover:bg-white/10
               (light) bg-white border-[#e0e0e0] text-[#1d1d1f] hover:bg-black/5
Flat:          text-xs font-semibold hover:bg-black/5 dark:hover:bg-white/5
Segment(pill군): wrapper flex p-0.5 rounded-full (light bg-[#e0e0e0]/50 · dark bg-white/5)
   active:   px-3 py-1 text-xs rounded-full font-medium bg-white text-[#1d1d1f] shadow-sm
   inactive: px-3 py-1 text-xs rounded-full font-medium text-[#7a7a7a] hover:text-[#1d1d1f]
Icon-only:     p-1.5 rounded-full hover:bg-white/5 text-white/60 transition-colors
```

### 7.4 사이드바 (Grafana Identity)
```
컨테이너: shrink-0 border-r h-full flex flex-col justify-between (w-64 ↔ w-16)
          (dark) bg-[#18191b] border-white/5  (light) bg-[#fafafc] border-[#e0e0e0]
로고:     w-8 h-8 rounded-lg shadow-md p-1.5
          bg-gradient-to-tr from-[#ff4a00] via-[#ff7c00] to-[#ffb800]  (Flame 아이콘 white)
브랜드텍스트: text-[13px] font-bold tracking-tight
서브텍스트:   text-[10px] font-mono text-[#0066cc] font-semibold uppercase tracking-wider
메뉴 아이템:  w-full flex items-center justify-between p-2.5 rounded-lg text-xs font-medium apple-transition
   active(dark):  bg-white/10 text-white
   active(light): bg-[#0066cc]/10 text-[#0066cc]
   hover:        hover:bg-white/5 (dark) · hover:bg-black/5 (light)
배지:     text-[10px] px-1.5 py-0.5 rounded-full font-bold font-mono uppercase
          (alert) bg-red-500 text-white animate-pulse
접힘 툴팁: absolute left-16 px-3 py-1.5 rounded-md text-[11px] font-semibold shadow-xl border z-50
          (dark) bg-[#1d1d1f] border-white/10 text-white  (light) bg-white border-[#e0e0e0]
푸터 아바타: w-8 h-8 rounded-full bg-[#0066cc] text-white font-bold text-xs shadow-inner
```

### 7.5 다이얼로그 · 이상치 배너 · 떠있는 바
```
다이얼로그 오버레이: fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4
다이얼로그 본문:     rounded-[18px] p-6 max-w-md w-full border  (cardBg)  + scale .95→1
이상치 배너: rounded-[18px] p-5 flex items-start justify-between
   (dark) bg-red-950/20 border-red-900/30  (light) bg-red-50 border-red-200
   타이틀 text-sm font-semibold text-red-800 dark:text-red-400
   아이콘 p-1.5 bg-red-100 dark:bg-red-950 rounded-full animate-pulse
떠있는 인시던트 바: fixed bottom-6 left-1/2 -translate-x-1/2 max-w-lg rounded-full px-6 py-3
   bg-[#18191b]/95 backdrop-blur-md border border-red-500/30 shadow-2xl
   + ping 도트 flex h-2 w-2 rounded-full bg-red-500 animate-ping
```

---

## 8. 차트 & 데이터 시각화 (Recharts)

차트 타입: **AreaChart**(트래픽+그라데이션 면적), **LineChart**(네트워크 대역폭), KPI **스파크라인**.

### 8.1 그리드 (CartesianGrid)
```tsx
<CartesianGrid strokeDasharray="3 3" vertical={false}
  stroke={isDark ? "rgba(255,255,255,0.05)" : "#f0f0f0"} />
```

### 8.2 축 (XAxis / YAxis)
```tsx
stroke={isDark ? "rgba(255,255,255,0.3)" : "rgba(29,29,31,0.45)"}
fontSize={10}  fontFamily="var(--font-mono)"  tickLine={false}  axisLine={false}
// XAxis dy={10}, YAxis dx={-5}(좌)/dx={5}(우). 이중축: yAxisId="left"/"right".
```

### 8.3 커스텀 툴팁 (CustomTooltip)
```
래퍼: p-3 rounded-lg shadow-xl font-sans text-xs border
  (dark) bg-[#18191b] border-white/10 text-white
  (light) bg-white border-[#e0e0e0] text-[#1d1d1f]
라벨: font-mono mb-1.5  (dark text-[#7a7a7a] · light text-[#86868b])
항목: 좌측 컬러 도트 w-1.5 h-1.5 rounded-full(시리즈색) + 이름(text-*/80)
      우측 값 font-mono font-semibold  →  value.toLocaleString() + unit
```

### 8.4 면적 그라데이션 (signature "연기처럼 녹아듦")
```tsx
// 메인 면적
<linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
  <stop offset="5%"  stopColor={isDark ? '#2997ff' : '#0066cc'} stopOpacity={0.2} />
  <stop offset="95%" stopColor={isDark ? '#2997ff' : '#0066cc'} stopOpacity={0.0} />
</linearGradient>
// KPI 스파크라인
<linearGradient id={`gradient-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
  <stop offset="0%"   stopColor={color} stopOpacity={0.3} />
  <stop offset="100%" stopColor={color} stopOpacity={0.0} />
</linearGradient>
```

### 8.5 시리즈 (Area / Line)
- 공통: `strokeWidth={2} dot={false} type="monotone"`, 면적은 `fillOpacity={1} fill="url(#...)"`.
- Requests(area) `#2997ff`/`#0066cc` · DB latency(line) `#a855f7` · Net-in `#10b981` · Net-out `#f59e0b`.
- 범례는 별도 렌더 대신 카드 푸터에 수동 도트(`w-2.5 h-2.5 rounded-full`)+라벨.
- 마진 예: 메인 `{top:10,right:10,left:-20,bottom:0}`. 활성 데이터 = `history.slice(-40)`, 스파크라인 `-20`.

---

## 9. 상태 (Interactive States)

| 상태 | 처리 |
| :--- | :--- |
| **focus** | `focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc]` (입력 공통) |
| **hover** | 표면 `hover:bg-white/5`(dark)·`hover:bg-black/5`(light); CTA `hover:bg-[#0071e3]` |
| **press** | `transform active:scale-95` |
| **selected** | 카드 `ring-2 ring-[#0066cc] border-transparent` |
| **anomaly** | 값·테두리·도트가 빨강(`#ef4444`)으로 시프트 + `animate-pulse`/`animate-ping` + spike 그림자 |
| **disabled/faint** | placeholder `*/20~30`, 아이콘 `opacity-60` |

---

## 부록 A — Reflex 구현 매핑 (`--am-*` CSS Variables)

실제 앱은 **Reflex(Python) + Radix Themes**이며 `assets/styles.css`의 기존 `--ks-*`는 **다크
전용 SCADA 아쿠아 팔레트**(`--ks-aqua #36E2C0`, `--ks-ink #0A1018` …)로 Apple-mode와 색·구조가
다르고 라이트 스코프가 없다. 따라서 충돌을 피해 **별도 `--am-*` 토큰 세트**를 신설한다.
(이 부록은 사양·매핑일 뿐 — `styles.css`/앱 코드는 이 작업에서 수정하지 않는다. 향후 구현자가
아래를 그대로 추가하면 된다.)

### A.1 토큰 정의 — 라이트는 `:root`, 다크는 `[data-theme="dark"]`
```css
:root {                                  /* LIGHT (기본) */
  --am-page:#f5f5f7; --am-card:#ffffff; --am-card-2:#ffffff;
  --am-header:#fafafc; --am-row:#fafafc; --am-select:#ffffff; --am-console:#fafafc;
  --am-text:#1d1d1f; --am-muted:#7a7a7a; --am-muted-2:#86868b; --am-faint:rgba(0,0,0,.3);
  --am-accent:#0066cc; --am-accent-press:#0071e3; --am-focus:#0066cc;
  --am-border:#e0e0e0; --am-border-strong:#e0e0e0; --am-hairline:#f0f0f0;
  --am-error:#ef4444; --am-warning:#f59e0b; --am-success:#10b981; --am-info:#0066cc;
  --am-series-a:#0066cc; --am-series-violet:#a855f7; --am-series-emerald:#10b981;
  --am-series-amber:#f59e0b; --am-series-alarm:#ef4444;
  --am-grid:#f0f0f0; --am-axis:rgba(29,29,31,.45);
  --am-r-card:18px; --am-r-card-2:16px; --am-r-lg:8px; --am-r-input:6px; --am-r-pill:9999px;
  --am-ease:cubic-bezier(.25,1,.5,1); --am-dur:.3s;
  --am-font-sans:"Inter",ui-sans-serif,system-ui,sans-serif;
  --am-font-mono:"JetBrains Mono",ui-monospace,SFMono-Regular,monospace;
  --am-brand:linear-gradient(to top right,#ff4a00,#ff7c00,#ffb800);
}
[data-theme="dark"] {                    /* DARK */
  --am-page:#111214; --am-card:#18191b; --am-card-2:#1e2022;
  --am-header:#18191b; --am-row:#151617; --am-select:#222529; --am-console:rgba(0,0,0,.45);
  --am-text:#ffffff; --am-muted:rgba(255,255,255,.6); --am-muted-2:rgba(255,255,255,.4);
  --am-faint:rgba(255,255,255,.3);
  --am-accent:#2997ff; --am-info:#2997ff;
  --am-border:rgba(255,255,255,.05); --am-border-strong:rgba(255,255,255,.1);
  --am-hairline:rgba(255,255,255,.05);
  --am-series-a:#2997ff; --am-grid:rgba(255,255,255,.05); --am-axis:rgba(255,255,255,.3);
}
```

### A.2 Reflex 사용 패턴
Reflex 컴포넌트는 `style=` dict 또는 `color=`/`bg=` prop에 **CSS 변수 문자열**을 그대로 넘긴다
(기존 `kpi_tile.py`가 `color="var(--ks-text)"`, `bg=scheme["bg"]`를 쓰는 방식과 동일).
```python
import reflex as rx

def am_card(*children, raised: bool = False) -> rx.Component:
    return rx.box(
        *children,
        style={
            "background": "var(--am-card-2)" if raised else "var(--am-card)",
            "border": "1px solid var(--am-border)",
            "borderRadius": "var(--am-r-card)",   # 18px
            "padding": "1.25rem",                  # p-5
            "transition": "all var(--am-dur) var(--am-ease)",
        },
    )

# 다크/라이트 토글: <html data-theme="dark"> 속성만 바꾸면 전 토큰이 뒤집힘
# (참조 앱의 isDark 분기를 CSS 변수 스코프로 대체 — 컴포넌트는 색을 모름)
```

### A.3 Tailwind 레시피 → Reflex 매핑 표

| Tailwind (참조) | `--am-*` / Reflex style |
| :--- | :--- |
| `bg-[#18191b]` / `bg-white` | `background: var(--am-card)` |
| `bg-[#1e2022]` (raised) | `background: var(--am-card-2)` |
| `text-white` / `text-[#1d1d1f]` | `color: var(--am-text)` |
| `text-white/60` / `text-[#7a7a7a]` | `color: var(--am-muted)` |
| `border-white/5` / `border-[#e0e0e0]` | `border: 1px solid var(--am-border)` |
| `text-[#2997ff]` / `text-[#0066cc]` | `color: var(--am-accent)` |
| `rounded-[18px]` | `borderRadius: var(--am-r-card)` |
| `rounded-full` | `borderRadius: var(--am-r-pill)` |
| `focus:ring-[#0066cc]` | `boxShadow: 0 0 0 1px var(--am-focus)` (focus 시) |
| `bg-red-500/10 text-red-500` | `background: color-mix(in srgb, var(--am-error) 10%, transparent); color: var(--am-error)` |
| `apple-transition` | `transition: all var(--am-dur) var(--am-ease)` |

> 시각 검증용 렌더는 `designs/design_guide_preview.html` 참조 — 위 `--am-*` 값과 1:1 동기화.
