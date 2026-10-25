-- ============================================================================
-- Migration 015: edgeEX 명칭 일원화에 따른 DB 메타데이터/주석 갱신 (D-1025-07)
-- 비고:
--   - 기존 마이그레이션(001~014)에는 스키마·표·역할·함수 등 DB 객체 이름에 레거시 접두사가 사용된 객체가 없음(0건).
--   - 본 마이그레이션은 기존 배포 DB의 컬럼 주석(COMMENT) 및 메타데이터 문자열을 edgeex_app / edgeEX 기준으로 멱등 갱신함.
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'edgeex_vqt_raw'
          AND column_name = 'influx_quality'
    ) THEN
        COMMENT ON COLUMN public.edgeex_vqt_raw.influx_quality IS 'edgeex_app quality (0=정상, 1=불확실, 2=불량)';
    END IF;
END
$$;
