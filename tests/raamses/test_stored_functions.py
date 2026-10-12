"""RaamsesAgent SQL state layer — stored-function tests (charter criterion 6).

These run against a live Postgres 16 + pgvector instance:

    docker compose -f docker-compose.postgres.yml up -d
    pytest tests/raamses/test_stored_functions.py

Connection comes from RAAMSES_DSN, defaulting to the docker-compose service.
When no server is reachable the whole module skips, so the stock Hermes suite
stays green on machines without Docker.

Every test drives the database ONLY through stored functions (charter
architecture rule: application code contains no raw SQL) except for the
assertions, which read tables directly to verify the functions' effects.
"""

from __future__ import annotations

import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.environ.get(
    "RAAMSES_DSN",
    "postgresql://raamses:raamses_dev_password@localhost:55432/raamses",
)


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg.connect(DSN, connect_timeout=5)
    except psycopg.Error as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no Postgres at {DSN}: {exc}")
    c.autocommit = True
    yield c
    c.close()


@pytest.fixture
def session_id(conn):
    """A throwaway session, cascade-deleted after the test."""
    sid = f"test-{uuid.uuid4().hex}"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO sessions (session_id) VALUES (%s)",
            (sid,),
        )
    yield sid
    with conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE session_id = %s", (sid,))


# Postgres resolves overloads from argument types, and psycopg sends untyped
# parameters as `unknown` — which fails to match VECTOR/JSONB/REAL signatures.
# Each stored function therefore declares the casts for its parameter list.
SIGNATURES = {
    "sp_append_message": ["text", "text", "text", "bigint", "integer", "jsonb"],
    "sp_log_tool_call": ["text", "text", "jsonb", "bigint", "jsonb", "text", "text", "numeric"],
    "sp_upsert_memory": ["bigint", "text", "text", "text", "vector(1536)", "real", "jsonb"],
    "sp_recall": ["text", "vector(1536)", "text", "integer"],
    "sp_compact_session": ["text", "text", "bigint", "integer"],
    "sp_build_context": ["text", "integer"],
}


def _placeholders(fn: str, n: int) -> str:
    casts = SIGNATURES[fn][:n]
    return ", ".join(f"%s::{c}" for c in casts)


