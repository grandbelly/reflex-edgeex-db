# 303c995 화면 결함 목록과 조치

근거:
- 전 캡처 12장. 엣지 영수증 `fable/receipts/acceptance/20261028T091746+0900__d1028-06-mini-scada-edge-accept/screenshots/menu-*-{1920,1366}.png`, SY 실데이터.
- `audit-before.json`(dashboard-ui-audit 정적 판정).

조치는 화면 계층에서만 했다. 서비스·쿼리·DB·Kafka 계약은 바꾸지 않았다.

| ID | 결함 | 근거 | 조치 | 시험 |
|---|---|---|---|---|
| Q-01 | 대시보드 채널 표 숫자 좌정렬(수용 #4 FAIL) | 범용 `table()`이 숫자를 일반 글자로 출력 | `scada_display.TABLES`에 숫자 열을 명시해 우정렬·고정폭 숫자로 표시. 같은 행의 원시·처리·최종값은 소수 자리를 0으로 채움(반올림 없음) | `NumericAlignment` |
| Q-02 | 1366 표 넘침 73 px(수용 #5 FAIL) | 전역 `.rt-TableRoot{min-width:500px}`이 폭 427 px짜리 4열 옆 칸에도 걸림 | 전역 최소폭 제거, 표마다 최소폭 지정, 12분할 트랙에서 픽셀 최소폭 제거 | `OverflowWidth`(측정값 427·73 재현) |
| Q-03 | Health 표 부재 원인 없음(수용 #7 FAIL) | "채널 Health를 확인할 수 없습니다"만 표시 | `SCHEMA_MISSING`을 원인과 다음 단계 한 줄로 표시 | `test_health_absence_states_cause_in_one_line` |
| Q-04 | 아이콘 빈 상자(최소 높이 190 px), 호출 14곳 | 워크플로우·통신·Edge 캡처 | 사실 한 줄(`note`)로 바꿈. 값이 있는 단계(측정·판단)는 실제 수치 표시 | 캡처 대기 |
| Q-05 | 군말 각주·면책 footer | "…과 구별", footer 고지 | 삭제. 화면 문자열은 80자 이하, 금칙어 없음 | `Wording` |
| Q-06 | 원시 ISO 마이크로초 시각 | 표·조회 기준·상세 | 표는 `10-28 09:27:02`. 상세는 `10-28 09:27:02.038037`(자릿수 유지, `T`·오프셋 제거) | `test_precise_time_keeps_every_digit` |
| Q-07 | 영문 품질어 `UNCERTAIN`, `GOOD/BAD` | 경보 메시지·품질 배지 | 표시 단계에서 양호/불확실/불량으로 바꿈 | `test_alarm_text_uses_ds017_terms` |
| Q-08 | 처리 사유 `["EWMA_APPLIED"]` 원문 | Edge 선택 태그 | `EWMA_APPLIED`로 표시. 빈 목록이면 행 생략 | `test_reasons_and_times_are_readable` |
| Q-09 | 값 없는 상세 행(`—`) 나열, 빈 단위 칸 | 선택 태그·표본·사건 상세 | `facts()`가 모르는 값을 생략. 단위가 없으면 `—`(DS-017) | `test_unknown_values_are_omitted` |
| Q-10 | 토큰이 DS-017과 다름(#0b1018, 파랑 강조) | `audit-before` VIS-02 | DS-017 §11.2·§11.31 토큰. leaf는 선택·초점에만, 정상은 무채색, 불량은 q-bad(0건이면 무채색) | 캡처 대기 |
| Q-11 | 트렌드 품질 계열 구분 약함, 범례 없음 | 트렌드 캡처 | 양호 최종값은 leaf 실선, 불확실은 회색 점선과 점, 원시·처리는 비교 모드에서만. 범례는 카드 하단 | 캡처 대기 |
| Q-12 | 메뉴명 "알람"(DS-017 용어는 경보) | 상단 탐색 | "경보". 경로 `/alarms`는 유지 | `Wording` |

## 설계 해석 지점

- **색.** `designs/`는 배치·밀도·카드·알약 모양만 따른다. emerald "정상"과 파란 강조색은 DS-017 §11.12와 충돌해 쓰지 않는다.
- **경보 우선순위 색.** 원천 `level`을 P1–P3로 대응시킨 계약을 찾지 못했다(시각화 계약·배치 설계 문서 확인). 그래서 경보 알약은 무채색으로 두고 우선순위는 글자로만 보인다. 대응표가 정해지면 `alarm_row`에서 tone만 바꾼다.
- **글자 크기 7종.** VIS-04 FAIL이지만 DS-017 글자 단계(12/13/14/16/20/28/32)를 우선했다. 감사 임계값 6과 상충한다.
- **VIS-02 HEX.** `:root` 토큰 정의와 Recharts SVG 선 색이 잡힌 것이다. SVG 속성은 CSS 변수를 안정적으로 해석하지 못해 `views/scada_view.py`의 `C`에 같은 값을 둔다.

## 감사 전후(dashboard-ui-audit)

- before: pass 20 / partial 7 / fail 8 → after: pass 21 / partial 6 / fail 8.
- 남은 FAIL은 위 해석 지점(VIS-04, VIS-02)과 정적 판정의 한계다. IA-01·DAT-01은 Reflex Python을 정규식으로 읽어서 생기며, 화면 확인은 캡처로 한다.
- 4/8 px 격자 이탈: before 있음 → after 0.
