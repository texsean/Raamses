-- RaamsesAgent SQL State Layer — 0006: session_id is TEXT, not UUID (Phase 3 foundation).
--
-- Why: Hermes session ids are timestamp strings like `20260912_113311_45eac8`,
-- produced by the runtime and passed in by callers (run_agent.py, the CLI, the
-- gateway). Phase 1/2 declared `sessions.session_id UUID` and generated ids with
-- `gen_random_uuid()` inside `sp_create_session` — that can never store a real
-- Hermes session, so the port would have dead-ended on its first real turn.
--
-- This migration rebuilds the schema with `session_id TEXT` as the primary key
-- everywhere it appears, and rewrites `sp_create_session` to take the caller's
-- id (upsert) instead of minting a UUID. The table shapes and the other stored
-- functions are otherwise unchanged. Full-fidelity columns (the ~60 wide columns
-- of the stock SQLite `sessions` table and the ~28 of `messages`) land in a
-- follow-up migration — this one fixes only the id type.
--
-- Safe to run destructively: the only data in this store is throwaway test rows.
-- Apply to a running instance with:
--   docker compose -f docker-compose.postgres.yml exec -T postgres \
--     psql -U raamses -d raamses -v ON_ERROR_STOP=1 < db/migrations/0006_session_id_text.sql

BEGIN;

