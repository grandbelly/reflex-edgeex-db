-- ============================================================================
-- Migration: 010_viewer_tag.sql
-- Description: Create viewer_tag table for controlling tag visibility per screen
-- Date: 2025-11-29
-- Applies to: RPI, Local, reflex-edgeex-refactor
-- ============================================================================

-- 1. Create viewer_tag table
CREATE TABLE IF NOT EXISTS viewer_tag (
    tag_name TEXT PRIMARY KEY,
    display_order INT DEFAULT 0,          -- 표시 순서 (낮을수록 먼저)
    show_dashboard BOOLEAN DEFAULT true,  -- 대시보드 표시
    show_alarm BOOLEAN DEFAULT true,      -- 알람 표시
    show_trend BOOLEAN DEFAULT true,      -- 트렌드 표시
    show_model BOOLEAN DEFAULT true,      -- 모델 학습 대상
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Add comment
COMMENT ON TABLE viewer_tag IS '화면별 태그 표시 제어 테이블';
COMMENT ON COLUMN viewer_tag.display_order IS '표시 순서 (낮을수록 먼저 표시)';
COMMENT ON COLUMN viewer_tag.show_dashboard IS '대시보드 화면 표시 여부';
COMMENT ON COLUMN viewer_tag.show_alarm IS '알람 화면 표시 여부';
COMMENT ON COLUMN viewer_tag.show_trend IS '트렌드 화면 표시 여부';
COMMENT ON COLUMN viewer_tag.show_model IS 'ML 모델 학습 대상 여부';

-- 3. Create updated_at trigger
CREATE OR REPLACE FUNCTION update_viewer_tag_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS viewer_tag_updated_at ON viewer_tag;
CREATE TRIGGER viewer_tag_updated_at
    BEFORE UPDATE ON viewer_tag
    FOR EACH ROW
    EXECUTE FUNCTION update_viewer_tag_timestamp();

-- 4. Populate from existing influx_hist tags (all visible by default)
INSERT INTO viewer_tag (tag_name, display_order, show_dashboard, show_alarm, show_trend, show_model)
SELECT DISTINCT
    tag_name,
    ROW_NUMBER() OVER (ORDER BY tag_name) * 10 as display_order,
    true, true, true, true
FROM influx_hist
WHERE ts > NOW() - INTERVAL '7 days'
ON CONFLICT (tag_name) DO NOTHING;

-- 5. Create helper views for each screen
-- Dashboard view
CREATE OR REPLACE VIEW influx_latest_dashboard AS
SELECT DISTINCT ON (h.tag_name)
    h.tag_name, h.ts, h.value, h.quality
FROM influx_hist h
INNER JOIN viewer_tag v ON h.tag_name = v.tag_name AND v.show_dashboard = true
WHERE h.ts > (now() - '1 day'::interval)
ORDER BY h.tag_name, h.ts DESC;

-- Alarm view
CREATE OR REPLACE VIEW influx_latest_alarm AS
SELECT DISTINCT ON (h.tag_name)
    h.tag_name, h.ts, h.value, h.quality
FROM influx_hist h
INNER JOIN viewer_tag v ON h.tag_name = v.tag_name AND v.show_alarm = true
WHERE h.ts > (now() - '1 day'::interval)
ORDER BY h.tag_name, h.ts DESC;

-- Trend view
CREATE OR REPLACE VIEW influx_latest_trend AS
SELECT DISTINCT ON (h.tag_name)
    h.tag_name, h.ts, h.value, h.quality
FROM influx_hist h
INNER JOIN viewer_tag v ON h.tag_name = v.tag_name AND v.show_trend = true
WHERE h.ts > (now() - '1 day'::interval)
ORDER BY h.tag_name, h.ts DESC;

-- Model training view
CREATE OR REPLACE VIEW influx_latest_model AS
SELECT DISTINCT ON (h.tag_name)
    h.tag_name, h.ts, h.value, h.quality
FROM influx_hist h
INNER JOIN viewer_tag v ON h.tag_name = v.tag_name AND v.show_model = true
WHERE h.ts > (now() - '1 day'::interval)
ORDER BY h.tag_name, h.ts DESC;

-- 6. Update original influx_latest to use viewer_tag (backward compatible)
CREATE OR REPLACE VIEW influx_latest AS
SELECT DISTINCT ON (h.tag_name)
    h.tag_name, h.ts, h.value, h.quality
FROM influx_hist h
INNER JOIN viewer_tag v ON h.tag_name = v.tag_name AND v.show_dashboard = true
WHERE h.ts > (now() - '1 day'::interval)
ORDER BY h.tag_name, h.ts DESC;

-- 7. Show result
SELECT 'viewer_tag migration complete' as status;
SELECT tag_name, display_order, show_dashboard, show_alarm, show_trend, show_model
FROM viewer_tag ORDER BY display_order;
