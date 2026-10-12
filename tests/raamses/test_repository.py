"""RaamsesAgent Phase 2 — repository layer tests.

Exercises :class:`raamses.RaamsesRepository` against a live Postgres. Skips
cleanly when no server is reachable, so the stock Hermes suite stays green on
machines without Docker.

    docker compose -f docker-compose.postgres.yml up -d
    pytest tests/raamses/test_repository.py
"""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")

from raamses import repository as repo_mod  # noqa: E402
from raamses.repository import (  # noqa: E402
    BACKEND_HERMES,
    BACKEND_RAAMSES,
    RaamsesRepository,
    RaamsesStorageError,
    backend_name,
    is_enabled,
    resolve_dsn,
)

DSN = os.environ.get(
    "RAAMSES_DSN",
    "postgresql://raamses:raamses_dev_password@localhost:55432/raamses",
)


@pytest.fixture(scope="module")
def pool():
    from psycopg_pool import ConnectionPool

    try:
        p = ConnectionPool(DSN, min_size=1, max_size=4, open=True,
                           kwargs={"autocommit": True}, timeout=5)
        with p.connection() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no Postgres at {DSN}: {exc}")
    yield p
    p.close()


@pytest.fixture
def repo(pool):
    return RaamsesRepository(pool=pool)


@pytest.fixture
def session(repo):
    sid = repo.create_session(f"repo-test-{uuid.uuid4().hex[:12]}")
    yield sid
    with repo._pool_or_default().connection() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = %s", (sid,))


# ------------------------------------------------------------ feature flag --

def test_backend_defaults_to_hermes(monkeypatch):
    monkeypatch.delenv("RAAMSES_BACKEND", raising=False)
    monkeypatch.setattr(repo_mod, "_storage_config", lambda: {})
    assert backend_name() == BACKEND_HERMES
    assert is_enabled() is False


def test_backend_flag_enables_postgres(monkeypatch):
    monkeypatch.delenv("RAAMSES_BACKEND", raising=False)
    monkeypatch.setattr(repo_mod, "_storage_config", lambda: {"backend": "raamses"})
    assert backend_name() == BACKEND_RAAMSES
    assert is_enabled() is True


def test_backend_env_var_overrides_config(monkeypatch):
    monkeypatch.setattr(repo_mod, "_storage_config", lambda: {"backend": "hermes"})
    monkeypatch.setenv("RAAMSES_BACKEND", "raamses")
    assert backend_name() == BACKEND_RAAMSES


def test_dsn_env_var_overrides_config(monkeypatch):
    monkeypatch.setattr(repo_mod, "_storage_config", lambda: {"dsn": "postgresql://cfg/x"})
    monkeypatch.setenv("RAAMSES_DSN", "postgresql://env/y")
    assert resolve_dsn() == "postgresql://env/y"


def test_storage_config_survives_missing_hermes_config(monkeypatch):
    """Importing the repo layer must never hard-fail on config problems."""
    import hermes_cli.config as hc

    def boom():
        raise RuntimeError("no config here")

    monkeypatch.setattr(hc, "load_config_readonly", boom)
    monkeypatch.delenv("RAAMSES_BACKEND", raising=False)
    assert backend_name() == BACKEND_HERMES


# ------------------------------------------------------- no raw SQL rule ----

def test_unknown_stored_function_is_rejected(repo):
    with pytest.raises(RaamsesStorageError):
        repo._scalar("DROP TABLE sessions; --")


def test_too_many_arguments_is_rejected(repo):
    with pytest.raises(RaamsesStorageError):
        repo._scalar("sp_get_session", "a", "b", "c")


def test_repository_module_contains_no_table_sql():
    """Charter rule: application code contains no raw SQL over the tables."""
    import inspect

    src = inspect.getsource(repo_mod)
    # The only permitted literal statements are stored-function calls and the
    # SELECT 1 liveness probe.
    for forbidden in ("INSERT INTO", "UPDATE sessions", "DELETE FROM", "CREATE TABLE"):
        assert forbidden not in src, f"raw SQL leaked into repository: {forbidden}"


# --------------------------------------------------------------- sessions ---

def test_ping(repo):
    assert repo.ping() is True


def test_create_and_get_session(repo, session):
    row = repo.get_session(session)
    assert row is not None
    assert row.session_id == session
    assert row.title is None
    assert row.status == "active"
    assert row.storage_backend == "raamses"


def test_get_unknown_session_returns_none(repo):
    assert repo.get_session("nonexistent-session-id") is None


def test_create_session_stores_metadata(repo):
    sid = repo.create_session(f"meta-{uuid.uuid4().hex[:8]}", metadata={"origin": "test"})
    try:
        assert repo.get_session(sid).metadata == {"origin": "test"}
    finally:
        with repo._pool_or_default().connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = %s", (sid,))


def test_end_session_sets_status_and_reason(repo, session):
    assert repo.end_session(session, "closed", "user_exit") is True
    row = repo.get_session(session)
    assert row.status == "closed"
    assert row.metadata.get("end_reason") == "user_exit"


def test_end_session_reason_is_first_wins(repo, session):
    repo.end_session(session, "closed", "first")
    repo.end_session(session, "closed", "second")
    assert repo.get_session(session).metadata["end_reason"] == "first"


def test_end_unknown_session_returns_false(repo):
    assert repo.end_session("nonexistent-session-id") is False


