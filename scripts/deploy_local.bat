@echo off
rem Local On-Premise Deployment and Optimization Script for Windows

echo ========================================================
echo 1. Starting Local Database (ksys-dev-db)
echo ========================================================
docker compose -f docker-compose.dev.yml up -d

echo Waiting for database container to be healthy...
:wait_loop
for /f "tokens=*" %%i in ('docker inspect --format="{{.State.Health.Status}}" ksys-dev-db 2^>nul') do set HEALTH=%%i
if "%HEALTH%"=="healthy" goto db_ready
echo Current DB status: "%HEALTH%". Waiting 2 seconds...
timeout /t 2 /nobreak >nul
goto wait_loop

:db_ready
echo Database is ready!

echo Ensuring database "ecoanp" exists...
docker exec -i ksys-dev-db psql -U postgres -c "CREATE DATABASE ecoanp;" >nul 2>&1

echo ========================================================
echo 2. Running database optimization SQL on "ecoanp"
echo ========================================================
docker exec -i ksys-dev-db psql -U postgres -d ecoanp < scripts\db_indexing_strategy.sql

echo ========================================================
echo 3. Starting local containers
echo ========================================================
docker compose -f docker-compose.local.yml up -d --build reflex-app data-injector forecast-scheduler timeseries-pipeline

echo ========================================================
echo 4. Verifying container state
echo ========================================================
docker ps

echo ========================================================
echo 5. Timeseries Pipeline Logs (Press Ctrl+C to stop trailing logs)
echo ========================================================
docker logs ksys-local-timeseries-pipeline
