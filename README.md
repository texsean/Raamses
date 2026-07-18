# RAAMSES — Remote AI Agent Monitoring & System Event Supervisor

**RAAMSES custom Agent Console e-paper pager:**

![RAAMSES Pager](assets/file_00000000fd9081f5a079e45037d43f3d.png)

**NOTE**  
We are almost live!  
Today's date is **7/18/2026**.

**Welcome to raamses.io**

We are going live on **9-01-2026**.  
We are accepting beta tester applications! Email **support@raamses.io**. We need testers with hardware already ready to be flashed.

**Note:** If you download any firmware prior to launch, do so at your own risk.  
We have published the full API and include a Python server emulator (see `server-emulator/`) so you can test firmware immediately.

**Desktop AI Agent Console (With Gateway)**

![RAAMSES Desktop Agent Monitoring Console](assets/raamses-softwareconsole.png)

**Agent Console full 3x5" OLED display example:**

![RAAMSES OLED Agent Monitor](assets/file_00000000b34481f8955c178988114fe4.png)

**Mission Control for AI Agents**

> "Friday, 6:12 PM. Your agent needs one decision. Without RAAMSES, it waits until Monday. With RAAMSES, your AI Operations Console vibrates, you select option A, and the work keeps going."

RAAMSES is a device sitting on your desk or an e-paper pager vibrating on your wrist or in your pocket.

**Watchy custom firmware, Agent Console example:**

![RAAMSES Logo Watchy](assets/file_00000000af8871fb8e9b328fceb2f571.png)

![RAAMSES Logo](assets/raamses-logo-highdpi.png)

---

## Smart Verification Engine (New)

RAAMSES does not just ask agents for status — it **verifies**.

### Configurable Inactivity & Verification Methodology
The server is small enough to distribute and fully configurable:

```yaml
verification:
  enabled: true
  inactivity_methodology: "LocalLLM"   # or "FILEbased"
  local_model: "llama3.2:3b"
  poll_interval_seconds: 30
  file_monitor:
    - "C:/Agents/status/agent1.md"
    - "/home/pi/agent_output.log"
```

- **`FILEbased`** — Monitors last-write time of any files you define. Simple, zero-LLM, very lightweight.
- **`LocalLLM`** — Uses a local Ollama model (`llama3.2:3b` or similar) to detect loops, hallucination, drift, inactivity, or misleading claims by comparing self-reported status against real evidence (git, processes, files, test results, token usage).

This gives users the choice: run completely lightweight, or enable intelligent verification. The LLM is completely optional.

See `verification/ollama_verifier.py` and `config.yaml`.

## Published Resources
- Full XML + JSON protocol schemas: `/schemas/`
- Python XML/JSON emulator: `/server-emulator/`
- Configurable software console (e-paper, CYD, desktop modes): `/software-console/`
- Unit tests + `run-tests.sh` runner: `/unit-tests/`
- Verification engine with LocalLLM and FILEbased modes: `/verification/`

All agents (Linux gateway, Android console, desktop, etc.) will use the same consistent naming and verification approach.

**We are building the universal agentic interface — Mission Control + Telegram for AI agents and IoT devices.**

**Sean & Remy**  
Director of Development

---

🟢 All Agents Operational  
🟡 Claude waiting for approval  
🟠 Token usage abnormal  
🔴 Loop detected  
🔴 Disk space critical

## Ecosystem
- RAAMSES Server (Linux reference implementation on Pi 5)
- Desktop AI Operations Console
- CYD / E-Paper / Watchy Consoles
- Android Console (in progress)
- Local Ollama Verification Engine (optional but powerful)
