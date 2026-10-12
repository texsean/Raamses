"""Learning layer (migration 0007) — stored functions via the repository.

Covers matching, counting, ranking, promotion, feedback/demotion, agent_id
scoping and stats against a live Postgres. Skips cleanly when no server is
reachable. Each test uses a unique agent_id, so tests never see each other's
problems and cleanup is one DELETE per agent.

    RAAMSES_DSN=postgresql://... pytest tests/raamses/test_learning_layer.py
"""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")

from raamses import dual_llm  # noqa: E402
from raamses.dual_llm import DualLLMConfig  # noqa: E402
from raamses.repository import RaamsesRepository  # noqa: E402

DSN = os.environ.get(
    "RAAMSES_DSN",
    "postgresql://raamses:raamses_dev_password@localhost:55432/raamses",
)

Q = "How do I rotate the API key for the staging gateway?"
A = "Run `gw keys rotate --env staging`, then restart the gateway service."


@pytest.fixture(scope="module")
def pool():
    from psycopg_pool import ConnectionPool

    try:
        p = ConnectionPool(DSN, min_size=1, max_size=4, open=True,
                           kwargs={"autocommit": True}, timeout=5)
        with p.connection() as conn:
            conn.execute("SELECT 1")
            if conn.execute("SELECT to_regclass('problems')").fetchone()[0] is None:
                pytest.skip("migration 0007 not applied")
    except pytest.skip.Exception:
        raise
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no Postgres at {DSN}: {exc}")
    yield p
    p.close()


@pytest.fixture
def repo(pool):
    return RaamsesRepository(pool=pool)


@pytest.fixture
def agent_ids(repo):
    made = []

    def new():
        made.append(f"test-agent-{uuid.uuid4().hex[:12]}")
        return made[-1]

    yield new
    with repo._pool_or_default().connection() as conn:
        for aid in made:
            conn.execute("DELETE FROM problems WHERE agent_id = %s", (aid,))


@pytest.fixture
def session(repo):
    sid = repo.create_session(f"learn-test-{uuid.uuid4().hex[:12]}")
    yield sid
    with repo._pool_or_default().connection() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = %s", (sid,))


def _q(repo, sql, *args):
    with repo._pool_or_default().connection() as conn:
        return conn.execute(sql, args).fetchall()


def test_record_creates_problem_and_counts(repo, agent_ids, session):
    aid = agent_ids()
    r1 = repo.learn_record(aid, session, Q, A, model="main-test", promote_after=3,
                           prompt_tokens=1200, completion_tokens=80)
    assert r1.main_answers == 1 and not r1.promoted
    # Differently worded/cased/punctuated question lands on the same problem.
    r2 = repo.learn_record(aid, session, "how do I rotate the api key for the staging gateway", A,
                           promote_after=3)
    assert r2.problem_id == r1.problem_id and r2.main_answers == 2
    # Identical answer text bumps times_given instead of adding a row.
    assert r2.solution_id == r1.solution_id
    assert _q(repo, "SELECT times_given FROM solutions WHERE id = %s", r1.solution_id)[0][0] == 2
    hits = _q(repo, "SELECT route, prompt_tokens FROM problem_hits WHERE problem_id = %s ORDER BY id",
              r1.problem_id)
    assert hits == [("main", 1200), ("main", None)]


def test_promotes_at_threshold_and_serves_ranked(repo, agent_ids, session):
    aid = agent_ids()
    for _ in range(2):
        rec = repo.learn_record(aid, session, Q, A, promote_after=3)
        assert not rec.promoted
        assert repo.learn_solutions(rec.problem_id) == []   # not promoted: nothing served
    rec = repo.learn_record(aid, session, Q, "Use the gateway CLI: gw keys rotate --env staging.",
                            promote_after=3)
    assert rec.promoted
    match = repo.learn_match(aid, Q)
    assert match.problem_id == rec.problem_id and match.promoted and match.similarity == pytest.approx(1.0)
    sols = repo.learn_solutions(rec.problem_id, k=3)
    # The answer given twice outranks the one-off.
    assert [s.rank for s in sols] == [1, 2] and sols[0].answer == A
    assert sols[0].score > sols[1].score


def test_unrelated_question_does_not_match(repo, agent_ids, session):
    aid = agent_ids()
    repo.learn_record(aid, session, Q, A)
    assert repo.learn_match(aid, "What is the capital of Australia and why was it chosen?") is None


def test_merge_threshold_keeps_near_misses_apart(repo, agent_ids, session):
    """Serving matches loosely (0.6); recording merges only near-identical wording (0.8)."""
    aid = agent_ids()
    staging = repo.learn_record(aid, session, Q, A, threshold=0.8)
    near_miss = "How do I rotate the API key for the production gateway?"
    assert repo.learn_match(aid, near_miss, 0.6).problem_id == staging.problem_id
    prod = repo.learn_record(aid, session, near_miss, "Run `gw keys rotate --env prod`.", threshold=0.8)
    assert prod.problem_id != staging.problem_id
    reworded = repo.learn_record(aid, session, "How can I rotate the staging gateway API key?", A,
                                 threshold=0.75)
    assert reworded.problem_id == staging.problem_id