def call(conn, fn: str, *args):
    """Invoke a scalar-returning stored function."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {fn}({_placeholders(fn, len(args))})", args)
        return cur.fetchone()[0]


def call_table(conn, fn: str, *args):
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {fn}({_placeholders(fn, len(args))})", args)
        return cur.fetchall()


# ------------------------------------------------------------ schema shape --

def test_all_v1_tables_exist(conn):
    expected = {
        "sessions", "messages", "tool_calls", "summaries",
        "memories", "skills", "turn_metrics", "file_sync",
    }
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        found = {r[0] for r in cur.fetchall()}
    assert expected <= found, f"missing tables: {expected - found}"


def test_all_v1_functions_exist(conn):
    expected = {
        "sp_append_message", "sp_log_tool_call", "sp_upsert_memory",
        "sp_compact_session", "sp_recall", "sp_build_context",
    }
    with conn.cursor() as cur:
        cur.execute(
            "SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND proname LIKE 'sp\\_%'"
        )
        found = {r[0] for r in cur.fetchall()}
    assert expected <= found, f"missing functions: {expected - found}"


# ------------------------------------------------------- sp_append_message --

def test_append_message_returns_id_and_persists(conn, session_id):
    mid = call(conn, "sp_append_message", session_id, "user", "hello world", None, 3, "{}")
    assert isinstance(mid, int)
    with conn.cursor() as cur:
        cur.execute("SELECT role, content, token_count FROM messages WHERE id = %s", (mid,))
        assert cur.fetchone() == ("user", "hello world", 3)


def test_append_message_bumps_session_updated_at(conn, session_id):
    with conn.cursor() as cur:
        cur.execute("SELECT updated_at FROM sessions WHERE session_id = %s", (session_id,))
        before = cur.fetchone()[0]
    call(conn, "sp_append_message", session_id, "user", "bump", None, None, "{}")
    with conn.cursor() as cur:
        cur.execute("SELECT updated_at FROM sessions WHERE session_id = %s", (session_id,))
        after = cur.fetchone()[0]
    assert after >= before


def test_append_message_supports_branching_via_parent_id(conn, session_id):
    root = call(conn, "sp_append_message", session_id, "user", "root", None, None, "{}")
    branch_a = call(conn, "sp_append_message", session_id, "assistant", "A", root, None, "{}")
    branch_b = call(conn, "sp_append_message", session_id, "assistant", "B", root, None, "{}")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM messages WHERE parent_id = %s", (root,))
        assert cur.fetchone()[0] == 2
    assert branch_a != branch_b


def test_append_message_rejects_bad_role(conn, session_id):
    with pytest.raises(psycopg.errors.CheckViolation):
        call(conn, "sp_append_message", session_id, "wizard", "nope", None, None, "{}")


# --------------------------------------------------------- sp_log_tool_call --

def test_log_tool_call_persists_payload(conn, session_id):
    mid = call(conn, "sp_append_message", session_id, "assistant", "calling tool", None, None, "{}")
    tid = call(
        conn, "sp_log_tool_call", session_id, "terminal",
        '{"command": "ls"}', mid, '{"exit_code": 0}', "ok", None, 12.5,
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tool_name, status, duration_ms, arguments FROM tool_calls WHERE id = %s",
            (tid,),
        )
        name, status, duration, args = cur.fetchone()
    assert (name, status, float(duration)) == ("terminal", "ok", 12.5)
    assert args == {"command": "ls"}


def test_log_tool_call_records_errors(conn, session_id):
    tid = call(
        conn, "sp_log_tool_call", session_id, "web_search",
        "{}", None, None, "error", "rate limited", None,
    )
    with conn.cursor() as cur:
        cur.execute("SELECT status, error_text FROM tool_calls WHERE id = %s", (tid,))
        assert cur.fetchone() == ("error", "rate limited")


# --------------------------------------------------------- sp_upsert_memory --

def test_upsert_memory_inserts_when_id_is_null(conn, session_id):
    mid = call(conn, "sp_upsert_memory", None, session_id, "fact", "postgres runs on 55432", None, 0.9, "{}")
    with conn.cursor() as cur:
        cur.execute("SELECT content, importance FROM memories WHERE id = %s", (mid,))
        content, importance = cur.fetchone()
    assert content == "postgres runs on 55432"
    assert importance == pytest.approx(0.9)


def test_upsert_memory_updates_existing_row(conn, session_id):
    mid = call(conn, "sp_upsert_memory", None, session_id, "fact", "old value", None, 0.5, "{}")
    same = call(conn, "sp_upsert_memory", mid, session_id, "fact", "new value", None, 0.7, "{}")
    assert same == mid
    with conn.cursor() as cur:
        cur.execute("SELECT content, importance FROM memories WHERE id = %s", (mid,))
        content, importance = cur.fetchone()
    assert content == "new value"
    assert importance == pytest.approx(0.7)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM memories WHERE session_id = %s", (session_id,))
        assert cur.fetchone()[0] == 1, "update must not insert a duplicate row"


def test_upsert_memory_raises_on_unknown_id(conn, session_id):
    with pytest.raises(psycopg.errors.RaiseException):
        call(conn, "sp_upsert_memory", 2_000_000_001, session_id, "fact", "ghost", None, 0.5, "{}")


# ---------------------------------------------------------------- sp_recall --

def test_recall_text_fallback_finds_relevant_memory(conn, session_id):
    call(conn, "sp_upsert_memory", None, session_id, "fact", "the staging database lives in eu-west-2", None, 0.5, "{}")
    call(conn, "sp_upsert_memory", None, session_id, "fact", "the office coffee machine is broken", None, 0.5, "{}")
    rows = call_table(conn, "sp_recall", session_id, None, "staging database", 5)
    assert rows, "trigram fallback returned nothing"
    assert "staging database" in rows[0][1]


def test_recall_without_query_returns_importance_ranked(conn, session_id):
    call(conn, "sp_upsert_memory", None, session_id, "fact", "low priority note", None, 0.1, "{}")
    call(conn, "sp_upsert_memory", None, session_id, "fact", "critical deploy key rotation", None, 0.99, "{}")
    rows = call_table(conn, "sp_recall", session_id, None, None, 5)
    assert rows[0][1] == "critical deploy key rotation"


# -------------------------------------------------------- sp_compact_session --

def test_compact_session_folds_messages_into_summary(conn, session_id):
    ids = [
        call(conn, "sp_append_message", session_id, "user", f"turn {i}", None, 5, "{}")
        for i in range(4)
    ]
    summary_id = call(conn, "sp_compact_session", session_id, "user discussed four turns", ids[2], 7)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content, covers_up_to_message_id FROM summaries WHERE id = %s",
            (summary_id,),
        )
        content, covers = cur.fetchone()
    assert content == "user discussed four turns"
    assert covers == ids[2]

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, is_summarized FROM messages WHERE session_id = %s ORDER BY id",
            (session_id,),
        )
        flags = dict(cur.fetchall())
    assert all(flags[i] for i in ids[:3]), "messages up to the cut must be summarized"
    assert flags[ids[3]] is False, "messages after the cut must stay raw"


def test_compact_session_rejects_foreign_message(conn, session_id):
    other = call(conn, "sp_append_message", session_id, "user", "mine", None, None, "{}")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO sessions (session_id) VALUES ('other-session') RETURNING session_id")
        other_sid = cur.fetchone()[0]
    try:
        with pytest.raises(psycopg.errors.RaiseException):
            call(conn, "sp_compact_session", other_sid, "bad", other, None)
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE session_id = %s", (other_sid,))


def test_compact_session_is_atomic_on_failure(conn, session_id):
    """Criterion 4: a failing compaction leaves history intact."""
    call(conn, "sp_append_message", session_id, "user", "keep me raw", None, None, "{}")
    with pytest.raises(psycopg.errors.RaiseException):
        call(conn, "sp_compact_session", session_id, "summary of nothing", 2_000_000_002, None)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM summaries WHERE session_id = %s", (session_id,))
        assert cur.fetchone()[0] == 0, "failed compaction must not leave a summary row"
        cur.execute(
            "SELECT count(*) FROM messages WHERE session_id = %s AND is_summarized",
            (session_id,),
        )
        assert cur.fetchone()[0] == 0, "failed compaction must not mark messages summarized"


# --------------------------------------------------------- sp_build_context --

def test_build_context_returns_sections_in_priority_order(conn, session_id):
    call(conn, "sp_upsert_memory", None, session_id, "fact", "a remembered fact", None, 0.9, "{}")
    mid = call(conn, "sp_append_message", session_id, "user", "first turn", None, 4, "{}")
    call(conn, "sp_compact_session", session_id, "earlier discussion", mid, 5)
    call(conn, "sp_append_message", session_id, "user", "current turn", None, 4, "{}")

    rows = call_table(conn, "sp_build_context", session_id, 8000)
    sections = [r[0] for r in rows]
    assert "summary" in sections and "memory" in sections and "message" in sections
    # priority order: summary before memory before skill before message
    rank = {"summary": 1, "memory": 2, "skill": 3, "message": 4}
    assert sections == sorted(sections, key=lambda s: rank[s])


def test_build_context_excludes_summarized_messages(conn, session_id):
    mid = call(conn, "sp_append_message", session_id, "user", "folded away", None, 4, "{}")
    call(conn, "sp_compact_session", session_id, "summary", mid, 4)
    call(conn, "sp_append_message", session_id, "user", "still live", None, 4, "{}")
    rows = call_table(conn, "sp_build_context", session_id, 8000)
    contents = [r[4] for r in rows if r[0] == "message"]
    assert "still live" in contents
    assert "folded away" not in contents


def test_build_context_trims_to_token_budget(conn, session_id):
    """Criterion 2: the function returns context ALREADY trimmed to budget."""
    for i in range(40):
        call(conn, "sp_append_message", session_id, "user", f"padded message number {i} " * 5, None, 50, "{}")

    generous = call_table(conn, "sp_build_context", session_id, 100_000)
    tight = call_table(conn, "sp_build_context", session_id, 200)

    assert len(tight) < len(generous), "tight budget must return fewer rows"
    assert sum(r[5] for r in tight) <= 200, "returned rows must fit the budget"


def test_build_context_zero_budget_returns_nothing(conn, session_id):
    call(conn, "sp_append_message", session_id, "user", "anything", None, 4, "{}")
    assert call_table(conn, "sp_build_context", session_id, 0) == []


def test_build_context_drops_oldest_turns_first(conn, session_id):
    """Eviction order: newest unsummarized turns survive a tight budget."""
    call(conn, "sp_append_message", session_id, "user", "OLDEST", None, 20, "{}")
    call(conn, "sp_append_message", session_id, "user", "NEWEST", None, 20, "{}")
    rows = call_table(conn, "sp_build_context", session_id, 20)
    contents = [r[4] for r in rows if r[0] == "message"]
    assert contents == ["NEWEST"]


def test_build_context_is_one_round_trip(conn, session_id):
    """Criterion 2: one call, one result set covering every section."""
    call(conn, "sp_append_message", session_id, "user", "hi", None, 2, "{}")
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sp_build_context(%s, %s)", (session_id, 8000))
        rows = cur.fetchall()
    assert rows
    assert len(rows[0]) == 6  # section, ord, ref_id, role, content, token_count
