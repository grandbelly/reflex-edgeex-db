-- ============================================
-- 013_fix_cagg_refresh_policies.sql
-- 재발 방지: influx_agg_* cagg refresh policy의 end_offset 보정
-- ============================================
-- 배경 (2026-06-24 장애):
--   live DB의 refresh policy job들이 end_offset => NULL 로 생성되어 있었음.
--   end_offset NULL + start_offset 만 있는 정책은 매 실행마다 invalidation
--   watermark가 materialization을 앞지르며 달아나, "이미 최신"으로 착각.
--   결과: cagg 집계는 2026-06-18 09:00에서 6일간 정지, 트렌드 페이지
--   "차트 데이터가 없습니다". 수동 CALL refresh_continuous_aggregate 조차
--   "already up-to-date" 로 materialize 거부 → cagg 4종 drop + recreate 로 복구.
--
-- 영구 해법 (2026-06-24, 2축):
--   A) Real-time Aggregate (materialized_only=false): 쿼리 시점에
--      materialized + 최근 raw 를 자동 병합. refresh job이 완전히
--      죽거나 dump의 bad policy 가 복원돼도 최근 데이터가 raw에서
--      실시간 채워져 "빈 차트"가 발생하지 않는다. (구조적 면역)
--   B) 아래 non-null end_offset 정책: refresh job이 정상 가동.
--   복원된 DB에서 어느 쪽이든 멱등하게 강제한다.
-- ============================================

-- A. Real-time Aggregate 로 전환 (refresh 실패에도 차트가 비지 않음)
ALTER MATERIALIZED VIEW influx_agg_1m  SET (timescaledb.materialized_only = false);
ALTER MATERIALIZED VIEW influx_agg_10m SET (timescaledb.materialized_only = false);
ALTER MATERIALIZED VIEW influx_agg_1h  SET (timescaledb.materialized_only = false);
ALTER MATERIALIZED VIEW influx_agg_1d  SET (timescaledb.materialized_only = false);

-- 기존 정책 제거 (잘못된 end_offset=null 정책이 있으면 덮어쓰기 위함)
SELECT remove_continuous_aggregate_policy('influx_agg_1m',  if_exists => true);
SELECT remove_continuous_aggregate_policy('influx_agg_10m', if_exists => true);
SELECT remove_continuous_aggregate_policy('influx_agg_1h',  if_exists => true);
SELECT remove_continuous_aggregate_policy('influx_agg_1d',  if_exists => true);

-- 정확한 end_offset으로 재설정 (migration 09 원래 의도)
-- 1m:  최근 2시간, 끝 1분, 1분마다
SELECT add_continuous_aggregate_policy('influx_agg_1m',
  start_offset => INTERVAL '2 hours',
  end_offset   => INTERVAL '1 minute',
  schedule_interval => INTERVAL '1 minute',
  if_not_exists => true);

-- 10m: 최근 2시간, 끝 10분, 10분마다
SELECT add_continuous_aggregate_policy('influx_agg_10m',
  start_offset => INTERVAL '2 hours',
  end_offset   => INTERVAL '10 minutes',
  schedule_interval => INTERVAL '10 minutes',
  if_not_exists => true);

-- 1h: 최근 7일, 끝 1시간, 1시간마다
SELECT add_continuous_aggregate_policy('influx_agg_1h',
  start_offset => INTERVAL '7 days',
  end_offset   => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour',
  if_not_exists => true);

-- 1d: 최근 30일, 끝 1일, 매일
SELECT add_continuous_aggregate_policy('influx_agg_1d',
  start_offset => INTERVAL '30 days',
  end_offset   => INTERVAL '1 day',
  schedule_interval => INTERVAL '1 day',
  if_not_exists => true);

-- 확인: end_offset이 모두 non-null 이어야 함
\echo '=== 검증: end_offset non-null ==='
SELECT application_name,
       config->>'start_offset' AS start_off,
       config->>'end_offset'   AS end_off
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_refresh_continuous_aggregate'
  AND application_name LIKE '%influx_agg%'
ORDER BY application_name;