def test_agent_scoping(repo, agent_ids, session):
    a1, a2 = agent_ids(), agent_ids()
    for _ in range(3):
        repo.learn_record(a1, session, Q, A, promote_after=3)
    assert repo.learn_match(a1, Q).promoted
    assert repo.learn_match(a2, Q) is None


def test_downvote_demotes_when_nothing_servable(repo, agent_ids, session):
    aid = agent_ids()
    rec = None
    for _ in range(3):
        rec = repo.learn_record(aid, session, Q, A, promote_after=3)
    assert rec.promoted
    # times_given 3 -> score 3; four downvotes push it to 3 - 12 < 0.
    still = True
    for _ in range(4):
        still = repo.learn_feedback(rec.solution_id, -1)
    assert still is False
    assert not repo.learn_match(aid, Q).promoted
    assert repo.learn_solutions(rec.problem_id) == []


def test_demote_restarts_counter(repo, agent_ids, session):
    aid = agent_ids()
    for _ in range(3):
        rec = repo.learn_record(aid, session, Q, A, promote_after=3)
    assert repo.learn_demote(rec.problem_id)
    m = repo.learn_match(aid, Q)
    assert not m.promoted and m.main_answers == 0
    again = repo.learn_record(aid, session, Q, A, promote_after=3)
    assert again.main_answers == 1 and not again.promoted


def test_ttl_hides_stale_solutions(repo, agent_ids, session):
    aid = agent_ids()
    for _ in range(3):
        rec = repo.learn_record(aid, session, Q, A, promote_after=3)
    with repo._pool_or_default().connection() as conn:
        conn.execute("UPDATE solutions SET last_given_at = now() - interval '40 days' WHERE problem_id = %s",
                     (rec.problem_id,))
    assert repo.learn_rank(rec.problem_id, 30) == 0
    assert repo.learn_solutions(rec.problem_id, ttl_days=30) == []
    assert len(repo.learn_solutions(rec.problem_id, ttl_days=None)) == 0  # rank cleared by the re-rank
    assert repo.learn_rank(rec.problem_id, None) == 1


def test_log_hit_and_stats(repo, agent_ids, session):
    aid = agent_ids()
    for _ in range(3):
        rec = repo.learn_record(aid, session, Q, A, promote_after=3, prompt_tokens=1000, completion_tokens=50)
    repo.learn_log_hit(rec.problem_id, session, "local", rec.solution_id, 0.9, "local-test")
    repo.learn_log_hit(rec.problem_id, session, "local_declined", rec.solution_id, 0.7, "local-test")
    stats = {s.route: s for s in repo.learn_stats(aid)}
    assert stats["main"].turns == 3 and stats["main"].prompt_tokens == 3000
    assert stats["local"].turns == 1 and stats["local_declined"].turns == 1
    assert _q(repo, "SELECT local_answers FROM problems WHERE id = %s", rec.problem_id)[0][0] == 1


def test_log_hit_rejects_main_route(repo, agent_ids, session):
    import psycopg

    aid = agent_ids()
    rec = repo.learn_record(aid, session, Q, A)
    with pytest.raises(psycopg.errors.RaiseException):
        repo.learn_log_hit(rec.problem_id, session, "main")


def test_deleting_session_keeps_learned_answers(repo, agent_ids):
    aid = agent_ids()
    sid = repo.create_session(f"learn-test-{uuid.uuid4().hex[:12]}")
    rec = repo.learn_record(aid, sid, Q, A)
    with repo._pool_or_default().connection() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = %s", (sid,))
    assert repo.learn_match(aid, Q).problem_id == rec.problem_id


def test_unknown_session_id_is_tolerated(repo, agent_ids):
    rec = repo.learn_record(agent_ids(), "no-such-session", Q, A)
    assert rec.main_answers == 1


def test_router_end_to_end(repo, agent_ids, session):
    """observe_turn x3 -> promoted -> try_local_turn serves from the DB."""
    from types import SimpleNamespace

    cfg = DualLLMConfig(enabled=True, agent_id=agent_ids(), promote_after=3,
                        local_base_url="http://localhost:11434/v1", local_model="local-test")
    persisted = []
    agent = SimpleNamespace(session_id=session, model="main-test", platform="cli",
                            session_prompt_tokens=0, session_completion_tokens=0,
                            context_compressor=SimpleNamespace(last_prompt_tokens=0),
                            _persist_session=lambda m, h=None: persisted.append(m))
    result = {"final_response": A, "completed": True, "messages": [], "model": "main-test"}
    for _ in range(3):
        dual_llm.observe_turn(agent, Q, [], result, cfg=cfg, repo=repo)

    seen = []
    out = dual_llm.try_local_turn(agent, Q, [], cfg=cfg, repo=repo,
                                  local_call=lambda c, m: seen.append(m) or A)
    assert out is not None and out["route"] == "local" and out["final_response"] == A
    assert A in seen[0][1]["content"]
    stats = {s.route: s.turns for s in repo.learn_stats(cfg.agent_id)}
    assert stats == {"main": 3, "local": 1}
