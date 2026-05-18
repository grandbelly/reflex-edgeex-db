# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