-- ---- drop functions first (they reference the tables) -----------------------
DROP FUNCTION IF EXISTS sp_build_context(UUID, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS sp_compact_session(UUID, TEXT, BIGINT, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS sp_recall(UUID, VECTOR, TEXT, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS sp_upsert_memory(BIGINT, UUID, TEXT, TEXT, VECTOR, REAL, JSONB) CASCADE;
DROP FUNCTION IF EXISTS sp_log_tool_call(UUID, TEXT, JSONB, BIGINT, JSONB, TEXT, TEXT, NUMERIC) CASCADE;
DROP FUNCTION IF EXISTS sp_append_message(UUID, TEXT, TEXT, BIGINT, INTEGER, JSONB) CASCADE;
DROP FUNCTION IF EXISTS sp_record_turn_metrics(UUID, INTEGER, NUMERIC, NUMERIC, NUMERIC, JSONB) CASCADE;
DROP FUNCTION IF EXISTS sp_list_sessions(TEXT, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS sp_get_session(UUID) CASCADE;
DROP FUNCTION IF EXISTS sp_end_session(UUID, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS sp_create_session(TEXT, JSONB) CASCADE;

-- ---- drop tables (children first) ------------------------------------------
DROP TABLE IF EXISTS file_sync CASCADE;
DROP TABLE IF EXISTS turn_metrics CASCADE;
DROP TABLE IF EXISTS memories CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS summaries CASCADE;
DROP TABLE IF EXISTS tool_calls CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;

-- ============================================================= sessions ====
CREATE TABLE sessions (
    session_id      TEXT PRIMARY KEY,
    title           TEXT,
    status          TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'archived', 'closed')),
    storage_backend TEXT NOT NULL DEFAULT 'raamses'
                        CHECK (storage_backend IN ('hermes', 'raamses')),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_status ON sessions (status);
CREATE INDEX idx_sessions_created_at ON sessions (created_at);

-- ============================================================= messages ====
CREATE TABLE messages (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    parent_id       BIGINT REFERENCES messages (id) ON DELETE SET NULL,
    role            TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content         TEXT NOT NULL,
    token_count     INTEGER,
    branch_label    TEXT,
    is_summarized   BOOLEAN NOT NULL DEFAULT false,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_session_id ON messages (session_id, created_at);
CREATE INDEX idx_messages_parent_id ON messages (parent_id);
CREATE INDEX idx_messages_session_not_summarized
    ON messages (session_id, created_at)
    WHERE is_summarized = false;

-- ============================================================ tool_calls ====
CREATE TABLE tool_calls (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    message_id      BIGINT REFERENCES messages (id) ON DELETE SET NULL,
    tool_name       TEXT NOT NULL,
    arguments       JSONB NOT NULL DEFAULT '{}'::jsonb,
    result          JSONB,
    status          TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'error', 'timeout')),
    error_text      TEXT,
    duration_ms     NUMERIC,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tool_calls_session_id ON tool_calls (session_id, created_at);
CREATE INDEX idx_tool_calls_tool_name ON tool_calls (tool_name);

-- ============================================================= summaries ====
CREATE TABLE summaries (
    id                      BIGSERIAL PRIMARY KEY,
    session_id              TEXT NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    content                 TEXT NOT NULL,
    covers_up_to_message_id BIGINT REFERENCES messages (id) ON DELETE SET NULL,
    token_count             INTEGER,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_summaries_session_id ON summaries (session_id, created_at DESC);

-- ============================================================== memories ====
CREATE TABLE memories (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT REFERENCES sessions (session_id) ON DELETE CASCADE,  -- NULL = global/user-level memory
    kind            TEXT NOT NULL DEFAULT 'fact' CHECK (kind IN ('fact', 'preference', 'episodic', 'summary')),
    content         TEXT NOT NULL,
    embedding       VECTOR(1536),
    importance      REAL NOT NULL DEFAULT 0.5,
    frozen          BOOLEAN NOT NULL DEFAULT false,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_memories_session_id ON memories (session_id);
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memories_content_trgm ON memories USING gin (content gin_trgm_ops);

-- ================================================================ skills ====
CREATE TABLE skills (
    id                  BIGSERIAL PRIMARY KEY,
    session_id          TEXT REFERENCES sessions (session_id) ON DELETE SET NULL,
    name                TEXT NOT NULL,
    description         TEXT,
    category            TEXT,
    content             TEXT NOT NULL,
    source              TEXT NOT NULL DEFAULT 'user'
                            CHECK (source IN ('bundled', 'plugin', 'hub', 'user')),
    file_path           TEXT,
    version             TEXT,
    usage_count         INTEGER NOT NULL DEFAULT 0,
    last_used_at        TIMESTAMPTZ,
    curator_state       JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_suppressed       BOOLEAN NOT NULL DEFAULT false,
    is_archived         BOOLEAN NOT NULL DEFAULT false,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, source)
);

CREATE INDEX idx_skills_name ON skills (name);
CREATE INDEX idx_skills_active ON skills (is_archived, is_suppressed);

-- ============================================================ turn_metrics ==
CREATE TABLE turn_metrics (
    id              BIGSERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    turn_number     INTEGER NOT NULL,
    db_ms           NUMERIC NOT NULL DEFAULT 0,
    model_ms        NUMERIC NOT NULL DEFAULT 0,
    tool_ms         NUMERIC NOT NULL DEFAULT 0,
    total_ms        NUMERIC GENERATED ALWAYS AS (db_ms + model_ms + tool_ms) STORED,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, turn_number)
);

CREATE INDEX idx_turn_metrics_session_id ON turn_metrics (session_id, turn_number);

-- ============================================================== file_sync ==
CREATE TABLE file_sync (
    id                  BIGSERIAL PRIMARY KEY,
    session_id          TEXT REFERENCES sessions (session_id) ON DELETE SET NULL,
    file_path           TEXT NOT NULL UNIQUE,
    content_hash        TEXT NOT NULL,
    watched_kind        TEXT NOT NULL CHECK (watched_kind IN ('skill', 'memory_md')),
    last_direction      TEXT CHECK (last_direction IN ('import', 'export', 'conflict')),
    last_synced_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_file_sync_kind ON file_sync (watched_kind);

-- ========================================================= sp_append_message
CREATE OR REPLACE FUNCTION sp_append_message(
    p_session_id    TEXT,
    p_role          TEXT,
    p_content       TEXT,
    p_parent_id     BIGINT DEFAULT NULL,
    p_token_count   INTEGER DEFAULT NULL,
    p_metadata      JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO messages (session_id, parent_id, role, content, token_count, metadata)
    VALUES (p_session_id, p_parent_id, p_role, p_content, p_token_count, p_metadata)
    RETURNING id INTO v_id;

    UPDATE sessions SET updated_at = now() WHERE session_id = p_session_id;

    RETURN v_id;
END;
$$;

-- ========================================================= sp_log_tool_call
CREATE OR REPLACE FUNCTION sp_log_tool_call(
    p_session_id    TEXT,
    p_tool_name     TEXT,
    p_arguments     JSONB,
    p_message_id    BIGINT DEFAULT NULL,
    p_result        JSONB DEFAULT NULL,
    p_status        TEXT DEFAULT 'ok',
    p_error_text    TEXT DEFAULT NULL,
    p_duration_ms   NUMERIC DEFAULT NULL
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO tool_calls (session_id, message_id, tool_name, arguments, result,
                             status, error_text, duration_ms)
    VALUES (p_session_id, p_message_id, p_tool_name, p_arguments, p_result,
            p_status, p_error_text, p_duration_ms)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

-- ========================================================= sp_upsert_memory
CREATE OR REPLACE FUNCTION sp_upsert_memory(
    p_id            BIGINT,             -- NULL => insert new
    p_session_id    TEXT,               -- NULL => global/user-level memory
    p_kind          TEXT,
    p_content       TEXT,
    p_embedding     VECTOR(1536) DEFAULT NULL,
    p_importance    REAL DEFAULT 0.5,
    p_metadata      JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_id BIGINT;
BEGIN
    IF p_id IS NULL THEN
        INSERT INTO memories (session_id, kind, content, embedding, importance, metadata)
        VALUES (p_session_id, p_kind, p_content, p_embedding, p_importance, p_metadata)
        RETURNING id INTO v_id;
    ELSE
        UPDATE memories
           SET content    = p_content,
               embedding  = COALESCE(p_embedding, embedding),
               importance = p_importance,
               metadata   = p_metadata,
               last_accessed_at = now()
         WHERE id = p_id
        RETURNING id INTO v_id;

        IF v_id IS NULL THEN
            RAISE EXCEPTION 'sp_upsert_memory: no memory row with id=%', p_id;
        END IF;
    END IF;

    RETURN v_id;
END;
$$;

-- ================================================================ sp_recall
CREATE OR REPLACE FUNCTION sp_recall(
    p_session_id        TEXT,
    p_query_embedding   VECTOR(1536) DEFAULT NULL,
    p_query_text        TEXT DEFAULT NULL,
    p_k                 INTEGER DEFAULT 8
) RETURNS TABLE (
    memory_id   BIGINT,
    content     TEXT,
    kind        TEXT,
    importance  REAL,
    score       REAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_query_embedding IS NOT NULL THEN
        RETURN QUERY
        SELECT m.id, m.content, m.kind, m.importance,
               (1 - (m.embedding <=> p_query_embedding))::REAL AS score
        FROM memories m
        WHERE (m.session_id = p_session_id OR m.session_id IS NULL)
          AND m.embedding IS NOT NULL
        ORDER BY m.embedding <=> p_query_embedding
        LIMIT p_k;
    ELSIF p_query_text IS NOT NULL THEN
        RETURN QUERY
        SELECT m.id, m.content, m.kind, m.importance,
               similarity(m.content, p_query_text)::REAL AS score
        FROM memories m
        WHERE (m.session_id = p_session_id OR m.session_id IS NULL)
          AND m.content % p_query_text
        ORDER BY score DESC
        LIMIT p_k;
    ELSE
        RETURN QUERY
        SELECT m.id, m.content, m.kind, m.importance, m.importance AS score
        FROM memories m
        WHERE (m.session_id = p_session_id OR m.session_id IS NULL)
        ORDER BY m.importance DESC, m.last_accessed_at DESC
        LIMIT p_k;
    END IF;
END;
$$;

-- ========================================================= sp_compact_session
CREATE OR REPLACE FUNCTION sp_compact_session(
    p_session_id        TEXT,
    p_summary_content   TEXT,
    p_up_to_message_id  BIGINT,
    p_summary_tokens    INTEGER DEFAULT NULL
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_summary_id BIGINT;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM messages
        WHERE id = p_up_to_message_id AND session_id = p_session_id
    ) THEN
        RAISE EXCEPTION 'sp_compact_session: message % not found in session %',
            p_up_to_message_id, p_session_id;
    END IF;

    INSERT INTO summaries (session_id, content, covers_up_to_message_id, token_count)
    VALUES (p_session_id, p_summary_content, p_up_to_message_id, p_summary_tokens)
    RETURNING id INTO v_summary_id;

    UPDATE messages
       SET is_summarized = true
     WHERE session_id = p_session_id
       AND id <= p_up_to_message_id
       AND is_summarized = false;

    UPDATE sessions SET updated_at = now() WHERE session_id = p_session_id;

    RETURN v_summary_id;
END;
$$;

-- ============================================================ sp_build_context
-- Budget-aware (migration 0004 semantics): walks sections in priority order
-- (summary > memory > skill > message), accumulates a running token total, and
-- stops emitting rows once p_token_budget is exhausted — so an over-budget
-- session evicts its OLDEST unsummarized turns (message rows are newest-first).
CREATE OR REPLACE FUNCTION sp_build_context(
    p_session_id    TEXT,
    p_token_budget  INTEGER DEFAULT 8000
) RETURNS TABLE (
    section         TEXT,
    ord             INTEGER,
    ref_id          BIGINT,
    role            TEXT,
    content         TEXT,
    token_count     INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_used      INTEGER := 0;
    v_budget    INTEGER := GREATEST(COALESCE(p_token_budget, 0), 0);
    r           RECORD;
BEGIN
    FOR r IN
        WITH summary_rows AS (
            SELECT 'summary'::TEXT       AS section,
                   0                     AS ord,
                   s.id                  AS ref_id,
                   'system'::TEXT        AS role,
                   s.content             AS content,
                   COALESCE(s.token_count, GREATEST(length(s.content) / 4, 1)) AS token_count,
                   1                     AS section_rank
            FROM summaries s
            WHERE s.session_id = p_session_id
            ORDER BY s.created_at DESC
            LIMIT 1
        ),
        memory_rows AS (
            SELECT 'memory'::TEXT,
                   ROW_NUMBER() OVER (ORDER BY m.importance DESC, m.last_accessed_at DESC)::INTEGER,
                   m.id,
                   'system'::TEXT,
                   m.content,
                   GREATEST(length(m.content) / 4, 1),
                   2
            FROM memories m
            WHERE (m.session_id = p_session_id OR m.session_id IS NULL)
            ORDER BY m.importance DESC, m.last_accessed_at DESC
            LIMIT 10
        ),
        skill_rows AS (
            SELECT 'skill'::TEXT,
                   ROW_NUMBER() OVER (ORDER BY sk.usage_count DESC, sk.name)::INTEGER,
                   sk.id,
                   'system'::TEXT,
                   sk.name || ': ' || COALESCE(sk.description, ''),
                   GREATEST(length(sk.name || ': ' || COALESCE(sk.description, '')) / 4, 1),
                   3
            FROM skills sk
            WHERE sk.is_archived = false AND sk.is_suppressed = false
            ORDER BY sk.usage_count DESC, sk.name
            LIMIT 20
        ),
        message_rows AS (
            SELECT 'message'::TEXT,
                   ROW_NUMBER() OVER (ORDER BY m.created_at DESC, m.id DESC)::INTEGER,
                   m.id,
                   m.role,
                   m.content,
                   COALESCE(m.token_count, GREATEST(length(m.content) / 4, 1)),
                   4
            FROM messages m
            WHERE m.session_id = p_session_id
              AND m.is_summarized = false
            ORDER BY m.created_at DESC, m.id DESC
        )
        SELECT * FROM summary_rows
        UNION ALL SELECT * FROM memory_rows
        UNION ALL SELECT * FROM skill_rows
        UNION ALL SELECT * FROM message_rows
        ORDER BY section_rank, ord
    LOOP
        EXIT WHEN v_used + r.token_count > v_budget;

        v_used := v_used + r.token_count;

        section     := r.section;
        ord         := r.ord;
        ref_id      := r.ref_id;
        role        := r.role;
        content     := r.content;
        token_count := r.token_count;
        RETURN NEXT;
    END LOOP;
END;
$$;

-- ========================================================= sp_create_session
-- Faithful to stock Hermes: the caller supplies the session id (a timestamp
-- string), we upsert and return it. Source is folded into metadata for now;
-- a real `source` column lands with the full-fidelity migration.
CREATE OR REPLACE FUNCTION sp_create_session(
    p_session_id    TEXT,
    p_source        TEXT DEFAULT NULL,
    p_metadata      JSONB DEFAULT '{}'::jsonb
) RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    v_meta JSONB := p_metadata;
BEGIN
    IF p_source IS NOT NULL THEN
        v_meta := jsonb_build_object('source', p_source) || v_meta;
    END IF;

    INSERT INTO sessions (session_id, metadata)
    VALUES (p_session_id, v_meta)
    ON CONFLICT (session_id) DO NOTHING;

    RETURN p_session_id;
END;
$$;

-- =========================================================== sp_end_session
CREATE OR REPLACE FUNCTION sp_end_session(
    p_session_id    TEXT,
    p_status        TEXT DEFAULT 'closed',
    p_end_reason    TEXT DEFAULT NULL
) RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_found BOOLEAN;
BEGIN
    UPDATE sessions
       SET status     = p_status,
           metadata   = CASE
                            WHEN p_end_reason IS NULL THEN metadata
                            WHEN metadata ? 'end_reason' THEN metadata  -- first-wins
                            ELSE metadata || jsonb_build_object('end_reason', p_end_reason)
                        END,
           updated_at = now()
     WHERE session_id = p_session_id
    RETURNING true INTO v_found;

    RETURN COALESCE(v_found, false);
END;
$$;

-- ========================================================== sp_get_session
CREATE OR REPLACE FUNCTION sp_get_session(
    p_session_id TEXT
) RETURNS TABLE (
    session_id      TEXT,
    title           TEXT,
    status          TEXT,
    storage_backend TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ
)
LANGUAGE sql
STABLE
AS $$
    SELECT s.session_id, s.title, s.status, s.storage_backend,
           s.metadata, s.created_at, s.updated_at
    FROM sessions s
    WHERE s.session_id = p_session_id;
$$;

-- ======================================================== sp_list_sessions
CREATE OR REPLACE FUNCTION sp_list_sessions(
    p_status    TEXT DEFAULT NULL,
    p_limit     INTEGER DEFAULT 50
) RETURNS TABLE (
    session_id      TEXT,
    title           TEXT,
    status          TEXT,
    message_count   BIGINT,
    created_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ
)
LANGUAGE sql
STABLE
AS $$
    SELECT s.session_id, s.title, s.status,
           (SELECT count(*) FROM messages m WHERE m.session_id = s.session_id),
           s.created_at, s.updated_at
    FROM sessions s
    WHERE p_status IS NULL OR s.status = p_status
    ORDER BY s.updated_at DESC
    LIMIT p_limit;
$$;

-- ======================================================= sp_record_turn_metrics
CREATE OR REPLACE FUNCTION sp_record_turn_metrics(
    p_session_id    TEXT,
    p_turn_number   INTEGER,
    p_db_ms         NUMERIC DEFAULT 0,
    p_model_ms      NUMERIC DEFAULT 0,
    p_tool_ms       NUMERIC DEFAULT 0,
    p_metadata      JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO turn_metrics (session_id, turn_number, db_ms, model_ms, tool_ms, metadata)
    VALUES (p_session_id, p_turn_number, p_db_ms, p_model_ms, p_tool_ms, p_metadata)
    ON CONFLICT (session_id, turn_number) DO UPDATE
        SET db_ms    = EXCLUDED.db_ms,
            model_ms = EXCLUDED.model_ms,
            tool_ms  = EXCLUDED.tool_ms,
            metadata = EXCLUDED.metadata
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

COMMIT;
