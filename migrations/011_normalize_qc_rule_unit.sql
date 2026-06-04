-- ============================================================================
-- Migration: 011_normalize_qc_rule_unit.sql
-- Description: 스키마 드리프트 정상화 — 코드가 요구하나 복원 DB에 누락된 컬럼 추가
-- Date: 2026-06-04
-- Applies to: RPI, Local
-- Root cause: 풀백업(20251019) 부분복원으로 influx_qc_rule.unit 누락 →
--   sensor_service.get_all_sensors_with_latest 의 SELECT q.unit 가 UndefinedColumnError →
--   _fetch_data 트랜잭션 전체 실패 → 대시보드 "0 센서" (기능 완전 마비).
--   alarms.py / alarm_rt_state.py 도 t.meta->> 참조 → influx_tag.meta 필요.
-- 검증: 적용 후 reflex-app 로그 "Loaded 100 sensors", 대시보드 Normal/Warning/Critical 정상.
-- ============================================================================

-- 코드가 요구하는 컬럼 (없으면 추가, 있으면 skip)
ALTER TABLE influx_qc_rule ADD COLUMN IF NOT EXISTS unit text;
ALTER TABLE influx_tag     ADD COLUMN IF NOT EXISTS meta jsonb;

-- 확인
SELECT 'influx_qc_rule.unit' AS col,
       count(*) FILTER (WHERE column_name='unit') AS exists
  FROM information_schema.columns WHERE table_name='influx_qc_rule'
UNION ALL
SELECT 'influx_tag.meta',
       count(*) FILTER (WHERE column_name='meta')
  FROM information_schema.columns WHERE table_name='influx_tag';
