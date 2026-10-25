-- Migration 014: edgeEX 무손실 VQT 원본/최종값 이력 테이블 (final_quality=0 BAD 및 final_val=NULL 표본 보존)
-- 계약(migrations/AGENTS.md): Idempotent (CREATE ... IF NOT EXISTS, create_hypertable if_not_exists => true)

CREATE TABLE IF NOT EXISTS public.edgeex_vqt_raw (
    ts            TIMESTAMPTZ NOT NULL,
    site_id       TEXT NOT NULL DEFAULT 'poongdo-edge-01',
    tag_id        TEXT NOT NULL,
    channel       TEXT NOT NULL DEFAULT 'default',
    raw_val       DOUBLE PRECISION NULL,
    cond_val      DOUBLE PRECISION NULL,
    final_val     DOUBLE PRECISION NULL,
    final_quality SMALLINT NOT NULL DEFAULT 2,   -- edgeEX OPC quality (2=GOOD, 1=UNCERTAIN, 0=BAD)
    influx_quality SMALLINT NOT NULL DEFAULT 0,  -- ksys_app quality (0=정상, 1=불확실, 2=불량)
    integ_class   SMALLINT NOT NULL DEFAULT 0,   -- 0~5 (NORMAL..COLLECTION_STOPPED)
    integ_status  TEXT NOT NULL DEFAULT 'NORMAL',
    reasons       JSONB NOT NULL DEFAULT '[]'::jsonb,
    unit          TEXT NOT NULL DEFAULT '',
    ingested_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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


-- CR-EXAT-277 경보 사건 멱등 Upsert (event_id, triggered_at) 고유 인덱스 보장
CREATE UNIQUE INDEX IF NOT EXISTS idx_alarm_history_event_triggered_uq
    ON public.alarm_history (event_id, triggered_at);
