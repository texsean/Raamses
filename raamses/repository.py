"""RaamsesAgent — Postgres repository layer (Phase 2).

The ONLY module in the codebase that talks to Postgres. Charter architecture
rule: one function per stored procedure, psycopg3 with a connection pool,
application code above this layer contains no raw SQL.

Design notes
------------
* **Stored functions only.** Every method here issues exactly one
  ``SELECT sp_*(...)`` call. There is no ad-hoc SQL, no ORM, and no query
  building. If a new access pattern is needed, it gets a new stored function
  and a new method here — not a query in application code.
* **Explicit parameter casts.** psycopg sends untyped parameters as ``unknown``,
  which fails to resolve overloads against ``VECTOR``/``JSONB``/``REAL``
  signatures. ``_SIGNATURES`` declares the cast for each positional argument.
* **Lazy pool.** The pool opens on first use, not at import, so importing this
  module on a machine with no Postgres is free and stock Hermes is unaffected.
* **Feature flag.** ``storage.backend`` (``hermes`` | ``raamses``) decides
  whether anything calls into here at all; see :func:`backend_name` and
  :func:`is_enabled`.

Configuration (config.yaml)::

    storage:
      backend: raamses          # 'hermes' (default, stock SQLite) | 'raamses'
      dsn: postgresql://raamses:raamses_dev_password@localhost:55432/raamses
      pool_min_size: 1
      pool_max_size: 8

``RAAMSES_DSN`` in the environment overrides ``storage.dsn``.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_DSN = "postgresql://raamses:raamses_dev_password@localhost:55432/raamses"

BACKEND_HERMES = "hermes"
BACKEND_RAAMSES = "raamses"


class RaamsesStorageError(RuntimeError):
    """Raised when the Postgres backend is requested but unusable."""


# --------------------------------------------------------------- config ----

def _storage_config() -> Dict[str, Any]:
    """Read the ``storage`` block from Hermes config, tolerating any failure.

    Import is deferred and failure is swallowed on purpose: this module must be
    importable in tests and scripts that never load Hermes config at all.
    """
    try:
        from hermes_cli.config import load_config_readonly

        cfg = load_config_readonly() or {}
    except Exception:
        return {}
    storage = cfg.get("storage")
    return storage if isinstance(storage, dict) else {}


def backend_name() -> str:
    """Return the configured storage backend, defaulting to stock Hermes."""
    env = os.environ.get("RAAMSES_BACKEND")
    if env:
        return env.strip().lower()
    value = _storage_config().get("backend", BACKEND_HERMES)
    return str(value).strip().lower() or BACKEND_HERMES


def is_enabled() -> bool:
    """True when the Postgres state layer should serve the live path."""
    return backend_name() == BACKEND_RAAMSES


def resolve_dsn() -> str:
    return os.environ.get("RAAMSES_DSN") or str(_storage_config().get("dsn") or DEFAULT_DSN)


# ----------------------------------------------------------------- pool ----

_pool = None
_pool_lock = threading.Lock()


def get_pool():
    """Return the process-wide connection pool, opening it on first use."""
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is not None:
            return _pool
        try:
            from psycopg_pool import ConnectionPool
        except ImportError as exc:  # pragma: no cover - depends on install
            raise RaamsesStorageError(
                "psycopg[pool] is required for storage.backend=raamses: "
                "pip install 'psycopg[binary,pool]'"
            ) from exc

        cfg = _storage_config()
        _pool = ConnectionPool(
            resolve_dsn(),
            min_size=int(cfg.get("pool_min_size", 1) or 1),
            max_size=int(cfg.get("pool_max_size", 8) or 8),
            open=True,
            kwargs={"autocommit": True},
        )
        return _pool


def close_pool() -> None:
    """Close the pool (test teardown / process shutdown)."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


# ------------------------------------------------------------ call layer ----

