"""Dual-LLM route (raamses.dual_llm) — routing logic against a fake repository.

No Postgres needed: the repository is an in-memory stand-in with the same
method names as RaamsesRepository's learning-layer methods. The SQL side
(ranking, promotion, scoping) is covered in test_learning_layer.py.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from raamses import dual_llm
from raamses.dual_llm import DualLLMConfig
from raamses.repository import LearnRecord, ProblemMatch, RankedSolution

Q = "How do I rotate the API key for the staging gateway?"


def _cfg(**overrides) -> DualLLMConfig:
    base = dict(
        enabled=True, agent_id="a1", promote_after=2, min_question_chars=10,
        local_base_url="http://localhost:11434/v1", local_model="local-test",
    )
    base.update(overrides)
    return DualLLMConfig(**base)


class FakeRepo:
    """Exact-text matching; promotes after cfg.promote_after main answers."""

    def __init__(self):
        self.problems = {}   # (agent_id, question) -> dict
        self.hits = []

    def learn_match(self, agent_id, question, threshold=0.6):
        p = self.problems.get((agent_id, question))
        if p is None:
            return None
        return ProblemMatch(p["id"], 1.0, p["main"], p["promoted"])

    def learn_record(self, agent_id, session_id, question, answer, *, promote_after=3, **kw):
        p = self.problems.setdefault(
            (agent_id, question),
            {"id": len(self.problems) + 1, "main": 0, "promoted": False, "answers": []},
        )
        p["main"] += 1
        p["answers"].append(answer)
        if p["main"] >= promote_after:
            p["promoted"] = True
        self.hits.append(("main", p["id"], kw))
        return LearnRecord(p["id"], len(p["answers"]), p["main"], p["promoted"])

    def learn_solutions(self, problem_id, k=3, ttl_days=30):
        for p in self.problems.values():
            if p["id"] == problem_id and p["promoted"]:
                return [RankedSolution(i + 1, a, 1.0, i + 1) for i, a in enumerate(p["answers"][:k])]
        return []

    def learn_log_hit(self, problem_id, session_id, route, *args, **kw):
        self.hits.append((route, problem_id, kw))
        return len(self.hits)


class FakeAgent(SimpleNamespace):
    def __init__(self, **kw):
        attrs = dict(
            session_id="20261011_120000_abcdef", model="main-test", provider="custom",
            base_url="https://example.invalid/v1", platform="cli",
            session_prompt_tokens=0, session_completion_tokens=0,
            context_compressor=SimpleNamespace(last_prompt_tokens=0),
            persisted=[],
        )
        attrs.update(kw)
        super().__init__(**attrs)

    def _persist_session(self, messages, conversation_history=None):
        self.persisted.append(list(messages))


def _main_result(answer="Run `gw keys rotate --env staging`.", **kw):
    r = {"final_response": answer, "completed": True, "failed": False, "interrupted": False,
         "partial": False, "messages": [{"role": "user", "content": Q},
                                        {"role": "assistant", "content": answer}],
         "model": "main-test", "api_calls": 1}
    r.update(kw)
    return r


def _answer_main(agent, repo, cfg, history=None, **result_kw):
    before = dual_llm.snapshot_tokens(agent)
    agent.session_prompt_tokens += 1200
    agent.session_completion_tokens += 80
    return dual_llm.observe_turn(
        agent, Q, history or [], _main_result(**result_kw), tokens_before=before, cfg=cfg, repo=repo,
    )


def test_not_served_locally_until_promoted():
    agent, repo, cfg = FakeAgent(), FakeRepo(), _cfg()
    calls = []
    local = lambda c, m: calls.append(m) or "local answer"

    assert dual_llm.try_local_turn(agent, Q, [], cfg=cfg, repo=repo, local_call=local) is None
    rec = _answer_main(agent, repo, cfg)
    assert rec.main_answers == 1 and not rec.promoted
    assert dual_llm.try_local_turn(agent, Q, [], cfg=cfg, repo=repo, local_call=local) is None
    assert calls == []

    rec = _answer_main(agent, repo, cfg)
    assert rec.promoted


def test_promoted_question_served_by_local_model_and_persisted():
    agent, repo, cfg = FakeAgent(), FakeRepo(), _cfg()
    for _ in range(2):
        _answer_main(agent, repo, cfg)
    seen = []

    def local(c, messages):
        seen.append(messages)
        return "Run `gw keys rotate --env staging`."

    history = [{"role": "user", "content": "hi there, quick question"},
               {"role": "assistant", "content": "Sure."}]
    result = dual_llm.try_local_turn(agent, Q, history, cfg=cfg, repo=repo, local_call=local)

    assert result is not None
    assert result["route"] == "local" and result["api_calls"] == 0 and result["completed"]
    assert result["final_response"].startswith("Run")
    # The local model saw the question and the ranked stored answers.
    assert Q in seen[0][1]["content"] and "[1]" in seen[0][1]["content"]
    # The transcript keeps history and gains exactly this turn's pair.
    assert agent.persisted[-1][:2] == history
    assert [m["role"] for m in agent.persisted[-1][2:]] == ["user", "assistant"]
    assert agent._persist_user_message_idx == len(history)
    assert repo.hits[-1][0] == "local"


def test_local_decline_falls_through_and_is_logged():
    agent, repo, cfg = FakeAgent(), FakeRepo(), _cfg()
    for _ in range(2):
        _answer_main(agent, repo, cfg)
    result = dual_llm.try_local_turn(agent, Q, [], cfg=cfg, repo=repo, local_call=lambda c, m: None)
    assert result is None
    assert repo.hits[-1][0] == "local_declined"
    assert agent.persisted == []


def test_local_failure_is_fail_open():
    agent, repo, cfg = FakeAgent(), FakeRepo(), _cfg()
    for _ in range(2):
        _answer_main(agent, repo, cfg)

    def boom(c, m):
        raise ConnectionError("local server down")

    assert dual_llm.try_local_turn(agent, Q, [], cfg=cfg, repo=repo, local_call=boom) is None


def test_main_route_tokens_are_recorded():
    agent, repo, cfg = FakeAgent(), FakeRepo(), _cfg()
    _answer_main(agent, repo, cfg)
    kw = repo.hits[-1][2]
    assert kw["prompt_tokens"] == 1200 and kw["completion_tokens"] == 80


@pytest.mark.parametrize(
    "cfg_kw, message, result_kw, agent_kw",
    [
        ({"enabled": False}, Q, {}, {}),
        ({}, "yes", {}, {}),                                   # too short to match safely
        ({}, [{"type": "text", "text": Q}], {}, {}),           # multimodal
        ({}, Q, {"failed": True}, {}),
        ({}, Q, {"interrupted": True}, {}),
        ({}, Q, {"route": "local"}, {}),                       # never learn from local answers
        ({}, Q, {"messages": [{"role": "assistant", "tool_calls": [{"id": "1"}]},
                              {"role": "tool", "content": "x"}]}, {}),
        ({}, Q, {}, {"platform": "subagent"}),
        ({}, Q, {}, {"_persist_disabled": True}),
    ],
)
def test_turns_that_are_never_learned(cfg_kw, message, result_kw, agent_kw):
    agent, repo, cfg = FakeAgent(**agent_kw), FakeRepo(), _cfg(**cfg_kw)
    rec = dual_llm.observe_turn(agent, message, [], _main_result(**result_kw), cfg=cfg, repo=repo)
    assert rec is None and repo.hits == []


def test_tool_turns_learned_when_opted_in():
    agent, repo, cfg = FakeAgent(), FakeRepo(), _cfg(learn_tool_turns=True)
    result = _main_result(messages=[{"role": "assistant", "tool_calls": [{"id": "1"}]}])
    assert dual_llm.observe_turn(agent, Q, [], result, cfg=cfg, repo=repo) is not None


def test_no_local_endpoint_never_serves():
    agent, repo = FakeAgent(), FakeRepo()
    cfg = _cfg(local_base_url="")
    for _ in range(2):
        _answer_main(agent, repo, cfg)
    assert dual_llm.try_local_turn(agent, Q, [], cfg=cfg, repo=repo, local_call=lambda c, m: "x") is None


def test_agents_do_not_share_learned_answers():
    agent, repo = FakeAgent(), FakeRepo()
    for _ in range(2):
        _answer_main(agent, repo, _cfg(agent_id="a1"))
    other = _cfg(agent_id="a2")
    assert dual_llm.try_local_turn(agent, Q, [], cfg=other, repo=repo, local_call=lambda c, m: "x") is None


def test_persist_user_message_is_the_match_text():
    assert dual_llm.question_text("[synthetic prefix] " + Q, Q) == Q
    assert dual_llm.question_text(Q) == Q
    assert dual_llm.question_text([{"type": "image"}]) is None


def test_load_config_defaults_and_env(monkeypatch):
    monkeypatch.delenv("RAAMSES_DUAL_LLM", raising=False)
    monkeypatch.delenv("RAAMSES_AGENT_ID", raising=False)
    cfg = dual_llm.load_config({})
    assert not cfg.enabled and cfg.agent_id == "default" and not cfg.local_configured

    monkeypatch.setenv("RAAMSES_DUAL_LLM", "1")
    monkeypatch.setenv("RAAMSES_AGENT_ID", "texsean-main")
    cfg = dual_llm.load_config({"local": {"base_url": "http://localhost:11434/v1", "model": "m"},
                                "ttl_days": 0})
    assert cfg.enabled and cfg.agent_id == "texsean-main" and cfg.local_configured
    assert cfg.ttl_days is None


def test_malformed_config_disables_route(monkeypatch):
    monkeypatch.setenv("RAAMSES_DUAL_LLM", "1")
    cfg = dual_llm.load_config({"promote_after": "three"})
    assert not cfg.enabled
