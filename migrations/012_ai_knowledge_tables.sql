-- ============================================================================
-- Migration: 012_ai_knowledge_tables.sql
-- Description: AI/RAG 가 요구하나 복원 DB에 누락된 테이블 생성 (audit C3)
-- Date: 2026-06-16
-- 코드 참조: ai_service.get_knowledge_base/save_chat_history, rag_engine._update_knowledge_cache
-- 주의: 빈 테이블이라 RAG 는 지식 없으면 템플릿 모드. 지식 적재(knowledge_loader)는 후속.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS ai_engine;

-- public.ai_knowledge_base — ai_service 가 category/title/content 조회
CREATE TABLE IF NOT EXISTS ai_knowledge_base (
    id          BIGSERIAL PRIMARY KEY,
    category    TEXT,
    title       TEXT,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- public.ai_chat_history — ai_service.save_chat_history
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id           BIGSERIAL PRIMARY KEY,
    user_message TEXT,
    ai_response  TEXT,
    metadata     JSONB DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ai_engine.knowledge_base — rag_engine TF-IDF 지식 캐시
CREATE TABLE IF NOT EXISTS ai_engine.knowledge_base (
    id           BIGSERIAL PRIMARY KEY,
    content      TEXT NOT NULL,
    content_type TEXT,
    metadata     JSONB DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

SELECT 'ai tables created' AS status,
       (SELECT count(*) FROM information_schema.tables
        WHERE table_name IN ('ai_knowledge_base','ai_chat_history')
           OR (table_schema='ai_engine' AND table_name='knowledge_base')) AS n;