# Positional parameter casts per stored function, in declaration order.
# Session ids are TEXT (Hermes timestamp strings), not UUID — see migration 0006.
_SIGNATURES: Dict[str, Sequence[str]] = {
    "sp_create_session": ("text", "text", "jsonb"),
    "sp_end_session": ("text", "text", "text"),
    "sp_get_session": ("text",),
    "sp_list_sessions": ("text", "integer"),
    "sp_record_turn_metrics": ("text", "integer", "numeric", "numeric", "numeric", "jsonb"),
    "sp_append_message": ("text", "text", "text", "bigint", "integer", "jsonb"),
    "sp_log_tool_call": (
        "text", "text", "jsonb", "bigint", "jsonb", "text", "text", "numeric",
    ),
    "sp_upsert_memory": ("bigint", "text", "text", "text", "vector(1536)", "real", "jsonb"),
    "sp_recall": ("text", "vector(1536)", "text", "integer"),
    "sp_compact_session": ("text", "text", "bigint", "integer"),
    "sp_build_context": ("text", "integer"),
    # Learning layer (dual-LLM route) — migration 0007.
    "sp_learn_match": ("text", "text", "real"),
    "sp_learn_record": (
        "text", "text", "text", "text", "text", "real", "integer", "integer",
        "integer", "integer", "jsonb",
    ),
    "sp_learn_rank": ("bigint", "integer"),
    "sp_learn_solutions": ("bigint", "integer", "integer"),
    "sp_learn_log_hit": ("bigint", "text", "text", "bigint", "real", "text", "jsonb"),
    "sp_learn_feedback": ("bigint", "integer", "integer"),
    "sp_learn_demote": ("bigint",),
    "sp_learn_stats": ("text", "timestamptz"),
}


def _placeholders(fn: str, count: int) -> str:
    try:
        casts = _SIGNATURES[fn][:count]
    except KeyError as exc:
        raise RaamsesStorageError(f"unknown stored function: {fn}") from exc
    if len(casts) != count:
        raise RaamsesStorageError(
            f"{fn} takes at most {len(_SIGNATURES[fn])} arguments, got {count}"
        )
    return ", ".join(f"%s::{cast}" for cast in casts)


