-- ============================================================================
-- TimescaleDB Optimization Strategy for influx_hist
-- ============================================================================

-- 1. Ensure composite index is created
-- This optimizes queries filtering by tag_name and ordering/filtering by timestamp descending
CREATE INDEX IF NOT EXISTS idx_tag_ts_desc ON influx_hist (tag_name, ts DESC);

-- 2. Verify and convert to Hypertable if not already done
-- Partitioning by the timestamp column 'ts'
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'influx_hist'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM timescaledb_information.hypertables 
            WHERE hypertable_schema = 'public' AND hypertable_name = 'influx_hist'
        ) THEN
            PERFORM create_hypertable('influx_hist', 'ts', migrate_data => true);
            RAISE NOTICE 'Hypertable created for influx_hist.';
        ELSE
            RAISE NOTICE 'influx_hist is already a hypertable.';
        END IF;
    END IF;
END $$;

-- 3. Enable TimescaleDB Compression
-- Segments data by tag_name and orders within compression chunks by ts DESC
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables 
        WHERE hypertable_schema = 'public' AND hypertable_name = 'influx_hist'
    ) THEN
        ALTER TABLE influx_hist SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'tag_name',
            timescaledb.compress_orderby = 'ts DESC'
        );
        RAISE NOTICE 'Compression enabled for influx_hist.';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Compression already enabled or could not be set: %', SQLERRM;
END $$;

-- 4. Add Compression Policy (compress chunks older than 7 days)
DO $$
BEGIN
    PERFORM add_compression_policy('influx_hist', INTERVAL '7 days');
    RAISE NOTICE 'Compression policy (7 days) added for influx_hist.';
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Compression policy for influx_hist already exists.';
    WHEN OTHERS THEN
        RAISE NOTICE 'Failed to add compression policy: %', SQLERRM;
END $$;

-- 5. Add Data Retention Policy (remove chunks older than 1 year)
DO $$
BEGIN
    PERFORM add_retention_policy('influx_hist', INTERVAL '1 year');
    RAISE NOTICE 'Retention policy (1 year) added for influx_hist.';
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Retention policy for influx_hist already exists.';
    WHEN OTHERS THEN
        RAISE NOTICE 'Failed to add retention policy: %', SQLERRM;
END $$;