def test_list_sessions_counts_messages(repo, session):
    repo.append_message(session, "user", "one")
    repo.append_message(session, "assistant", "two")
    rows = [s for s in repo.list_sessions(limit=100) if s.session_id == session]
    assert rows and rows[0].message_count == 2


def test_list_sessions_filters_by_status(repo, session):
    repo.end_session(session, "archived")
    active = [s.session_id for s in repo.list_sessions(status="active", limit=200)]
    archived = [s.session_id for s in repo.list_sessions(status="archived", limit=200)]
    assert session not in active
    assert session in archived


# --------------------------------------------------------------- messages ---

def test_append_message_returns_id(repo, session):
    mid = repo.append_message(session, "user", "hello", token_count=2)
    assert isinstance(mid, int)


def test_append_message_with_metadata_and_parent(repo, session):
    root = repo.append_message(session, "user", "root")
    child = repo.append_message(session, "assistant", "child", parent_id=root,
                                metadata={"model": "opus"})
    ctx = repo.build_context(session, 8000)
    contents = [r.content for r in ctx if r.section == "message"]
    assert "child" in contents and "root" in contents
    assert child != root


# ------------------------------------------------------------- tool calls ---

def test_log_tool_call_roundtrip(repo, session):
    mid = repo.append_message(session, "assistant", "running tool")
    tid = repo.log_tool_call(session, "terminal", {"command": "ls"}, message_id=mid,
                             result={"exit_code": 0}, duration_ms=8.25)
    assert isinstance(tid, int)


def test_log_tool_call_error_status(repo, session):
    tid = repo.log_tool_call(session, "web_search", {}, status="error",
                             error_text="429 rate limited")
    assert isinstance(tid, int)


# ---------------------------------------------------------------- memories --

def test_upsert_memory_insert_then_update(repo, session):
    mid = repo.upsert_memory("first value", session_id=session, importance=0.4)
    same = repo.upsert_memory("second value", memory_id=mid, session_id=session,
                              importance=0.8)
    assert same == mid
    found = repo.recall(session_id=session, query_text="second value")
    assert found and found[0].content == "second value"


def test_recall_importance_ranking(repo, session):
    repo.upsert_memory("trivia", session_id=session, importance=0.1)
    repo.upsert_memory("the deploy key rotates monthly", session_id=session, importance=0.95)
    top = repo.recall(session_id=session)
    assert top[0].content == "the deploy key rotates monthly"


def test_recall_with_embedding_uses_vector_path(repo, session):
    vec_a = [0.0] * 1536
    vec_a[0] = 1.0
    vec_b = [0.0] * 1536
    vec_b[1] = 1.0
    repo.upsert_memory("vector A", session_id=session, embedding=vec_a)
    repo.upsert_memory("vector B", session_id=session, embedding=vec_b)
    hits = repo.recall(session_id=session, embedding=vec_a, k=2)
    assert hits[0].content == "vector A"
    assert hits[0].score > hits[1].score


def test_recall_returns_typed_rows(repo, session):
    repo.upsert_memory("typed row check", session_id=session, importance=0.9)
    hit = repo.recall(session_id=session)[0]
    assert isinstance(hit.memory_id, int)
    assert isinstance(hit.importance, float)
    assert isinstance(hit.score, float)


# -------------------------------------------------------------- compaction --

def test_compact_session_then_context_excludes_folded(repo, session):
    first = repo.append_message(session, "user", "old turn", token_count=4)
    repo.append_message(session, "user", "new turn", token_count=4)
    repo.compact_session(session, "summary of the old turn", first, 6)
    rows = repo.build_context(session, 8000)
    messages = [r.content for r in rows if r.section == "message"]
    summaries = [r.content for r in rows if r.section == "summary"]
    assert "new turn" in messages
    assert "old turn" not in messages
    assert summaries == ["summary of the old turn"]


def test_compact_session_rejects_unknown_message(repo, session):
    import psycopg

    with pytest.raises(psycopg.errors.RaiseException):
        repo.compact_session(session, "bad", 2_000_000_003)


# ----------------------------------------------------------- build_context --

def test_build_context_returns_typed_rows(repo, session):
    repo.append_message(session, "user", "hello", token_count=2)
    rows = repo.build_context(session, 8000)
    assert rows
    row = rows[0]
    assert isinstance(row.section, str)
    assert isinstance(row.token_count, int)


def test_build_context_respects_budget(repo, session):
    for i in range(30):
        repo.append_message(session, "user", f"message {i} " * 8, token_count=40)
    tight = repo.build_context(session, 200)
    assert RaamsesRepository.context_tokens(tight) <= 200


def test_context_tokens_helper(repo, session):
    repo.append_message(session, "user", "count me", token_count=7)
    rows = repo.build_context(session, 8000)
    assert RaamsesRepository.context_tokens(rows) == sum(r.token_count for r in rows)


# ------------------------------------------------------------ turn metrics --

def test_record_turn_metrics(repo, session):
    mid = repo.record_turn_metrics(session, 1, db_ms=3.5, model_ms=1200.0, tool_ms=45.0)
    assert isinstance(mid, int)


def test_record_turn_metrics_upserts_on_retry(repo, session):
    first = repo.record_turn_metrics(session, 7, db_ms=1.0)
    second = repo.record_turn_metrics(session, 7, db_ms=2.0)
    assert first == second, "same turn number must update, not duplicate"
