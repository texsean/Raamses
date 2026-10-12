"""RaamsesAgent — dual-LLM route over the learning layer (migration 0007).

The main model answers questions as usual. Every completed main-route answer is
recorded as a *solution* to a *problem* (the normalized question). Once a
problem has been answered ``promote_after`` times its solutions are ranked in
SQL and the problem is promoted; from then on a similar question is answered by
the configured local model from the top-ranked stored solutions, and the main
model is never called for that turn.

Two entry points, both called from :mod:`agent.turn_facade` and both fail-open
(any error means "use the main route", never a failed turn):

* :func:`try_local_turn` — before the main loop. Returns a finished turn result
  when the local route served it, else ``None``.
* :func:`observe_turn` — after a main-route turn. Records the answer.

Safety rails:

* The local model is reached only through an explicit ``dual_llm.local``
  endpoint. With no endpoint configured the route never serves, so it can never
  silently fall back to a paid provider.
* The local model may decline (reply ``NO_MATCH``) when the stored answers do
  not fit the question; the turn then falls through to the main route, which
  logs ``local_declined`` and records the fresh answer.
* Turns that used tools are not learned by default: their answers depend on
  live state (files, web, time) that a stored answer cannot see.
* Local answers are never stored as solutions, so the local model cannot
  reinforce its own output.

Configuration (config.yaml)::

    dual_llm:
      enabled: false
      agent_id: default          # learned answers are scoped per agent
      promote_after: 3           # main-route answers before the local route serves
      match_threshold: 0.6       # pg_trgm similarity to SERVE a stored problem locally
      merge_threshold: 0.8       # stricter similarity to RECORD an answer under an existing problem
      min_question_chars: 20     # shorter messages ("yes", "do it") are never matched
      ttl_days: 30               # solutions older than this are not served
      top_k: 3                   # ranked solutions handed to the local model
      learn_tool_turns: false
      local:
        base_url: http://localhost:11434/v1   # any OpenAI-compatible local server
        model: <local model name>
        api_key: ""              # most local servers ignore it
        timeout: 60

``RAAMSES_DUAL_LLM=1|0`` and ``RAAMSES_AGENT_ID`` override the config file.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

DECLINE_TOKEN = "NO_MATCH"
ROUTE_LOCAL = "local"

_LOCAL_SYSTEM_PROMPT = (
    "You answer a user's question using ONLY the verified answers provided. "
    "They were given earlier to the same or a very similar question and are "
    "ranked best first. Prefer the first; merge details from the others only "
    "when they agree. Answer directly, in the style of the verified answers, "
    "without mentioning that you were given them. If the verified answers do "
    f"not answer this exact question, reply with exactly {DECLINE_TOKEN} and "
    "nothing else."
)

# Session token keys mirrored from agent.turn_finalizer so a local-route result
# has the same shape as a main-route one.
_SESSION_TOKEN_KEYS = (
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
    "reasoning_tokens", "prompt_tokens", "completion_tokens", "total_tokens",
)
_SESSION_COST_KEYS = ("estimated_cost_usd", "cost_status", "cost_source")


# --------------------------------------------------------------- config ----

@dataclass(frozen=True)
class DualLLMConfig:
    enabled: bool = False
    agent_id: str = "default"
    promote_after: int = 3
    match_threshold: float = 0.6
    merge_threshold: float = 0.8
    min_question_chars: int = 20
    ttl_days: Optional[int] = 30
    top_k: int = 3
    learn_tool_turns: bool = False
    local_base_url: str = ""
    local_model: str = ""
    local_api_key: str = ""
    local_timeout: float = 60.0

    @property
    def local_configured(self) -> bool:
        return bool(self.local_base_url and self.local_model)


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _dual_llm_block() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config_readonly

        cfg = load_config_readonly() or {}
    except Exception:
        return {}
    block = cfg.get("dual_llm")
    return block if isinstance(block, dict) else {}


def load_config(block: Optional[Dict[str, Any]] = None) -> DualLLMConfig:
    """Build the config from ``dual_llm`` in config.yaml plus env overrides.

    Never raises: a malformed block disables the route instead of failing turns.
    """
    try:
        return _build_config(_dual_llm_block() if block is None else block)
    except Exception:
        logger.warning("dual_llm: invalid dual_llm config; route disabled", exc_info=True)
        return DualLLMConfig()


def _build_config(raw: Dict[str, Any]) -> DualLLMConfig:
    local = raw.get("local") if isinstance(raw.get("local"), dict) else {}
    enabled = _truthy(raw.get("enabled", False))
    if os.environ.get("RAAMSES_DUAL_LLM"):
        enabled = _truthy(os.environ["RAAMSES_DUAL_LLM"])
    ttl = raw.get("ttl_days", 30)
    return DualLLMConfig(
        enabled=enabled,
        agent_id=str(os.environ.get("RAAMSES_AGENT_ID") or raw.get("agent_id") or "default"),
        promote_after=max(1, int(raw.get("promote_after", 3))),
        match_threshold=float(raw.get("match_threshold", 0.6)),
        merge_threshold=float(raw.get("merge_threshold", 0.8)),
        min_question_chars=int(raw.get("min_question_chars", 20)),
        ttl_days=None if ttl in (None, "", 0) else int(ttl),
        top_k=max(1, int(raw.get("top_k", 3))),
        learn_tool_turns=_truthy(raw.get("learn_tool_turns", False)),
        local_base_url=str(local.get("base_url") or "").strip(),
        local_model=str(local.get("model") or "").strip(),
        local_api_key=str(local.get("api_key") or "").strip(),
        local_timeout=float(local.get("timeout", 60) or 60),
    )


# -------------------------------------------------------------- helpers ----

def question_text(user_message: Any, persist_user_message: Any = None) -> Optional[str]:
    """The text to learn/match on, or None when the turn is not a plain question.

    ``persist_user_message`` wins when given: it is the clean user text without
    API-only synthetic prefixes. Multimodal (list) messages are never matched.
    """
    for candidate in (persist_user_message, user_message):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _eligible(agent: Any, cfg: DualLLMConfig, question: Optional[str], moa_config: Any) -> bool:
    # Subagents and persistence-isolated forks (background review) share the
    # parent's session; only real user turns learn or get served locally.
    if getattr(agent, "platform", None) == "subagent" or getattr(agent, "_persist_disabled", False):
        return False
    return (
        cfg.enabled
        and not moa_config
        and question is not None
        and len(question) >= cfg.min_question_chars
    )


def _turn_used_tools(result: Dict[str, Any], history_len: int) -> bool:
    messages = result.get("messages") or []
    for msg in messages[history_len:]:
        if isinstance(msg, dict) and (msg.get("tool_calls") or msg.get("role") == "tool"):
            return True
    return False


def snapshot_tokens(agent: Any) -> Dict[str, int]:
    """Session token counters before a turn, so :func:`observe_turn` can diff."""
    return {
        key: int(getattr(agent, f"session_{key}", 0) or 0)
        for key in ("prompt_tokens", "completion_tokens")
    }


def _repo():
    from raamses.repository import get_repository

    return get_repository()


# ------------------------------------------------------------ local call ----

def build_local_messages(question: str, answers: Sequence[str]) -> List[Dict[str, str]]:
    numbered = "\n\n".join(f"[{i}] {a.strip()}" for i, a in enumerate(answers, 1))
    return [
        {"role": "system", "content": _LOCAL_SYSTEM_PROMPT},
        {"role": "user", "content": f"Question:\n{question}\n\nVerified answers (best first):\n\n{numbered}"},
    ]


def call_local_model(cfg: DualLLMConfig, messages: List[Dict[str, str]]) -> Optional[str]:
    """Ask the configured local endpoint. None when it declines or returns nothing."""
    from agent.auxiliary_client import call_llm, extract_content_or_reasoning

    response = call_llm(
        provider="custom",
        base_url=cfg.local_base_url,
        api_key=cfg.local_api_key or "no-key",
        model=cfg.local_model,
        messages=messages,
        temperature=0.2,
        timeout=cfg.local_timeout,
    )
    text = (extract_content_or_reasoning(response) or "").strip()
    if not text or text.upper().startswith(DECLINE_TOKEN):
        return None
    return text


# ------------------------------------------------------------ local turn ----

def _local_result(agent: Any, messages: List[Dict[str, Any]], answer: str, learn: Dict[str, Any]) -> Dict[str, Any]:
    """A turn result with the same keys as ``agent.turn_finalizer.finalize_turn``."""
    compressor = getattr(agent, "context_compressor", None)
    return {
        "final_response": answer,
        "last_reasoning": None,
        "messages": messages,
        "api_calls": 0,
        "completed": True,
        "turn_exit_reason": "dual_llm_local",
        "failed": False,
        "partial": False,
        "interrupted": False,
        "response_transformed": False,
        "pre_transform_response": None,
        "response_previewed": False,
        "model": getattr(agent, "model", None),
        "provider": getattr(agent, "provider", None),
        "base_url": getattr(agent, "base_url", None),
        **{key: getattr(agent, f"session_{key}", 0) for key in _SESSION_TOKEN_KEYS},
        "last_prompt_tokens": getattr(compressor, "last_prompt_tokens", 0) or 0,
        **{key: getattr(agent, f"session_{key}", None) for key in _SESSION_COST_KEYS},
        "service_tier": None,
        "session_id": getattr(agent, "session_id", None),
        "route": ROUTE_LOCAL,
        "dual_llm": learn,
    }


def try_local_turn(
    agent: Any,
    user_message: Any,
    conversation_history: Optional[List[Dict[str, Any]]],
    *,
    persist_user_message: Any = None,
    persist_user_timestamp: Optional[float] = None,
    persist_user_platform_id: Optional[str] = None,
    moa_config: Any = None,
    cfg: Optional[DualLLMConfig] = None,
    repo: Any = None,
    local_call: Optional[Callable[[DualLLMConfig, List[Dict[str, str]]], Optional[str]]] = None,
) -> Optional[Dict[str, Any]]:
    """Serve the turn from the local model when its question is promoted."""
    try:
        cfg = cfg or load_config()
        question = question_text(user_message, persist_user_message)
        if not _eligible(agent, cfg, question, moa_config) or not cfg.local_configured:
            return None
        repo = repo or _repo()
        session_id = str(getattr(agent, "session_id", "") or "") or None

        match = repo.learn_match(cfg.agent_id, question, cfg.match_threshold)
        if match is None or not match.promoted:
            return None
        solutions = repo.learn_solutions(match.problem_id, cfg.top_k, cfg.ttl_days)
        if not solutions:
            return None

        answer = (local_call or call_local_model)(
            cfg, build_local_messages(question, [s.answer for s in solutions])
        )
        top = solutions[0].solution_id
        if answer is None:
            repo.learn_log_hit(
                match.problem_id, session_id, "local_declined", top, match.similarity, cfg.local_model,
            )
            return None
        repo.learn_log_hit(
            match.problem_id, session_id, ROUTE_LOCAL, top, match.similarity, cfg.local_model,
            {"solution_ids": [s.solution_id for s in solutions]},
        )
    except Exception:
        logger.warning("dual_llm: local route failed; using main route", exc_info=True)
        return None

    history = list(conversation_history or [])
    messages = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": answer},
    ]
    # Mirror build_turn_context's per-turn persist state so the session flush
    # applies this turn's override (and never a stale one) to the right row.
    agent._persist_user_message_idx = len(history)
    agent._persist_user_message_override = persist_user_message
    agent._persist_user_message_timestamp = persist_user_timestamp
    agent._persist_user_message_platform_id = persist_user_platform_id
    try:
        agent._persist_session(messages, conversation_history)
    except Exception:
        logger.warning("dual_llm: persisting local turn failed", exc_info=True)
    learn = {
        "problem_id": match.problem_id,
        "solution_id": top,
        "similarity": match.similarity,
        "local_model": cfg.local_model,
    }
    return _local_result(agent, messages, answer, learn)


# --------------------------------------------------------------- observe ----

def observe_turn(
    agent: Any,
    user_message: Any,
    conversation_history: Optional[List[Dict[str, Any]]],
    result: Any,
    *,
    persist_user_message: Any = None,
    moa_config: Any = None,
    tokens_before: Optional[Dict[str, int]] = None,
    cfg: Optional[DualLLMConfig] = None,
    repo: Any = None,
):
    """Record a completed main-route answer. Returns the LearnRecord or None."""
    try:
        cfg = cfg or load_config()
        question = question_text(user_message, persist_user_message)
        if not _eligible(agent, cfg, question, moa_config) or not isinstance(result, dict):
            return None
        if result.get("route") == ROUTE_LOCAL:
            return None
        if not result.get("completed") or result.get("failed") or result.get("interrupted") or result.get("partial"):
            return None
        # Record what the model said, before display-only output hooks.
        answer = result.get("pre_transform_response") or result.get("final_response")
        if not isinstance(answer, str) or not answer.strip():
            return None
        if not cfg.learn_tool_turns and _turn_used_tools(result, len(conversation_history or [])):
            return None

        prompt_tokens = completion_tokens = None
        if tokens_before is not None:
            after = snapshot_tokens(agent)
            prompt_tokens = max(0, after["prompt_tokens"] - tokens_before.get("prompt_tokens", 0))
            completion_tokens = max(0, after["completion_tokens"] - tokens_before.get("completion_tokens", 0))

        repo = repo or _repo()
        return repo.learn_record(
            cfg.agent_id,
            str(getattr(agent, "session_id", "") or "") or None,
            question,
            answer.strip(),
            model=str(result.get("model") or getattr(agent, "model", "") or "") or None,
            # Recording is stricter than serving: "production gateway" vs "staging
            # gateway" is close enough for the local model to look (and decline),
            # but must never file a production answer under the staging problem.
            threshold=cfg.merge_threshold,
            promote_after=cfg.promote_after,
            ttl_days=cfg.ttl_days,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            metadata={"api_calls": result.get("api_calls")},
        )
    except Exception:
        logger.warning("dual_llm: recording main-route answer failed", exc_info=True)
        return None
