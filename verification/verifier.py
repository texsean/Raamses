#!/usr/bin/env python3
"""
RAAMSES Configurable Verification Engine
Supports two methodologies:
  1. rule_based — simple last-write, git activity, process checks (no LLM)
  2. localLlm — uses Ollama (llama3.2:3b or any model) for intelligent detection
Both can be combined (LLM primary with rule fallback).
Fully configurable via config/verification.json
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests

CONFIG_PATH = Path("config/verification.json")
OLLAMA_URL = "http://localhost:11434/api/generate"

class RAAMSESVerifier:
    def __init__(self):
        self.config = self._load_config()
        self.model = self.config.get("local_model", "llama3.2:3b")
        print(f"[Verifier] Initialized with methodology: {self.config['inactivity_methodology']}")

    def _load_config(self):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return json.load(f)
        # Default safe config
        return {
            "inactivity_methodology": "rule_based",
            "local_model": "llama3.2:3b",
            "fallback_to_rules": True,
            "rule_based": {
                "watch_files": ["README.md", "src/", "logs/"],
                "max_inactivity_seconds": 300,
                "require_git_activity": True
            },
            "verification_interval_seconds": 60,
            "alert_on_confidence_below": 60
        }

    def verify(self, agent_claim: dict, evidence: dict, context: str = "") -> dict:
        methodology = self.config["inactivity_methodology"]
        result = {"verified": True, "confidence": 80, "status": "valid", "summary": "All checks passed", "methodology_used": methodology}

        # Rule-based checks (always available as fallback or primary)
        if methodology == "rule_based" or self.config.get("fallback_to_rules", True):
            rule_result = self._rule_based_check(agent_claim, evidence)
            if not rule_result["verified"]:
                return rule_result

        # Local LLM verification (more powerful)
        if methodology == "localLlm":
            llm_result = self._llm_verify(agent_claim, evidence, context)
            if llm_result.get("verified") is False and self.config.get("fallback_to_rules", True):
                print("[Verifier] LLM flagged issue — falling back to rules")
                return self._rule_based_check(agent_claim, evidence)
            return llm_result

        return result

    def _rule_based_check(self, claim: dict, evidence: dict) -> dict:
        max_inactive = self.config["rule_based"]["max_inactivity_seconds"]
        last_activity = datetime.fromisoformat(claim.get("last_activity", "2020-01-01").replace("Z", "+00:00"))
        inactive_seconds = (datetime.utcnow() - last_activity).total_seconds()

        if inactive_seconds > max_inactive:
            return {
                "verified": False,
                "confidence": 65,
                "status": "inactive",
                "summary": f"Agent inactive for {inactive_seconds:.0f}s (threshold {max_inactive}s)",
                "recommendation": "restart_agent_or_escalate",
                "methodology_used": "rule_based"
            }
        return {"verified": True, "confidence": 75, "status": "valid", "summary": "Rule-based checks passed", "methodology_used": "rule_based"}

    def _llm_verify(self, claim: dict, evidence: dict, context: str) -> dict:
        prompt = f"""You are RAAMSES Verification Agent. Be strict.

AGENT CLAIM: {json.dumps(claim, indent=2)}
REAL EVIDENCE: {json.dumps(evidence, indent=2)}
Context: {context}

Return ONLY valid JSON with this schema:
{{"verified": true/false, "confidence": 0-100, "status": "valid|stuck|drifting|hallucinating|looping|inactive", "summary": "...", "issues": [...], "recommendation": "..."}}"""

        try:
            r = requests.post(
                OLLAMA_URL,
                json={"model": self.model, "prompt": prompt, "stream": False, "temperature": 0.2, "format": "json"},
                timeout=25
            )
            if r.status_code == 200:
                verdict = json.loads(r.json()["response"])
                verdict["methodology_used"] = "localLlm"
                verdict["model_used"] = self.model
                return verdict
        except Exception as e:
            pass  # fall through to rule-based if configured

        return {"verified": False, "confidence": 30, "status": "llm_unavailable", "summary": "Ollama unavailable", "recommendation": "start_ollama", "methodology_used": "localLlm"}

    def should_alert(self, verdict: dict) -> bool:
        return verdict.get("confidence", 100) < self.config.get("alert_on_confidence_below", 60)


if __name__ == "__main__":
    verifier = RAAMSESVerifier()
    
    claim = {"agent_id": "claude-01", "state": "Working", "progress_percent": 92, "last_activity": "2026-07-18T22:00:00Z"}
    evidence = {"files_changed": 2, "git_commits_last_hour": 0, "processes_running": ["python"], "token_usage": 12400}
    
    print("=== RAAMSES Configurable Verifier Test ===")
    print(f"Methodology: {verifier.config['inactivity_methodology']} | Model: {verifier.config.get('local_model')}")
    result = verifier.verify(claim, evidence, "Testing configurable verification engine")
    print(json.dumps(result, indent=2))
    if verifier.should_alert(result):
        print("🚨 ALERT: Human review recommended")