def _jsonb(value: Any) -> str:
    """Normalize a dict/None into a JSONB-castable string."""
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _vector(value: Optional[Sequence[float]]) -> Optional[str]:
    """Render an embedding as pgvector literal text, or None."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return "[" + ",".join(repr(float(x)) for x in value) + "]"


# ----------------------------------------------------------- result rows ----

@dataclass(frozen=True)
class SessionRow:
    session_id: str
    title: Optional[str]
    status: str
    storage_backend: str
    metadata: Dict[str, Any]
    created_at: Any
    updated_at: Any


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    title: Optional[str]
    status: str
    message_count: int
    created_at: Any
    updated_at: Any


@dataclass(frozen=True)
class ContextRow:
    """One row of :meth:`RaamsesRepository.build_context`."""

    section: str          # 'summary' | 'memory' | 'skill' | 'message'
    ord: int
    ref_id: Optional[int]
    role: str
    content: str
    token_count: int


@dataclass(frozen=True)
class RecalledMemory:
    memory_id: int
    content: str
    kind: str
    importance: float
    score: float


@dataclass(frozen=True)
class ProblemMatch:
    """One row of :meth:`RaamsesRepository.learn_match`."""

    problem_id: int
    similarity: float
    main_answers: int
    promoted: bool


@dataclass(frozen=True)
class LearnRecord:
    """Result of :meth:`RaamsesRepository.learn_record`."""

    problem_id: int
    solution_id: int
    main_answers: int
    promoted: bool


@dataclass(frozen=True)
class RankedSolution:
    solution_id: int
    answer: str
    score: float
    rank: int


@dataclass(frozen=True)
class RouteStats:
    route: str              # 'main' | 'local' | 'local_declined'
    turns: int
    prompt_tokens: int
    completion_tokens: int


# ------------------------------------------------------------ repository ----

class RaamsesRepository:
    """One method per stored function. No SQL anywhere above this class."""

    def __init__(self, pool=None):
        self._pool = pool

    # -- plumbing ----------------------------------------------------------

    def _pool_or_default(self):
        return self._pool if self._pool is not None else get_pool()

    def _scalar(self, fn: str, *args):
        sql = f"SELECT {fn}({_placeholders(fn, len(args))})"
        with self._pool_or_default().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, args)
                row = cur.fetchone()
        return row[0] if row else None

    def _rows(self, fn: str, *args) -> List[tuple]:
        sql = f"SELECT * FROM {fn}({_placeholders(fn, len(args))})"
        with self._pool_or_default().connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, args)
                return cur.fetchall()

    def ping(self) -> bool:
        """True when the configured Postgres is reachable."""
        try:
            with self._pool_or_default().connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return cur.fetchone()[0] == 1
        except Exception:
            return False

    # -- sp_create_session / sp_end_session / sp_get_session ---------------

    def create_session(
        self,
        session_id: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create (upsert) a session with the caller-supplied Hermes id.

        Faithful to ``SessionDB.create_session``: the id is a timestamp string
        minted by the runtime (``20260912_113311_45eac8``), not generated here.
        """
        return str(self._scalar("sp_create_session", session_id, source, _jsonb(metadata)))

    def end_session(
        self,
        session_id: str,
        status: str = "closed",
        end_reason: Optional[str] = None,
    ) -> bool:
        """Close a session. ``end_reason`` is first-wins, as in stock Hermes."""
        return bool(self._scalar("sp_end_session", session_id, status, end_reason))

    def get_session(self, session_id: str) -> Optional[SessionRow]:
        rows = self._rows("sp_get_session", session_id)
        if not rows:
            return None
        r = rows[0]
        return SessionRow(str(r[0]), r[1], r[2], r[3], r[4], r[5], r[6])

    def list_sessions(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[SessionSummary]:
        rows = self._rows("sp_list_sessions", status, limit)
        return [SessionSummary(str(r[0]), r[1], r[2], int(r[3]), r[4], r[5]) for r in rows]

    # -- sp_record_turn_metrics -------------------------------------------

    def record_turn_metrics(
        self,
        session_id: str,
        turn_number: int,
        db_ms: float = 0.0,
        model_ms: float = 0.0,
        tool_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Criterion 5: log the per-turn timing split. Upserts on retry."""
        return self._scalar(
            "sp_record_turn_metrics",
            session_id, turn_number, db_ms, model_ms, tool_ms, _jsonb(metadata),
        )

    # -- sp_append_message -------------------------------------------------

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        parent_id: Optional[int] = None,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Append one message; returns its new id."""
        return self._scalar(
            "sp_append_message",
            session_id, role, content, parent_id, token_count, _jsonb(metadata),
        )

    # -- sp_log_tool_call --------------------------------------------------

    def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        message_id: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        status: str = "ok",
        error_text: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> int:
        return self._scalar(
            "sp_log_tool_call",
            session_id,
            tool_name,
            _jsonb(arguments),
            message_id,
            None if result is None else _jsonb(result),
            status,
            error_text,
            duration_ms,
        )

    # -- sp_upsert_memory --------------------------------------------------

    def upsert_memory(
        self,
        content: str,
        memory_id: Optional[int] = None,
        session_id: Optional[str] = None,
        kind: str = "fact",
        embedding: Optional[Sequence[float]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert a memory (``memory_id=None``) or update the row with that id."""
        return self._scalar(
            "sp_upsert_memory",
            memory_id, session_id, kind, content,
            _vector(embedding), importance, _jsonb(metadata),
        )

    # -- sp_recall ---------------------------------------------------------

    def recall(
        self,
        session_id: Optional[str] = None,
        embedding: Optional[Sequence[float]] = None,
        query_text: Optional[str] = None,
        k: int = 8,
    ) -> List[RecalledMemory]:
        """Vector recall when an embedding is given, trigram fallback on text,
        importance ranking when neither is supplied."""
        rows = self._rows("sp_recall", session_id, _vector(embedding), query_text, k)
        return [RecalledMemory(r[0], r[1], r[2], float(r[3]), float(r[4])) for r in rows]

    # -- sp_compact_session ------------------------------------------------

    def compact_session(
        self,
        session_id: str,
        summary_content: str,
        up_to_message_id: int,
        summary_tokens: Optional[int] = None,
    ) -> int:
        """Transactionally fold messages up to ``up_to_message_id`` into a summary."""
        return self._scalar(
            "sp_compact_session",
            session_id, summary_content, up_to_message_id, summary_tokens,
        )

    # -- sp_build_context --------------------------------------------------

    def build_context(self, session_id: str, token_budget: int = 8000) -> List[ContextRow]:
        """The money function: one round-trip, pre-trimmed to budget, in order."""
        rows = self._rows("sp_build_context", session_id, token_budget)
        return [ContextRow(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]

    @staticmethod
    def context_tokens(rows: Sequence[ContextRow]) -> int:
        """Total tokens in an assembled context — for ``turn_metrics``."""
        return sum(r.token_count for r in rows)

    # -- learning layer (dual-LLM route, migration 0007) -------------------

    def learn_match(
        self, agent_id: str, question: str, threshold: float = 0.6,
    ) -> Optional[ProblemMatch]:
        """Best stored problem for ``question`` within ``agent_id``, or None."""
        rows = self._rows("sp_learn_match", agent_id, question, threshold)
        if not rows:
            return None
        r = rows[0]
        return ProblemMatch(r[0], float(r[1]), r[2], bool(r[3]))

    def learn_record(
        self,
        agent_id: str,
        session_id: Optional[str],
        question: str,
        answer: str,
        model: Optional[str] = None,
        threshold: float = 0.6,
        promote_after: int = 3,
        ttl_days: Optional[int] = 30,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LearnRecord:
        """Store one main-route answer; ranks and promotes at ``promote_after``."""
        r = self._rows(
            "sp_learn_record",
            agent_id, session_id, question, answer, model, threshold, promote_after,
            ttl_days, prompt_tokens, completion_tokens, _jsonb(metadata),
        )[0]
        return LearnRecord(r[0], r[1], r[2], bool(r[3]))

    def learn_rank(self, problem_id: int, ttl_days: Optional[int] = 30) -> int:
        """Re-rank one problem's solutions; returns how many are rankable."""
        return self._scalar("sp_learn_rank", problem_id, ttl_days)

    def learn_solutions(
        self, problem_id: int, k: int = 3, ttl_days: Optional[int] = 30,
    ) -> List[RankedSolution]:
        """Top-k servable solutions of a promoted problem (empty if not promoted)."""
        rows = self._rows("sp_learn_solutions", problem_id, k, ttl_days)
        return [RankedSolution(r[0], r[1], float(r[2]), r[3]) for r in rows]

    def learn_log_hit(
        self,
        problem_id: int,
        session_id: Optional[str],
        route: str,
        solution_id: Optional[int] = None,
        similarity: Optional[float] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log a ``local`` or ``local_declined`` turn against a problem."""
        return self._scalar(
            "sp_learn_log_hit",
            problem_id, session_id, route, solution_id, similarity, model, _jsonb(metadata),
        )

    def learn_feedback(self, solution_id: int, vote: int, ttl_days: Optional[int] = 30) -> bool:
        """Vote +1/-1 on a solution; returns whether its problem is still promoted."""
        return bool(self._scalar("sp_learn_feedback", solution_id, vote, ttl_days))

    def learn_demote(self, problem_id: int) -> bool:
        """Send a problem back to the main route and restart its counter."""
        return bool(self._scalar("sp_learn_demote", problem_id))

    def learn_stats(self, agent_id: str, since: Any = None) -> List[RouteStats]:
        """Per-route turn counts and main-route tokens actually spent."""
        rows = self._rows("sp_learn_stats", agent_id, since)
        return [RouteStats(r[0], r[1], int(r[2] or 0), int(r[3] or 0)) for r in rows]


_repository: Optional[RaamsesRepository] = None
_repository_lock = threading.Lock()


def get_repository() -> RaamsesRepository:
    """Process-wide repository singleton."""
    global _repository
    if _repository is None:
        with _repository_lock:
            if _repository is None:
                _repository = RaamsesRepository()
    return _repository
