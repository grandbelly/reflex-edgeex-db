# PR: refactor — 보안 외부화 + spec 역설계 17문서 + dead-code 정리(-3318 LOC) + /ai 활성화

**Base:** master ← **Compare:** refactor/secrets-externalize-day1 (44 commits, 145 files, +39,515/−22,746)

## Summary
44커밋 멀티페이즈 작업. 주요 테마:

**보안 / 외부화 (Day 1-7)**
- 하드코딩 크리덴셜 env 외부화 (sync_monitor, docker-compose `${VAR:?}`/`${VAR:-}`)
- SQLi 차단: RAG 엔진 `_TAG_RE` 화이트리스트(양 브랜치), pg_notify 파라미터화, db_events 채널 검증
- `@event_with_error` 데코레이터 PoC, `.env.example`/`.dockerignore` 추가
- RPI 부트스트랩/복원/베이스라인 스크립트

**Spec 역설계 — 정통 SI 산출물 17문서 (reports/, 전부 HTML)**
- 메뉴/사이트맵 → 스토리보드 → 화면설계(08~11) → 기능명세(12) → 프로세스(13) → 운영(14) → 기획(15) → SRS(16)
- `spec_map.html`: 문서 플로우 DAG + RTM 추적 매트릭스 + orphan 검출

**정합성 #1 — 순번 불일치 해소**
- spec_12 FN 색인 ↔ spec_16 SRS RTM set-diff, FN-ALM-16/TRD-09/SYS-15 backfill
- 색인 오류 0 (ALM/SYS 완전 1:1, DSH/TRD는 DEAD/GAP로 설명)

**정합성 #2 — DEAD 12건 처리 (−3318 LOC)**
- 삭제 7: alarm_state, model_config_state, sync_monitor_state, training_wizard_state_enhanced, legacy DashboardState 패키지, features_table, indicators_table
- /ai 라우트 등록 (FN-AI-01~05 DEAD→live, 사용자 결정)

**/ai 결함 수정 (ship 전 병렬 감사가 발견)**
- get_rag_response 인자 불일치(TypeError) 수정 → 챗 작동
- ai_insights import 부팅 가드 (ENABLE_AI_FEATURES + try/except) → dep 누락 시 사이트 전체 부팅 실패 방지

## Verification (병렬 4차원 감사 — 10 agents, 156 tool calls, 436K tokens)
- **deletion-safety: CLEAN** — 삭제 7파일 잔여 live 참조 0, `python -m compileall ksys_app` EXIT=0
- **import-integrity: CLEAN** — 깨진 import 0, 순환 0, 16 페이지 모듈 전부 @rx.page 보유
- **ai-cluster-health** — /ai 결함 2건 발견 → 수정 완료. ai_engine 17개 엔진 SQLi/RCE 스캔 clean
- 컨테이너 런타임: 15/15 라우트 + /ai 프리렌더, Playwright /ai 렌더 OK

## Known follow-ups (비차단)
- **2차 dead 군집** (residual-dead-code 감사): TagHierarchy Enhanced orphan 3종+base, hierarchical_tag_selector, orphan 서비스 3종, states/data.py(stock mock), stock_chart.py — 전부 confirmed dead(런타임 영향 없음), #2 Phase 4 후속
- **AI 품질**: /ai 챗은 작동하나 실응답 품질은 별도 rework(LLM 키/knowledge_base 테이블, extra_context 프롬프트 주입)
- 🔐 **시크릿 로테이션 필수 (PR 전 선행)**: 외부화 이전 git 히스토리에 Cloudflare 토큰 / upstream DB 크리덴셜 / POSTGRES_PASSWORD / SSH 비번 `!eonware`(commit 879abff, `01_remote_ksys/`) 원본 잔존 — 이미 푸시되어 노출 기정사실, 외부화만으로 불충분하므로 외부 대시보드에서 실제 무효화 필요

🤖 Generated with [Claude Code](https://claude.com/claude-code)
