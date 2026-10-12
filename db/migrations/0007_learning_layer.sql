-- RaamsesAgent — 0007: learning layer (dual-LLM route).
--
-- The main model answers a question; the answer is stored as a solution to a
-- problem (the normalized question). Once a problem has been answered via the
-- main route `promote_after` times, its solutions are ranked and the problem is
-- promoted: later similar questions are answered by the local model from the
-- top-ranked stored solutions, spending no main-model tokens.
--
-- Every table here is scoped by agent_id so several agents can share one
-- database without sharing what they learned. session_id records provenance
-- only (ON DELETE SET NULL): deleting a session never deletes learned answers.
--
-- Matching is pg_trgm similarity on the normalized question (pg_trgm is
-- already enabled in 0001). No embedding provider is required.

-- ======================================================== normalization ===
CREATE OR REPLACE FUNCTION fn_learn_normalize(p_text TEXT)
RETURNS TEXT
LANGUAGE sql IMMUTABLE
AS $$
    SELECT btrim(
        regexp_replace(
            regexp_replace(lower(coalesce(p_text, '')), '\s+', ' ', 'g'),
            '[\s[:punct:]]+$', ''
        )
    );
$$;

-- ============================================================= problems ===
CREATE TABLE problems (
    id               BIGSERIAL PRIMARY KEY,
    agent_id         TEXT NOT NULL,
    session_id       TEXT REFERENCES sessions (session_id) ON DELETE SET NULL,  -- first seen in
    question         TEXT NOT NULL,          -- first raw wording seen
    normalized       TEXT NOT NULL,          -- fn_learn_normalize(question)
    main_answers     INTEGER NOT NULL DEFAULT 0,   -- times answered via the main route
    local_answers    INTEGER NOT NULL DEFAULT 0,   -- times served by the local route
    promoted_at      TIMESTAMPTZ,            -- non-NULL => local route serves this problem
    demoted_at       TIMESTAMPTZ,            -- last explicit demotion (bad local answer)
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (agent_id, normalized)
);

CREATE INDEX idx_problems_agent ON problems (agent_id);
CREATE INDEX idx_problems_normalized_trgm ON problems USING gin (normalized gin_trgm_ops);

-- ============================================================ solutions ===
-- One row per distinct main-model answer. Identical answers (same hash) bump
-- times_given instead of inserting. Local-route answers are never stored here,
-- so the local model cannot reinforce its own output.
CREATE TABLE solutions (
    id               BIGSERIAL PRIMARY KEY,
    problem_id       BIGINT NOT NULL REFERENCES problems (id) ON DELETE CASCADE,
    agent_id         TEXT NOT NULL,
    session_id       TEXT REFERENCES sessions (session_id) ON DELETE SET NULL,
    answer           TEXT NOT NULL,
    answer_hash      TEXT NOT NULL,          -- md5(answer), dedup key
    model            TEXT,                   -- main model that produced it
    times_given      INTEGER NOT NULL DEFAULT 1,
    upvotes          INTEGER NOT NULL DEFAULT 0,
    downvotes        INTEGER NOT NULL DEFAULT 0,
    score            REAL NOT NULL DEFAULT 0,      -- set by sp_learn_rank
    rank             INTEGER,                      -- 1 = best; set by sp_learn_rank
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_given_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (problem_id, answer_hash)
);

CREATE INDEX idx_solutions_problem_rank ON solutions (problem_id, rank);
CREATE INDEX idx_solutions_agent ON solutions (agent_id);

