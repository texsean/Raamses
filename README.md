# RAAMSES — Remote AI Agent Monitoring & System Event Supervisor

**RAAMSES custom Agent Console e-paper pager:**

![RAAMSES Pager](assets/file_00000000fd9081f5a079e45037d43f3d.png)

**NOTE**  
We are almost live!  
Today's date is 7/18/2026.

**Welcome to raamses.io**

We are going live on 9-01-2026.  
We are accepting beta tester applications! Email support@raamses.io. We need testers with hardware already ready to be flashed.

**Note:** If you download any firmware prior to launch, do so at your own risk.  
We have published the full API and include a Python server emulator (see `server-emulator/`) so you can test firmware immediately.

**Sean**

**Desktop AI Agent Console (With Gateway)**

![RAAMSES Desktop Agent Monitoring Console](assets/raamses-softwareconsole.png)

**Agent Console full 3x5" OLED display example:**

![RAAMSES OLED Agent Monitor](assets/file_00000000b34481f8955c178988114fe4.png)

**Mission Control for AI Agents**

"Friday, 6:12 PM. Your agent needs one decision. Without RAAMSES, it waits until Monday. With RAAMSES, your AI Operations Console vibrates, you select option A, and the work keeps going."

RAAMSES is a device sitting on your desk or an e-paper pager vibrating on your wrist or in your pocket.

**Watchy custom firmware, Agent Console example:**

![RAAMSES Logo Watchy](assets/file_00000000af8871fb8e9b328fceb2f571.png)

![RAAMSES Logo](assets/raamses-logo-highdpi.png)

🟢 All Agents Operational  
🟡 Claude waiting for approval  
🟠 Token usage abnormal  
🔴 Loop detected  
🔴 Disk space critical

## Ecosystem

RAAMSES Server  
├── Desktop AI Operations Console  
├── CYD AI Operations Console  
├── E-Paper AI Operations Console  
├── Mobile AI Operations Console  
└── Wearable AI Operations Console

Pressing a button immediately opens the details or approval screen. That is instantly understandable.

**Real-time visibility into your agentic systems.**

RAAMSES gives developers and DevOps engineers a beautiful, always-on dashboard for Hermes, Claude Code, and other autonomous agents. No more constantly checking Telegram or email.

**What the live console shows**

**LAST VERIFIED WORK**  
18 seconds ago

Editing: gateway.cpp  
Process: clang++  
CPU: 61%

“Verified” means the RAAMSES server observed an actual filesystem, process, tool, API, or source-control event — not a sentence supplied by the agent.

**Suggested states:**  
**ACTIVE** — verified event within 2 minutes  
**QUIET** — no verified event for 2–15 minutes

## Smart Verification Engine (NEW)

RAAMSES does not trust agent self-reports. It periodically polls status **and then independently verifies** using real telemetry (filesystem changes, git commits, process activity, tool calls, test results, token burn rate, etc.).

When discrepancies are detected, RAAMSES immediately escalates via console, pager, or alert with clear evidence.

A local Ollama instance (Qwen2.5 or similar) runs as an independent second brain to detect astray agents, hallucinated progress, subtle drift, or repeated identical claims with no actual output. This makes RAAMSES significantly more trustworthy and sets it apart from simple dashboards.

## Technical Foundation (Public)

- Full XML + JSON protocol (published in `/schemas/`)
- Python XML/JSON emulator (`server-emulator/`) for immediate testing
- Configurable Software Console that can emulate e-paper, CYD, desktop, or any other device via simple XML config files
- Unit test suite + `run-tests.sh` that runs against the emulator and software console in every simulated hardware mode (no physical device required)

**Schemas & API:** https://github.com/texsean/Raamses/tree/master/schemas

The full smart gateway (C# .NET 8 for Windows/Linux with Hermes/Claude integration) lives in the private `RaamsesServer` repository.

**Almost live.** Beta applications are open.

Contact: support@raamses.io

---

*RAAMSES — Powerful oversight for autonomous AI agents.*
