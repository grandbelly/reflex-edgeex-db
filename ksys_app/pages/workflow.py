"""공정 워크플로우 페이지 — PLC 수집 → 시뮬레이션 → PLC 제어 (closed loop).

frontend-design(Anthropic) 적용. 제어실 계기판 테마. 시각화 본문은 정적
SVG/CSS(스크립트 비의존)로 렌더 — 계측값은 운영 DB 실측 스냅샷.
라이브 바인딩은 후속(State 연결)으로 확장 가능.
"""
import reflex as rx
from ..components.layout import shell


# ── 운영 DB 실측 스냅샷 (ksys-dev-db, 2026-06-17 13:11 KST) ──
# gauge fill % = (v-lo)/(hi-lo)*100
_VIZ_HTML = r"""
<style>
.wfviz{--aqua:#36E2C0;--flow:#4DA3FF;--amber:#FFB454;--alarm:#FF566E;
  --haze:#8DA2C0;--text:#E8F0FA;--panel:#13212F;--panel-2:#192D40;
  --line:rgba(141,162,192,.16);--line-2:rgba(141,162,192,.30);
  --fd:"Space Grotesk",system-ui,sans-serif;--fb:"Inter",system-ui,sans-serif;--fm:"IBM Plex Mono",ui-monospace,monospace;
  color:var(--text);font-family:var(--fb);padding:6px 4px 40px;max-width:1180px;margin:0 auto}
.wfviz *{box-sizing:border-box}
.wfviz .eyebrow{font-family:var(--fm);font-size:12px;letter-spacing:.3em;text-transform:uppercase;color:var(--aqua);display:flex;align-items:center;gap:12px}
.wfviz .eyebrow::before{content:"";width:30px;height:1px;background:var(--aqua);opacity:.7}
.wfviz h1{font-family:var(--fd);font-weight:600;font-size:clamp(26px,4vw,42px);line-height:1.06;letter-spacing:-.5px;margin:16px 0 0}
.wfviz h1 em{font-style:normal;color:var(--aqua)} .wfviz h1 .c{color:var(--amber)}
.wfviz .lede{max-width:680px;color:#AFC0D6;font-size:16px;margin:16px 0 0}
.wfviz .lede b{color:var(--text);font-weight:600}
.wfviz .pillrow{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}
.wfviz .pill{display:inline-flex;align-items:center;gap:7px;font-family:var(--fm);font-size:11.5px;color:#AFC0D6;padding:6px 11px;border:1px solid var(--line);border-radius:999px;background:rgba(25,45,64,.4)}
.wfviz .ld{width:7px;height:7px;border-radius:50%;background:var(--aqua);box-shadow:0 0 0 0 rgba(54,226,192,.6);animation:wfbeat 2.4s ease-out infinite}
@keyframes wfbeat{0%{box-shadow:0 0 0 0 rgba(54,226,192,.5)}70%{box-shadow:0 0 0 7px rgba(54,226,192,0)}100%{box-shadow:0 0 0 0 rgba(54,226,192,0)}}
.wfviz .sec-head{display:flex;align-items:baseline;gap:14px;margin:42px 0 20px}
.wfviz .sec-num{font-family:var(--fm);font-size:12px;color:var(--haze)}
.wfviz .sec-head h2{font-family:var(--fd);font-weight:600;font-size:21px;margin:0;letter-spacing:-.2px}
.wfviz .sec-head p{margin:0 0 0 auto;color:var(--haze);font-size:12.5px;font-family:var(--fm)}

.wfviz .loopstage{position:relative;border:1px solid var(--line);border-radius:20px;background:linear-gradient(180deg,rgba(19,33,47,.55),rgba(14,23,36,.55));padding:34px 24px 24px;overflow:hidden}
.wfviz .loopstage::before{content:"공정 제어 루프 · PROCESS CONTROL LOOP";position:absolute;top:14px;left:24px;font-family:var(--fm);font-size:10.5px;letter-spacing:.22em;color:var(--haze)}
.wfviz .flowrow{display:flex;align-items:stretch;margin-top:24px;position:relative;z-index:2}
.wfviz .station{flex:1 1 0;min-width:0;display:flex}
.wfviz .pipe{flex:0 0 42px;align-self:center;position:relative;height:3px;margin-top:8px}
.wfviz .pipe::before{content:"";position:absolute;inset:0;border-radius:3px;background:linear-gradient(90deg,var(--flow),var(--aqua));opacity:.3}
.wfviz .pipe::after{content:"";position:absolute;inset:0;border-radius:3px;background:linear-gradient(90deg,transparent,var(--aqua) 40%,#bafff0 50%,var(--aqua) 60%,transparent);background-size:200% 100%;animation:wfflow 1.9s linear infinite}
@keyframes wfflow{0%{background-position:120% 0}100%{background-position:-120% 0}}
.wfviz .card{position:relative;border:1px solid var(--line);border-radius:14px;background:var(--panel);padding:17px 15px 15px;width:100%;transition:transform .25s,border-color .25s}
.wfviz .card:hover{transform:translateY(-4px);border-color:var(--line-2)}
.wfviz .card .top{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.wfviz .glyph{width:42px;height:42px;border-radius:11px;display:grid;place-items:center;background:rgba(141,162,192,.08);border:1px solid var(--line)}
.wfviz .sidx{font-family:var(--fm);font-size:10.5px;color:var(--haze)}
.wfviz .card h3{font-family:var(--fd);font-weight:600;font-size:15px;margin:0 0 2px}
.wfviz .card .en{font-family:var(--fm);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--haze)}
.wfviz .card .desc{font-size:12px;color:#AFC0D6;margin:10px 0 12px;min-height:54px}
.wfviz .metric{font-family:var(--fm);font-size:11.5px;color:var(--text);padding-top:10px;border-top:1px solid var(--line)}
.wfviz .metric .k{color:var(--haze)}
.wfviz .t-flow .glyph{background:rgba(77,163,255,.1);border-color:rgba(77,163,255,.35)} .wfviz .t-flow{border-top:2px solid var(--flow)}
.wfviz .t-haze{border-top:2px solid var(--haze)}
.wfviz .t-alarm .glyph{background:rgba(255,86,110,.1);border-color:rgba(255,86,110,.35)} .wfviz .t-alarm{border-top:2px solid var(--alarm)}
.wfviz .t-aqua .glyph{background:rgba(54,226,192,.1);border-color:rgba(54,226,192,.35)} .wfviz .t-aqua{border-top:2px solid var(--aqua)}
.wfviz .t-amber .glyph{background:rgba(255,180,84,.1);border-color:rgba(255,180,84,.35)} .wfviz .t-amber{border-top:2px solid var(--amber)}
.wfviz .feedback{position:relative;margin-top:6px;height:72px;z-index:1}
.wfviz .feedback svg{width:100%;height:100%;overflow:visible}
.wfviz .fb-label{position:absolute;left:50%;bottom:6px;transform:translateX(-50%);font-family:var(--fm);font-size:11px;color:var(--amber);letter-spacing:.16em;background:#0A1018;padding:2px 12px;border:1px solid rgba(255,180,84,.3);border-radius:999px}

.wfviz .grid{display:grid;gap:14px}
.wfviz .inst{grid-template-columns:repeat(auto-fit,minmax(186px,1fr))}
.wfviz .gauge{border:1px solid var(--line);border-radius:14px;background:var(--panel-2);padding:15px}
.wfviz .gauge .gtop{display:flex;justify-content:space-between;align-items:baseline}
.wfviz .gauge .name{font-family:var(--fm);font-size:11px;letter-spacing:.06em;color:#AFC0D6}
.wfviz .gauge .ko{font-size:11px;color:var(--haze)}
.wfviz .gauge .val{font-family:var(--fm);font-weight:600;font-size:25px;margin:7px 0 1px;letter-spacing:-.5px}
.wfviz .gauge .unit{font-family:var(--fm);font-size:11.5px;color:var(--haze);margin-left:5px;font-weight:400}
.wfviz .track{height:6px;border-radius:6px;background:rgba(141,162,192,.14);margin-top:12px;position:relative;overflow:hidden}
.wfviz .fill{position:absolute;inset:0 auto 0 0;border-radius:6px;background:linear-gradient(90deg,var(--flow),var(--aqua));animation:wfgrow 1.1s ease-out}
@keyframes wfgrow{from{width:0}}
.wfviz .rng{display:flex;justify-content:space-between;font-family:var(--fm);font-size:10px;color:var(--haze);margin-top:6px}
.wfviz .kpi{grid-template-columns:repeat(auto-fit,minmax(208px,1fr));margin-top:14px}
.wfviz .kcard{border:1px solid var(--line);border-radius:14px;padding:17px 17px 15px;background:linear-gradient(160deg,rgba(54,226,192,.07),rgba(19,33,47,.5))}
.wfviz .kcard.amb{background:linear-gradient(160deg,rgba(255,180,84,.08),rgba(19,33,47,.5))}
.wfviz .kcard .kk{font-family:var(--fm);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--haze)}
.wfviz .kcard .kv{font-family:var(--fm);font-weight:600;font-size:32px;margin:7px 0 2px;letter-spacing:-1px;color:var(--aqua)}
.wfviz .kcard .kv.amber{color:var(--amber)}
.wfviz .kcard .kd{font-size:12px;color:#AFC0D6}

.wfviz .stage-list{display:grid;border:1px solid var(--line);border-radius:18px;overflow:hidden}
.wfviz .srow{display:grid;grid-template-columns:60px 1.1fr 1.5fr 1fr;gap:16px;padding:18px 20px;border-bottom:1px solid var(--line);align-items:start;transition:background .2s}
.wfviz .srow:last-child{border-bottom:none}
.wfviz .srow:hover{background:rgba(25,45,64,.34)}
.wfviz .srow .ring{width:36px;height:36px;border-radius:50%;border:1px solid var(--line-2);display:grid;place-items:center;font-family:var(--fm);font-size:13px;color:var(--text)}
.wfviz .srow h4{font-family:var(--fd);font-weight:600;font-size:15px;margin:0 0 3px}
.wfviz .srow .en2{font-family:var(--fm);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--haze)}
.wfviz .srow p{margin:0;font-size:12.5px;color:#AFC0D6}
.wfviz .srow p b{color:var(--text)}
.wfviz .chips{display:flex;flex-wrap:wrap;gap:6px}
.wfviz .chip{font-family:var(--fm);font-size:10px;color:#AFC0D6;padding:3px 8px;border:1px solid var(--line);border-radius:6px;background:rgba(141,162,192,.06)}
.wfviz .chip.r{color:var(--aqua);border-color:rgba(54,226,192,.3)}
.wfviz .legend{display:flex;flex-wrap:wrap;gap:20px;padding:18px 20px;border:1px solid var(--line);border-radius:14px;background:#0E1724;font-size:12.5px;color:#AFC0D6;margin-top:14px}
.wfviz .legend .li{display:flex;align-items:center;gap:9px}
.wfviz .sw{width:26px;height:6px;border-radius:6px}
.wfviz .prov{margin-top:24px;padding-top:16px;border-top:1px solid var(--line);color:var(--haze);font-size:11.5px;font-family:var(--fm);display:flex;flex-wrap:wrap;gap:6px 20px}
.wfviz .prov .lv{color:var(--aqua)}
@media (max-width:880px){
  .wfviz .flowrow{flex-direction:column}
  .wfviz .pipe{width:3px;height:28px;margin:2px 0 2px 28px;flex-basis:28px}
  .wfviz .pipe::before{background:linear-gradient(180deg,var(--flow),var(--aqua))}
  .wfviz .pipe::after{background:linear-gradient(180deg,transparent,var(--aqua) 45%,#bafff0 50%,var(--aqua) 55%,transparent);background-size:100% 200%;animation:wfflowv 1.9s linear infinite}
  @keyframes wfflowv{0%{background-position:0 120%}100%{background-position:0 -120%}}
  .wfviz .feedback{display:none}
  .wfviz .srow{grid-template-columns:46px 1fr}
  .wfviz .srow .c3,.wfviz .srow .c4{grid-column:2}
}
@media (prefers-reduced-motion:reduce){.wfviz *{animation:none!important;transition:none!important}}
</style>

<div class="wfviz">
  <div class="eyebrow">현장에서 제어까지 · 단일 폐루프</div>
  <h1>역삼투 정수 플랜트의<br><em>데이터</em>는 흐르고, <span class="c">제어</span>로 되돌아온다</h1>
  <p class="lede">PLC가 읽은 압력·전도도·유량이 엣지 저장소와 AI 예측을 거쳐 다시 펌프와 밸브로 돌아가는 전 과정 —
  <b>수집 → 시뮬레이션 → 제어</b>의 닫힌 루프. 아래 계측값은 운영 DB의 실측 스냅샷입니다.</p>
  <div class="pillrow">
    <span class="pill"><span class="ld"></span> DB ONLINE · ksys-dev-db</span>
    <span class="pill">100 TAGS · 807,351 ROWS</span>
    <span class="pill">SNAPSHOT 2026-06-17 13:11 KST</span>
  </div>

  <div class="sec-head"><span class="sec-num">01</span><h2>공정 워크플로우 루프</h2><p>forward = 데이터 · feedback = 제어</p></div>
  <div class="loopstage">
    <div class="flowrow">
      <div class="station"><div class="card t-flow">
        <div class="top"><div class="glyph"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="9" r="6" stroke="#4DA3FF" stroke-width="1.6"/><path d="M12 9 L15 6" stroke="#4DA3FF" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="9" r="1.4" fill="#4DA3FF"/><path d="M12 15 V21 M8 21 H16" stroke="#4DA3FF" stroke-width="1.6" stroke-linecap="round"/></svg></div><span class="sidx">STAGE 01</span></div>
        <h3>현장 수집</h3><div class="en">PLC Acquisition</div>
        <div class="desc">PLC가 압력·전도도·유량 센서를 폴링해 원시 시계열을 수집. 통신 성공률을 함께 감시.</div>
        <div class="metric"><span class="k">태그</span> 100 · <span class="k">폴링</span> 5 s</div>
      </div></div>
      <div class="pipe"></div>
      <div class="station"><div class="card t-haze">
        <div class="top"><div class="glyph"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><ellipse cx="12" cy="5.5" rx="7" ry="2.6" stroke="#8DA2C0" stroke-width="1.5"/><path d="M5 5.5 V12 C5 13.4 8.1 14.6 12 14.6 C15.9 14.6 19 13.4 19 12 V5.5" stroke="#8DA2C0" stroke-width="1.5"/><path d="M5 12 V18.5 C5 19.9 8.1 21 12 21 C15.9 21 19 19.9 19 18.5 V12" stroke="#8DA2C0" stroke-width="1.5"/></svg></div><span class="sidx">STAGE 02</span></div>
        <h3>저장 · 집계</h3><div class="en">Edge · TimescaleDB</div>
        <div class="desc">하이퍼테이블에 적재하고 연속집계(1m·10m·1h·1d)로 다운샘플 — 트렌드·예측의 공통 기반.</div>
        <div class="metric"><span class="k">rows</span> 807K · <span class="k">cagg</span> ×4</div>
      </div></div>
      <div class="pipe"></div>
      <div class="station"><div class="card t-alarm">
        <div class="top"><div class="glyph"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M3 14 H8 L10.5 7 L13.5 18 L16 12 H21" stroke="#FF566E" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 9 H21" stroke="#FF566E" stroke-width="1.2" stroke-dasharray="2 2.5" opacity=".65"/></svg></div><span class="sidx">STAGE 03</span></div>
        <h3>품질 · 알람</h3><div class="en">QC &amp; SCADA Alarm</div>
        <div class="desc">QC 임계값으로 매 샘플을 판정해 warning·critical 발화하고 이력으로 누적.</div>
        <div class="metric"><span class="k">rule</span> 임계 5종 · <span class="k">level</span> 2</div>
      </div></div>
      <div class="pipe"></div>
      <div class="station"><div class="card t-aqua">
        <div class="top"><div class="glyph"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M3 16 C6 16 7 8 10 8 C12 8 12.5 12 14 12" stroke="#36E2C0" stroke-width="1.7" fill="none" stroke-linecap="round"/><path d="M14 12 C16 12 17 6 21 6" stroke="#36E2C0" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-dasharray="2.5 2.5"/><circle cx="14" cy="12" r="1.8" fill="#36E2C0"/><circle cx="21" cy="6" r="1.8" stroke="#36E2C0" stroke-width="1.5"/></svg></div><span class="sidx">STAGE 04</span></div>
        <h3>AI 예측 · 시뮬레이션</h3><div class="en">Forecast Engine</div>
        <div class="desc">학습 마법사로 모델을 만들고 스케줄러가 5분 주기로 예측 — 운영값의 다음 거동을 시뮬레이션.</div>
        <div class="metric"><span class="k">horizon</span> 5 m · <span class="k">RAG</span> on</div>
      </div></div>
      <div class="pipe"></div>
      <div class="station"><div class="card t-amber">
        <div class="top"><div class="glyph"><svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M4 10 L10 6 L10 14 Z" stroke="#FFB454" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M20 10 L14 6 L14 14 Z" stroke="#FFB454" stroke-width="1.6" fill="none" stroke-linejoin="round"/><path d="M10 10 H14 M12 10 V18 M8 18 H16" stroke="#FFB454" stroke-width="1.6" stroke-linecap="round"/></svg></div><span class="sidx">STAGE 05</span></div>
        <h3>제어 출력</h3><div class="en">PLC Writeback</div>
        <div class="desc">예측·알람을 근거로 펌프 속도·농축수 밸브·약품 주입 셋포인트를 PLC에 기록해 공정을 보정.</div>
        <div class="metric"><span class="k">setpoint</span> VFD · 밸브 · 주입</div>
      </div></div>
    </div>
    <div class="feedback">
      <svg viewBox="0 0 1000 72" preserveAspectRatio="none">
        <path id="wffb" d="M955 0 C955 50 955 58 880 58 L120 58 C45 58 45 50 45 6" fill="none" stroke="url(#wffbg)" stroke-width="2.4" stroke-dasharray="7 7"/>
        <defs><linearGradient id="wffbg" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#FFB454"/><stop offset="1" stop-color="#FFB454" stop-opacity=".35"/></linearGradient></defs>
        <polygon points="45,10 41,2 49,2" fill="#FFB454"/>
        <circle r="3.6" fill="#FFB454"><animateMotion dur="3.4s" repeatCount="indefinite" keyPoints="1;0" keyTimes="0;1" calcMode="linear"><mpath href="#wffb"/></animateMotion></circle>
      </svg>
      <span class="fb-label">제어 피드백 → 현장 (closed loop)</span>
    </div>
  </div>

  <div class="sec-head"><span class="sec-num">02</span><h2>실시간 공정 계측</h2><p>운영 DB 실측 · 2026-06-17</p></div>
  <div class="grid inst">
    <div class="gauge"><div class="gtop"><span class="name">INLET_PRESSURE</span><span class="ko">막 인입압</span></div><div class="val">3.73<span class="unit">bar</span></div><div class="track"><div class="fill" style="width:32.9%"></div></div><div class="rng"><span>3.5</span><span>운영범위</span><span>4.2</span></div></div>
    <div class="gauge"><div class="gtop"><span class="name">FEED_COND</span><span class="ko">유입 전도도</span></div><div class="val">987.8<span class="unit">µS/cm</span></div><div class="track"><div class="fill" style="width:53.9%"></div></div><div class="rng"><span>950</span><span>운영범위</span><span>1020</span></div></div>
    <div class="gauge"><div class="gtop"><span class="name">PRODUCT_COND</span><span class="ko">생산수 전도도</span></div><div class="val">8.64<span class="unit">µS/cm</span></div><div class="track"><div class="fill" style="width:21.3%"></div></div><div class="rng"><span>8.0</span><span>운영범위</span><span>11.0</span></div></div>
    <div class="gauge"><div class="gtop"><span class="name">FEED_FLOW</span><span class="ko">유입 유량</span></div><div class="val">51.27<span class="unit">m³/h</span></div><div class="track"><div class="fill" style="width:81.8%"></div></div><div class="rng"><span>48</span><span>운영범위</span><span>52</span></div></div>
    <div class="gauge"><div class="gtop"><span class="name">PRODUCT_FLOW</span><span class="ko">생산 유량</span></div><div class="val">25.44<span class="unit">m³/h</span></div><div class="track"><div class="fill" style="width:8.8%"></div></div><div class="rng"><span>25</span><span>운영범위</span><span>30</span></div></div>
  </div>
  <div class="grid kpi">
    <div class="kcard"><div class="kk">염 제거율 · Salt Rejection</div><div class="kv">99.1%</div><div class="kd">FEED 987.8 → PRODUCT 8.6 µS/cm. 막 성능 정상 (목표 ≥ 98%).</div></div>
    <div class="kcard"><div class="kk">회수율 · Recovery</div><div class="kv">49.6%</div><div class="kd">PRODUCT 25.4 / FEED 51.3 m³/h. 농축수 25.8 m³/h 배출.</div></div>
    <div class="kcard amb"><div class="kk">막 인입압 · Inlet Pressure</div><div class="kv amber">3.73 bar</div><div class="kd">운영범위 3.5–4.2 bar 내. 제어 셋포인트의 1차 변수.</div></div>
  </div>

  <div class="sec-head"><span class="sec-num">03</span><h2>단계별 동작과 연결 화면</h2><p>각 단계는 앱의 실제 라우트로</p></div>
  <div class="stage-list">
    <div class="srow"><div><div class="ring">1</div></div><div><h4>현장 수집</h4><div class="en2">PLC Acquisition</div></div><div class="c3"><p>PLC가 5초 주기로 필드 센서를 읽어 <b>influx_hist</b> 하이퍼테이블에 적재. 통신 누락은 성공률 히트맵으로 추적.</p></div><div class="c4 chips"><span class="chip">asyncpg</span><span class="chip">influx_hist</span><span class="chip r">/comm</span></div></div>
    <div class="srow"><div><div class="ring">2</div></div><div><h4>저장 · 집계</h4><div class="en2">Edge Storage</div></div><div class="c3"><p>TimescaleDB 연속집계가 1m·10m·1h·1d로 자동 롤업. 트렌드 화면은 구간에 맞춰 집계 레벨을 선택.</p></div><div class="c4 chips"><span class="chip">TimescaleDB</span><span class="chip">cagg ×4</span><span class="chip r">/trend</span></div></div>
    <div class="srow"><div><div class="ring">3</div></div><div><h4>품질 · 알람</h4><div class="en2">QC &amp; Alarm</div></div><div class="c3"><p><b>influx_qc_rule</b> 임계로 각 샘플을 판정해 warning·critical 발화, 알람 이력에 누적하고 실시간 배너로 표시.</p></div><div class="c4 chips"><span class="chip">qc_rule</span><span class="chip">SCADA</span><span class="chip r">/alarms_rt</span><span class="chip r">/alarms_hist</span></div></div>
    <div class="srow"><div><div class="ring">4</div></div><div><h4>AI 예측 · 시뮬레이션</h4><div class="en2">Forecast &amp; Simulation</div></div><div class="c3"><p>학습 마법사로 모델 학습 → 예측 스케줄러가 5분 주기 온라인 예측 생성 → 성능 화면에서 정확도 추적. RAG 챗이 운영 질의에 응답.</p></div><div class="c4 chips"><span class="chip">training</span><span class="chip">forecast</span><span class="chip r">/forecast</span><span class="chip r">/model-performance</span><span class="chip r">/ai</span></div></div>
    <div class="srow"><div><div class="ring" style="border-color:rgba(255,180,84,.5);color:#FFB454">5</div></div><div><h4>제어 출력</h4><div class="en2">PLC Writeback</div></div><div class="c3"><p>예측·알람을 근거로 고압펌프 VFD 속도, 농축수 밸브 개도, 약품 주입률 셋포인트를 산출해 PLC에 기록 — 루프를 닫습니다.</p></div><div class="c4 chips"><span class="chip" style="color:#FFB454;border-color:rgba(255,180,84,.3)">setpoint</span><span class="chip" style="color:#FFB454;border-color:rgba(255,180,84,.3)">VFD · valve · dosing</span></div></div>
  </div>

  <div class="legend">
    <div class="li"><span class="sw" style="background:linear-gradient(90deg,#4DA3FF,#36E2C0)"></span> 정방향 흐름 — 데이터 (수집→집계→예측)</div>
    <div class="li"><span class="sw" style="background:#FFB454"></span> 역방향 흐름 — 제어 피드백 (예측→현장)</div>
    <div class="li"><span class="sw" style="background:#FF566E"></span> 품질 이탈 — 알람</div>
    <div class="li"><span class="sw" style="background:#36E2C0"></span> 정수(permeate) · AI 지능 계층</div>
  </div>
  <div class="prov">
    <span>KSYS RO Workflow · frontend-design 적용</span>
    <span class="lv">● 실측 스냅샷 2026-06-17 13:11:22 KST</span>
    <span>source: ksys-dev-db / influx_hist · 100 tags · 807,351 rows</span>
  </div>
</div>
"""


@rx.page(route="/workflow", title="워크플로우 | KSYS")
def workflow_page() -> rx.Component:
    """PLC 수집 → 시뮬레이션 → PLC 제어 전체 워크플로우 시각화."""
    return shell(
        rx.box(
            rx.html(_VIZ_HTML),
            padding="22px",
            width="100%",
        ),
        active_route="/workflow",
    )