-- ======================================================== problem_hits ===
-- The counter ledger: one row per routed turn, whichever route served it.
-- problems.main_answers / local_answers are the running totals of this table.
CREATE TABLE problem_hits (
    id               BIGSERIAL PRIMARY KEY,
    problem_id       BIGINT NOT NULL REFERENCES problems (id) ON DELETE CASCADE,
    solution_id      BIGINT REFERENCES solutions (id) ON DELETE SET NULL,
    agent_id         TEXT NOT NULL,
    session_id       TEXT REFERENCES sessions (session_id) ON DELETE SET NULL,
    route            TEXT NOT NULL CHECK (route IN ('main', 'local', 'local_declined')),
    similarity       REAL,                   -- match score that routed the turn
    model            TEXT,
    prompt_tokens    INTEGER,                -- main route only: what the turn actually cost
    completion_tokens INTEGER,
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_problem_hits_problem ON problem_hits (problem_id, created_at);
CREATE INDEX idx_problem_hits_agent_route ON problem_hits (agent_id, route, created_at);

-- ======================================================== sp_learn_match
-- Best problem for a question within one agent, if any clears the threshold.
-- Returns zero or one row. Read-only: counters move only on sp_learn_record /
-- sp_learn_log_hit, so a match that the caller then declines costs nothing.
-- The `%` operator uses pg_trgm.similarity_threshold (default 0.3) for the
-- index scan, so thresholds below that floor behave as 0.3.
CREATE OR REPLACE FUNCTION sp_learn_match(
    p_agent_id   TEXT,
    p_question   TEXT,
    p_threshold  REAL DEFAULT 0.6
) RETURNS TABLE (
    problem_id    BIGINT,
    similarity    REAL,
    main_answers  INTEGER,
    promoted      BOOLEAN
)
LANGUAGE sql STABLE
AS $$
    SELECT p.id,
           similarity(p.normalized, fn_learn_normalize(p_question)),
           p.main_answers,
           p.promoted_at IS NOT NULL
      FROM problems p
     WHERE p.agent_id = p_agent_id
       AND p.normalized % fn_learn_normalize(p_question)
       AND similarity(p.normalized, fn_learn_normalize(p_question)) >= p_threshold
     ORDER BY similarity(p.normalized, fn_learn_normalize(p_question)) DESC, p.main_answers DESC
     LIMIT 1;
$$;

-- ========================================================= sp_learn_rank
-- Rank one problem's solutions. Score is consensus plus feedback:
--   * consensus  = sum over the problem's other solutions of
--                  similarity(this, other) * other.times_given — an answer the
--                  main model keeps converging on outranks a one-off;
--   * own weight = times_given;
--   * feedback   = 2 * upvotes - 3 * downvotes.
-- Solutions older than p_ttl_days (by last_given_at) are ranked NULL and are
-- never served. Returns the number of rankable solutions.
CREATE OR REPLACE FUNCTION sp_learn_rank(
    p_problem_id BIGINT,
    p_ttl_days   INTEGER DEFAULT 30
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH live AS (
        SELECT s.id, s.answer, s.times_given, s.upvotes, s.downvotes, s.last_given_at
          FROM solutions s
         WHERE s.problem_id = p_problem_id
           AND (p_ttl_days IS NULL OR s.last_given_at >= now() - make_interval(days => p_ttl_days))
    ), scored AS (
        SELECT a.id,
               a.times_given
               + coalesce((SELECT sum(similarity(a.answer, b.answer) * b.times_given)
                             FROM live b WHERE b.id <> a.id), 0)
               + 2 * a.upvotes - 3 * a.downvotes AS score,
               a.last_given_at
          FROM live a
    ), ranked AS (
        SELECT id, score,
               row_number() OVER (ORDER BY score DESC, last_given_at DESC, id DESC) AS rnk
          FROM scored
    )
    UPDATE solutions s
       SET score = r.score, rank = r.rnk
      FROM ranked r
     WHERE s.id = r.id;

    GET DIAGNOSTICS v_count = ROW_COUNT;

    UPDATE solutions
       SET rank = NULL
     WHERE problem_id = p_problem_id
       AND p_ttl_days IS NOT NULL
       AND last_given_at < now() - make_interval(days => p_ttl_days);

    RETURN v_count;
END;
$$;

-- ======================================================= sp_learn_record
-- Record one main-route answer. Finds the matching problem (or creates one),
-- upserts the solution, logs a 'main' hit, and — once main_answers reaches
-- p_promote_after and at least one solution has a non-negative score — ranks
-- and promotes the problem. Runs in the caller's single statement, so the
-- counters, the hit row and the promotion are atomic.
CREATE OR REPLACE FUNCTION sp_learn_record(
    p_agent_id          TEXT,
    p_session_id        TEXT,
    p_question          TEXT,
    p_answer            TEXT,
    p_model             TEXT DEFAULT NULL,
    p_threshold         REAL DEFAULT 0.6,
    p_promote_after     INTEGER DEFAULT 3,
    p_ttl_days          INTEGER DEFAULT 30,
    p_prompt_tokens     INTEGER DEFAULT NULL,
    p_completion_tokens INTEGER DEFAULT NULL,
    p_metadata          JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE (
    problem_id   BIGINT,
    solution_id  BIGINT,
    main_answers INTEGER,
    promoted     BOOLEAN
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
DECLARE
    v_problem_id  BIGINT;
    v_similarity  REAL;
    v_solution_id BIGINT;
    v_main        INTEGER;
    v_promoted    BOOLEAN;
    v_session     TEXT;
BEGIN
    -- Provenance only: an unknown session id is stored as NULL, not rejected.
    SELECT s.session_id INTO v_session FROM sessions s WHERE s.session_id = p_session_id;

    SELECT m.problem_id, m.similarity INTO v_problem_id, v_similarity
      FROM sp_learn_match(p_agent_id, p_question, p_threshold) m;

    IF v_problem_id IS NULL THEN
        INSERT INTO problems (agent_id, session_id, question, normalized)
        VALUES (p_agent_id, v_session, p_question, fn_learn_normalize(p_question))
        ON CONFLICT (agent_id, normalized) DO UPDATE SET last_seen_at = now()
        RETURNING id INTO v_problem_id;
        v_similarity := 1.0;
    END IF;

    INSERT INTO solutions (problem_id, agent_id, session_id, answer, answer_hash, model)
    VALUES (v_problem_id, p_agent_id, v_session, p_answer, md5(p_answer), p_model)
    ON CONFLICT ON CONSTRAINT solutions_problem_id_answer_hash_key DO UPDATE
        SET times_given   = solutions.times_given + 1,
            last_given_at = now(),
            model         = coalesce(EXCLUDED.model, solutions.model)
    RETURNING id INTO v_solution_id;

    UPDATE problems p
       SET main_answers = p.main_answers + 1,
           last_seen_at = now()
     WHERE p.id = v_problem_id
    RETURNING p.main_answers, p.promoted_at IS NOT NULL INTO v_main, v_promoted;

    INSERT INTO problem_hits (problem_id, solution_id, agent_id, session_id, route,
                              similarity, model, prompt_tokens, completion_tokens, metadata)
    VALUES (v_problem_id, v_solution_id, p_agent_id, v_session, 'main',
            v_similarity, p_model, p_prompt_tokens, p_completion_tokens, coalesce(p_metadata, '{}'::jsonb));

    IF v_main >= p_promote_after THEN
        PERFORM sp_learn_rank(v_problem_id, p_ttl_days);
        IF NOT v_promoted AND EXISTS (
            SELECT 1 FROM solutions s
             WHERE s.problem_id = v_problem_id AND s.rank IS NOT NULL AND s.score >= 0
        ) THEN
            UPDATE problems SET promoted_at = now() WHERE id = v_problem_id;
            v_promoted := true;
        END IF;
    END IF;

    RETURN QUERY SELECT v_problem_id, v_solution_id, v_main, v_promoted;
END;
$$;

-- ==================================================== sp_learn_solutions
-- Top-k ranked, non-negative, in-TTL solutions for a promoted problem — the
-- material the local model answers from. Empty when the problem is not promoted.
CREATE OR REPLACE FUNCTION sp_learn_solutions(
    p_problem_id BIGINT,
    p_k          INTEGER DEFAULT 3,
    p_ttl_days   INTEGER DEFAULT 30
) RETURNS TABLE (
    solution_id BIGINT,
    answer      TEXT,
    score       REAL,
    rank        INTEGER
)
LANGUAGE sql STABLE
AS $$
    SELECT s.id, s.answer, s.score, s.rank
      FROM solutions s
      JOIN problems p ON p.id = s.problem_id
     WHERE s.problem_id = p_problem_id
       AND p.promoted_at IS NOT NULL
       AND s.rank IS NOT NULL
       AND s.score >= 0
       AND (p_ttl_days IS NULL OR s.last_given_at >= now() - make_interval(days => p_ttl_days))
     ORDER BY s.rank
     LIMIT greatest(p_k, 1);
$$;

-- ====================================================== sp_learn_log_hit
-- Log a local-route outcome: 'local' (served) or 'local_declined' (the local
-- model said the stored answers do not fit; the turn fell through to main).
CREATE OR REPLACE FUNCTION sp_learn_log_hit(
    p_problem_id  BIGINT,
    p_session_id  TEXT,
    p_route       TEXT,
    p_solution_id BIGINT DEFAULT NULL,
    p_similarity  REAL DEFAULT NULL,
    p_model       TEXT DEFAULT NULL,
    p_metadata    JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_id      BIGINT;
    v_agent   TEXT;
    v_session TEXT;
BEGIN
    IF p_route NOT IN ('local', 'local_declined') THEN
        RAISE EXCEPTION 'sp_learn_log_hit: route must be local or local_declined, got %', p_route;
    END IF;

    SELECT agent_id INTO v_agent FROM problems WHERE id = p_problem_id;
    IF v_agent IS NULL THEN
        RAISE EXCEPTION 'sp_learn_log_hit: unknown problem %', p_problem_id;
    END IF;
    SELECT s.session_id INTO v_session FROM sessions s WHERE s.session_id = p_session_id;

    INSERT INTO problem_hits (problem_id, solution_id, agent_id, session_id, route,
                              similarity, model, metadata)
    VALUES (p_problem_id, p_solution_id, v_agent, v_session, p_route,
            p_similarity, p_model, coalesce(p_metadata, '{}'::jsonb))
    RETURNING id INTO v_id;

    IF p_route = 'local' THEN
        UPDATE problems SET local_answers = local_answers + 1, last_seen_at = now()
         WHERE id = p_problem_id;
    END IF;

    RETURN v_id;
END;
$$;

-- ===================================================== sp_learn_feedback
-- Up/down-vote one solution, re-rank its problem, and demote the problem when
-- no servable solution remains. p_vote: +1 or -1. Returns the problem's
-- promoted state after the vote.
CREATE OR REPLACE FUNCTION sp_learn_feedback(
    p_solution_id BIGINT,
    p_vote        INTEGER,
    p_ttl_days    INTEGER DEFAULT 30
) RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_problem_id BIGINT;
BEGIN
    IF p_vote NOT IN (1, -1) THEN
        RAISE EXCEPTION 'sp_learn_feedback: vote must be 1 or -1, got %', p_vote;
    END IF;

    UPDATE solutions
       SET upvotes   = upvotes   + (p_vote = 1)::int,
           downvotes = downvotes + (p_vote = -1)::int
     WHERE id = p_solution_id
    RETURNING problem_id INTO v_problem_id;

    IF v_problem_id IS NULL THEN
        RAISE EXCEPTION 'sp_learn_feedback: unknown solution %', p_solution_id;
    END IF;

    PERFORM sp_learn_rank(v_problem_id, p_ttl_days);

    IF NOT EXISTS (
        SELECT 1 FROM solutions
         WHERE problem_id = v_problem_id AND rank IS NOT NULL AND score >= 0
    ) THEN
        UPDATE problems SET promoted_at = NULL, demoted_at = now()
         WHERE id = v_problem_id AND promoted_at IS NOT NULL;
    END IF;

    RETURN (SELECT promoted_at IS NOT NULL FROM problems WHERE id = v_problem_id);
END;
$$;

-- ======================================================== sp_learn_demote
-- Force a problem back to the main route. Its counter restarts so it must
-- earn promotion again with fresh main-model answers.
CREATE OR REPLACE FUNCTION sp_learn_demote(p_problem_id BIGINT)
RETURNS BOOLEAN
LANGUAGE sql
AS $$
    UPDATE problems
       SET promoted_at = NULL, demoted_at = now(), main_answers = 0
     WHERE id = p_problem_id
    RETURNING true;
$$;

-- ========================================================= sp_learn_stats
-- Per-route turn counts for one agent since p_since (NULL = all time), plus
-- the main-route tokens actually spent. Feeds the benchmark; no estimates.
CREATE OR REPLACE FUNCTION sp_learn_stats(
    p_agent_id TEXT,
    p_since    TIMESTAMPTZ DEFAULT NULL
) RETURNS TABLE (
    route             TEXT,
    turns             BIGINT,
    prompt_tokens     BIGINT,
    completion_tokens BIGINT
)
LANGUAGE sql STABLE
AS $$
    SELECT h.route, count(*), sum(h.prompt_tokens), sum(h.completion_tokens)
      FROM problem_hits h
     WHERE h.agent_id = p_agent_id
       AND (p_since IS NULL OR h.created_at >= p_since)
     GROUP BY h.route
     ORDER BY h.route;
$$;
