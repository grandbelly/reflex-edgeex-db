# ksys_app/ai_engine — RAG + multi-agent layer

## Purpose

Retrieval-augmented generation and multi-agent reasoning for water-quality Q&A. Powers the `/ai` page.

## Ownership

Key files: `rag_engine.py` (semantic search + OpenAI calls, lazy init), `agent_orchestrator.py`
(Research/Analysis/Review agents), `audit_agent_system.py` (grades agent output),
`graph_rag_engine.py` (knowledge-graph RAG), `hallucination_prevention.py` (cross-checks LLM vs DB facts).

## Local Contracts

- **This whole layer is optional.** It depends on `openai`, `scikit-learn`, `numpy`, and pgvector embeddings.
- **Never import this layer on an unconditional boot path.** It loads only behind the `ENABLE_AI_FEATURES`
  flag + try/except in `ksys_app.py`; a missing dep must skip `/ai` only, never crash app boot.
- Async APIs throughout; lazy init (e.g. `RAGEngine._initialized` set on first response).
- Validate LLM output against DB facts (`hallucination_prevention`) before returning to the user.

## Work Guidance

- Keep new heavy imports lazy/inside functions, not at module top, so the guard stays effective.
- Agents return structured `W5H1Response` (Why/What/When/Who/Where/How) — follow that shape.

## Verification

Manual via `/ai` with `ENABLE_AI_FEATURES=true` and deps installed. Confirm app still boots with the
flag off or deps missing.

## Child DOX Index

None.
