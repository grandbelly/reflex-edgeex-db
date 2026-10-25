-- ============================================================================
-- CR-EXAT-277 상위 Consumer 엣지 통합 시험용 최소 스키마 (migrations/edge_test_schema.sql)
-- 대상 이미지: timescale/timescaledb:2.28.2-pg16 (빈 DB에 즉시 적용 가능)
-- 특징:
--   1. Consumer가 적재하는 표 5종 생성:
--      - public.influx_tag
--      - public.viewer_tag
--      - public.influx_hist (TimescaleDB hypertable)
--      - public.alarm_history
--      - public.edgeex_vqt_raw (TimescaleDB hypertable)
--   2. 모든 ON CONFLICT 대상 고유 제약(PRIMARY KEY / UNIQUE) 포함
--   3. 완전 멱등(Idempotent): 2회 이상 반복 실행 및 014_create_edgeex_vqt_lossless.sql 후속 실행 시 무오류 보장
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1. public.influx_tag (ON CONFLICT DO NOTHING 대상 고유 제약: key PK, tag_id UNIQUE, tag_name UNIQUE)
CREATE TABLE IF NOT EXISTS public.influx_tag (
    key         TEXT PRIMARY KEY,
    tag_id      TEXT UNIQUE,
    tag_name    TEXT UNIQUE NOT NULL,
    tag_type    TEXT NOT NULL DEFAULT 'analog',
    description TEXT NULL,
    unit        TEXT NULL,
    meta        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. public.viewer_tag (ON CONFLICT (tag_name) DO NOTHING 대상 고유 제약: tag_name PK)
CREATE TABLE IF NOT EXISTS public.viewer_tag (
    tag_name       TEXT PRIMARY KEY,
    display_order  INT NOT NULL DEFAULT 0,
    show_dashboard BOOLEAN NOT NULL DEFAULT TRUE,
    show_alarm     BOOLEAN NOT NULL DEFAULT TRUE,
    show_trend     BOOLEAN NOT NULL DEFAULT TRUE,
    show_model     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. public.influx_hist (ON CONFLICT (ts, tag_name) DO UPDATE 대상 고유 제약: (ts, tag_name) PK)
CREATE TABLE IF NOT EXISTS public.influx_hist (
    ts       TIMESTAMPTZ NOT NULL,
    tag_name TEXT NOT NULL,
    value    DOUBLE PRECISION NOT NULL,
    quality  SMALLINT NOT NULL DEFAULT 0,
    qc       SMALLINT NOT NULL DEFAULT 0,
    meta     JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts, tag_name)
);

SELECT create_hypertable(
    'public.influx_hist',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_influx_hist_tag_ts
    ON public.influx_hist (tag_name, ts DESC);

-- 4. public.alarm_history (ON CONFLICT (event_id, triggered_at) DO UPDATE 대상 고유 제약)
CREATE TABLE IF NOT EXISTS public.alarm_history (
    event_id      VARCHAR(128) NOT NULL,
    scenario_id   VARCHAR(50) NOT NULL DEFAULT 'EDGEEX_ISA18',
    level         SMALLINT NOT NULL DEFAULT 3,
    triggered_at  TIMESTAMPTZ NOT NULL,
    message       TEXT NOT NULL,
    sensor_data   JSONB NOT NULL DEFAULT '{}'::jsonb,
    actions_taken TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    acknowledged  BOOLEAN NOT NULL DEFAULT FALSE,
    resolved      BOOLEAN NOT NULL DEFAULT FALSE,
    ai_generated  BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (event_id, triggered_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_alarm_history_event_triggered_uq
    ON public.alarm_history (event_id, triggered_at);

CREATE INDEX IF NOT EXISTS idx_alarm_triggered_at
    ON public.alarm_history (triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_alarm_sensor_tag
    ON public.alarm_history ((sensor_data->>'tag_name'));

-- 5. public.edgeex_vqt_raw (ON CONFLICT (site_id, tag_id, ts) DO UPDATE 대상 고유 제약: (site_id, tag_id, ts) PK)
CREATE TABLE IF NOT EXISTS public.edgeex_vqt_raw (
    ts             TIMESTAMPTZ NOT NULL,
    site_id        TEXT NOT NULL DEFAULT 'poongdo-edge-01',
    tag_id         TEXT NOT NULL,
    channel        TEXT NOT NULL DEFAULT 'default',
    raw_val        DOUBLE PRECISION NULL,
    cond_val       DOUBLE PRECISION NULL,
    final_val      DOUBLE PRECISION NULL,
    final_quality  SMALLINT NOT NULL DEFAULT 2,
    influx_quality SMALLINT NOT NULL DEFAULT 0,
    integ_class    SMALLINT NOT NULL DEFAULT 0,
    integ_status   TEXT NOT NULL DEFAULT 'NORMAL',
    reasons        JSONB NOT NULL DEFAULT '[]'::jsonb,
    unit           TEXT NOT NULL DEFAULT '',
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (site_id, tag_id, ts)
);

SELECT create_hypertable(
    'public.edgeex_vqt_raw',
    'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_edgeex_vqt_raw_tag_ts
    ON public.edgeex_vqt_raw (tag_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_edgeex_vqt_raw_quality_ts
    ON public.edgeex_vqt_raw (final_quality, ts DESC);
