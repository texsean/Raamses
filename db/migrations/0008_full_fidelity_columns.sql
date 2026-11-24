-- RaamsesAgent — 0008: full-fidelity columns (Phase 3, step 1).
--
-- Stock SQLite sessions is 58 columns and messages is 24 (hermes_state_common.py
-- SCHEMA_SQL) — a correction to the Sept 12 progress log's "~60 / ~28".
-- The Postgres skeleton after 0006 is sessions 7 cols / messages 10 cols.
-- This migration adds the missing 56 + 19 = 75 columns, additive only:
-- ALTER TABLE ... ADD COLUMN IF NOT EXISTS. No DROP, no rebuild (cf. 0006 gotcha).
--
-- Type rules: TEXT -> TEXT (including JSON-encoded TEXT: model_config,
-- origin_json, handoff_state, tool_calls, reasoning_details, codex_*,
-- api_content, display_metadata — kept TEXT, not JSONB, so the facade does no
-- silent conversion in 0008), INTEGER -> INTEGER, REAL epoch/cost -> DOUBLE
-- PRECISION. Flags stay INTEGER 0/1 as in SQLite.
--
-- system_prompts: stock has this table (hash TEXT PRIMARY KEY, prompt TEXT
-- NOT NULL) and get_session() LEFT JOINs it, so it is created here — the
-- draft left it open, stock settles it.
--
-- Defaults: stock columns with DEFAULT 0 are added here with NO default, so
-- the migration applies cleanly to existing test rows. The final facade must
-- set them on insert (_insert_session_row only writes 17 session columns on
-- create; the rest arrive via later setters/counters), or a follow-up
-- migration should add the DEFAULTs. started_at is NOT NULL in stock but is
-- left nullable here for the same reason; the facade must always set it.
--
-- No indexes in this migration — add only if list_sessions_rich /
-- find_session_by_origin proves slow (session_key, chat_id, started_at).
--
-- Apply to a running instance with:
--   docker compose -f docker-compose.postgres.yml exec -T postgres \
--     psql -U raamses -d raamses -v ON_ERROR_STOP=1 < db/migrations/0008_full_fidelity_columns.sql

-- ======================================================== system_prompts ===
CREATE TABLE IF NOT EXISTS system_prompts (
    hash TEXT PRIMARY KEY,
    prompt TEXT NOT NULL
);

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS session_key TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS chat_id TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS chat_type TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS thread_id TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS origin_json TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS expiry_finalized INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS model TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS model_config TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS system_prompt TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS system_prompt_hash TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS parent_session_id TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS started_at DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS ended_at DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS end_reason TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS message_count INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS tool_call_count INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS input_tokens INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS output_tokens INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cache_read_tokens INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cache_write_tokens INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS reasoning_tokens INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cwd TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS git_branch TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS git_repo_root TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS git_metadata_generation INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS billing_provider TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS billing_base_url TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS billing_mode TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS estimated_cost_usd DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS actual_cost_usd DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cost_status TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS cost_source TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS pricing_version TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS title_source TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_activity_at DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_activity_description TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_activity_provenance TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS api_call_count INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS handoff_state TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS handoff_platform TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS handoff_error TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS compression_failure_cooldown_until DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS compression_failure_error TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS compression_fallback_streak INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS compression_ineffective_count INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS compression_recovery_deadline DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS profile_name TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS rewind_count INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS archived INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS pinned INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS hidden INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS last_read_at DOUBLE PRECISION;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS tool_names TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS tool_call_id TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS tool_calls TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS tool_name TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS effect_disposition TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS timestamp DOUBLE PRECISION;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS finish_reason TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS reasoning TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS reasoning_content TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS reasoning_details TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS codex_reasoning_items TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS codex_message_items TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS platform_message_id TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS observed INTEGER;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS _compressed_summary INTEGER;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS active INTEGER;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS compacted INTEGER;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS api_content TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS display_kind TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS display_metadata TEXT;
