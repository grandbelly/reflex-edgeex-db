#!/bin/bash
# TimescaleDB 완전 복원 스크립트 (Chunks 포함)
# 생성일: 2025-10-31

set -e

echo "=== Step 1: Terminate existing connections ==="
docker exec rpi-finished-pgai-db psql -U postgres -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'ecoanp' AND pid <> pg_backend_pid();
"

echo "=== Step 2: Drop and recreate database ==="
docker exec rpi-finished-pgai-db psql -U postgres <<EOF
DROP DATABASE IF EXISTS ecoanp;
CREATE DATABASE ecoanp;
EOF

echo "=== Step 3: Install extensions (MUST BE FIRST!) ==="
docker exec rpi-finished-pgai-db psql -U postgres -d ecoanp <<EOF
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_cron CASCADE;
CREATE EXTENSION IF NOT EXISTS plpython3u CASCADE;
CREATE EXTENSION IF NOT EXISTS vector CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_trgm CASCADE;
CREATE EXTENSION IF NOT EXISTS btree_gin CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements CASCADE;
CREATE EXTENSION IF NOT EXISTS pgcrypto CASCADE;
CREATE EXTENSION IF NOT EXISTS plpgsql CASCADE;

-- Verify extensions
\dx
EOF

echo "=== Step 4: Run timescaledb_pre_restore() ==="
docker exec rpi-finished-pgai-db psql -U postgres -d ecoanp -c "
SELECT timescaledb_pre_restore();
"

echo "=== Step 5: Restore database with pg_restore ==="
docker exec rpi-finished-pgai-db pg_restore \
  -U postgres \
  -d ecoanp \
  --verbose \
  --no-owner \
  --no-acl \
  /backup/ecoanp_from_local_20251031.dump 2>&1 | tee /tmp/restore.log

echo "=== Step 6: Run timescaledb_post_restore() ==="
docker exec rpi-finished-pgai-db psql -U postgres -d ecoanp -c "
SELECT timescaledb_post_restore();
"

echo "=== Step 6b: Disable lingering restore mode (cagg refresh killer) ==="
# 복원 후 timescaledb.restoring 이 켜져 있으면 background worker 가 job 을 안 돌려
# cagg 가 멈추고 트렌드 차트가 빈다. 영구 해법의 일부.
docker exec rpi-finished-pgai-db psql -U postgres -d ecoanp <<'EOF'
ALTER DATABASE ecoanp SET timescaledb.restoring = 'off';
SET timescaledb.restoring = 'off';
EOF

echo "=== Step 6c: Normalize caggs (real-time + correct refresh policy) ==="
# dump 가 bad config(end_offset=NULL, materialized_only=true)를 가져와 매 복원마다
# 재발. real-time 전환으로 refresh job 실패에도 차트가 안 비게 하고, 정책을
# non-null end_offset 으로 강제. (migrations/013_fix_cagg_refresh_policies.sql)
docker exec rpi-finished-pgai-db psql -U postgres -d ecoanp -v ON_ERROR_STOP=0 <<'EOF'
ALTER MATERIALIZED VIEW influx_agg_1m  SET (timescaledb.materialized_only = false);
ALTER MATERIALIZED VIEW influx_agg_10m SET (timescaledb.materialized_only = false);
ALTER MATERIALIZED VIEW influx_agg_1h  SET (timescaledb.materialized_only = false);
ALTER MATERIALIZED VIEW influx_agg_1d  SET (timescaledb.materialized_only = false);
SELECT remove_continuous_aggregate_policy('influx_agg_1m',  if_exists => true);
SELECT remove_continuous_aggregate_policy('influx_agg_10m', if_exists => true);
SELECT remove_continuous_aggregate_policy('influx_agg_1h',  if_exists => true);
SELECT remove_continuous_aggregate_policy('influx_agg_1d',  if_exists => true);
SELECT add_continuous_aggregate_policy('influx_agg_1m',  start_offset => INTERVAL '2 hours', end_offset => INTERVAL '1 minute',  schedule_interval => INTERVAL '1 minute',  if_not_exists => true);
SELECT add_continuous_aggregate_policy('influx_agg_10m', start_offset => INTERVAL '2 hours', end_offset => INTERVAL '10 minutes', schedule_interval => INTERVAL '10 minutes', if_not_exists => true);
SELECT add_continuous_aggregate_policy('influx_agg_1h',  start_offset => INTERVAL '7 days',  end_offset => INTERVAL '1 hour',    schedule_interval => INTERVAL '1 hour',    if_not_exists => true);
SELECT add_continuous_aggregate_policy('influx_agg_1d',  start_offset => INTERVAL '30 days', end_offset => INTERVAL '1 day',     schedule_interval => INTERVAL '1 day',     if_not_exists => true);
EOF

echo "=== Step 7: Analyze database ==="
docker exec rpi-finished-pgai-db psql -U postgres -d ecoanp -c "ANALYZE;"

echo "=== Step 8: Verify restoration ==="
docker exec rpi-finished-pgai-db psql -U postgres -d ecoanp <<EOF
-- Check table counts
SELECT
  schemaname,
  relname,
  n_live_tup as row_count
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY n_live_tup DESC
LIMIT 10;

-- Check influx_hist
SELECT COUNT(*) as total_count,
       MIN(ts)::date as earliest,
       MAX(ts)::date as latest
FROM influx_hist;

-- Check chunks
SELECT
  schemaname || '.' || relname as chunk_name,
  n_live_tup as rows
FROM pg_stat_user_tables
WHERE schemaname = '_timescaledb_internal'
  AND relname LIKE '%hyper%'
  AND n_live_tup > 0
ORDER BY n_live_tup DESC
LIMIT 10;
EOF

echo "=== Restoration complete! ==="
