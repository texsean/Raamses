#!/usr/bin/env python3
"""
RAAMSES Configurable Verification Engine
Supports two inactivity/verification methodologies:
  - FILEbased: Simple last-modified timestamp monitoring on user-defined files
  - LocalLLM: Uses local Ollama model (llama3.2:3b or similar) for intelligent detection of loops, hallucination, drift
"""

import json
import requests
import yaml
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

CONFIG_PATH = Path("config.yaml")

class RaamsesVerifier:
    def __init__(self):
        self.config = self._load_config()
        self.method = self.config["verification"]["inactivity_methodology"]
        self.model = self.config["verification"].get("local_model", "llama3.2:3b")
        self.ollama_url = "http://localhost:11434/api/generate"
        print(f"RAAMSES Verifier initialized with methodology: {self.method} (model: {self.model})")

    def _load_config(self) -> Dict:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return yaml.safe_load(f)
        return {
            "verification": {
                "inactivity_methodology": "LocalLLM",
                "local_model": "llama3.2:3b",
                "poll_interval_seconds": 30,
                "confidence_threshold": 65,
                "file_monitor": []
            }
        }

    def check_file_based(self, files: List[str]) -> Dict[str, Any]:
        """Simple last-write-time monitoring."""
        issues = []
        now = datetime.utcnow()
        
        for fpath in files:
            path = Path(fpath)
            if not path.exists():
                issues.append(f"Monitored file not found: {fpath}")
                continue
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = (now - mtime).total_seconds() / 60  # minutes
            if age > 15:  # configurable threshold later
                issues.append(f"File {path.name} has not been updated in {age:.1f} minutes")
        
        if issues:
            return {
                "verified": False,
                "confidence": 80,
                "status": "inactivity_detected",
                "summary": "Agent appears inactive based on file timestamps.",
                "issues": issues,
                "recommendation": "trigger_alert_or_restart",
                "method": "FILEbased"
            }
        return {"verified": True, "confidence": 90, "status": "active", "method": "FILEbased"}

    def verify_with_llm(self, agent_claim: Dict, evidence: Dict, context: str = "") -> Dict:
        """Intelligent verification using local Ollama."""
        prompt = f"""You are an independent RAAMSES Verification Agent.
Analyze whether this agent is legitimate, stuck, drifting, looping, or hallucinating.

AGENT CLAIM:
{json.dumps(agent_claim, indent=2)}

REAL EVIDENCE:
{json.dumps(evidence, indent=2)}

Context: {context}

Return ONLY valid JSON matching this schema:
{{
  "verified": true/false,
  "confidence": 0-100,
  "status": "valid|stuck|drifting|hallucinating|looping|blocked|inactive",
  "summary": "one sentence",
  "issues": ["bullet list"],
  "recommendation": "escalate|restart-agent|human-review|mute|ignore",
  "evidence_gaps": ["list of mismatches"]
}}"""

        try:
            resp = requests.post(
                self.ollama_url,
                json={"model": self.model, "prompt": prompt, "stream": False, "temperature": 0.3, "format": "json"},
                timeout=45
            )
            if resp.status_code == 200:
                result = resp.json()
                verdict = json.loads(result.get("response", "{}"))
                verdict.update({
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "model_used": self.model,
                    "method": "LocalLLM"
                })
                return verdict
        except Exception as e:
            return {"verified": False, "confidence": 0, "status": "llm_error", "summary": str(e), "method": "LocalLLM"}

        return {"verified": False, "confidence": 30, "status": "llm_unavailable", "method": "LocalLLM"}

    def verify(self, agent_claim: Dict, evidence: Dict = None, context: str = "") -> Dict:
        """Main entry point — chooses methodology from config."""
        if self.method == "FILEbased":
            files = self.config["verification"].get("file_monitor", [])
            return self.check_file_based(files)
        else:
            return self.verify_with_llm(agent_claim, evidence or {}, context)


# Test when run directly
if __name__ == "__main__":
    verifier = RaamsesVerifier()
    
    claim = {
        "agent_id": "claude-code-worker",
        "state": "Working",
        "progress_percent": 92,
        "task": "Building RAAMSES Android client"
    }
    
    evidence = {
        "last_file_write": "2026-07-18T21:55:00Z",
        "git_commits_today": 0,
        "processes_running": ["ollama", "python"],
        "token_burn_rate": "very_high"
    }
    
    result = verifier.verify(claim, evidence, "Testing configurable verification engine")
    print(json.dumps(result, indent=2))
