# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🔄 NEW SESSION: 먼저 HANDOFF.md 읽을 것

**이전 Claude 세션이 진행 중이던 작업이 있다면 [HANDOFF.md](./HANDOFF.md)를 가장 먼저 확인.**
환경 셋업 진행 상황, 막힌 지점, 다음 단계, 리팩토링 백로그가 모두 정리돼 있음.

작업 종료 시 다음 세션을 위해 HANDOFF.md를 갱신할 것 (또는 새 핸드오프 작성).

## 🤖 카파시 에이전틱 엔지니어링 체계

이 프로젝트는 **Karpathy 4단계 Agentic Engineering 파이프라인**으로 운영됩니다.
리팩토링/신규 기능 작업 시 단일 LLM에 vibe-coding으로 던지지 말고:

```
/agentic-pipeline <feature-name>
```

체계 전체 매뉴얼: `C:\dev\agent-office\AGENTIC_PIPELINE_MANUAL.md`
Doctrine + 설정 출처: `~/.claude/projects/<this>/memory/reference_karpathy_requirements.md`
시각화 UI: http://localhost (Agent Office 픽셀 오피스, Docker compose)

---

## 🚨🚨🚨 CRITICAL: RPI 풍도 폴더 동기화 정보 🚨🚨🚨

**RPI 서버 작업 시 반드시 확인!**

| 환경 | 경로 |
|------|------|
| **RPI 서버** | `ssh tion@192.168.0.80` |
| **RPI 앱 경로** | `/home/tion/deployment/20251030-rpi-finished/` |
| **로컬 풍도 폴더** | `C:\reflex\reflex-rpi\reflex-rpi-local-deployment-poongdo` |
| **컨테이너** | `rpi-finished-reflex-app`, `rpi-finished-pgai-db` |
| **포트** | 14000 (웹앱) |

```bash
# RPI → 풍도 로컬 동기화
scp tion@192.168.0.80:/home/tion/deployment/20251030-rpi-finished/ksys_app/states/forecast_player_state.py \
    "C:/reflex/reflex-rpi/reflex-rpi-local-deployment-poongdo/ksys_app/states/"

# 풍도 로컬 → RPI 동기화
scp "C:/reflex/reflex-rpi/reflex-rpi-local-deployment-poongdo/ksys_app/states/forecast_player_state.py" \
    tion@192.168.0.80:/home/tion/deployment/20251030-rpi-finished/ksys_app/states/
```

**⚠️ 주의: `reflex-ksys-refactor` 폴더가 아닙니다!**

---

## 배포 명령어

```bash
# RPI 접속
ssh tion@192.168.0.80

# RPI 앱 경로로 이동
cd /home/tion/deployment/20251030-rpi-finished/

# 컨테이너 상태 확인
docker ps | grep rpi-finished

# 앱 재시작
docker restart rpi-finished-reflex-app

# 로그 확인
docker logs rpi-finished-reflex-app -f

# DB 접속
docker exec -it rpi-finished-pgai-db psql -U postgres -d ecoanp
```

## 메인 개발 저장소

자세한 개발 가이드는 `C:\reflex\reflex-ksys-refactor\CLAUDE.md` 참조
