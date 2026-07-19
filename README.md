# RAAMSES — Remote AI Agent Monitoring & System Event Supervisor

**Last Updated:** 2026-07-18

**raamses.io** — The control plane for the agent economy.

## Vision
RAAMSES is more than a monitor. It is the **control plane** for autonomous AI agents.

- **v1** — Monitor agents from Hermes, Claude, Grok and others with independent verification.
- **v2** — Raamses-native agents that report structured evidence natively (no wrapper needed).
- **v3** — Agent marketplace where RAAMSES is the OS — every agent plugs directly into your console.

We are already on this trajectory with a launched domain, working firmware, CI-built Android app, Pi 5 Linux gateway in progress, and a verification engine that no one else has.

## Core Differentiator — Anti-Hallucination Verification
Most systems trust what agents say. RAAMSES **asks for status… then independently verifies**.

- Compares agent claims against real evidence (git state, files changed, processes, test results, token usage, logs).
- Uses configurable methodology: LocalLLM (Ollama), FILEbased (user-defined status files), auto, or lightweight blink checks.
- Flags hallucination, loops, drift, or inactivity with confidence score and recommendation.
- “Agent claims 85% complete — verified evidence shows 48%. Mismatch alert.”

This is a feature CTOs, DevOps leads, and CFOs will want yesterday. It is proprietary, private, and runs locally or with your chosen lightweight LLM.

**Configurable Local LLM Support**  
Choose your own model (`llama3.2:3b`, etc.) or let RAAMSES detect and use an existing one. Perfect for **detecting wasted tokens and inactive agents** without cloud dependency. Performance is guarded so slow models never block the gateway.

**Future Raamses-Native Agents**  
Our own agents will report structured evidence directly. No parsing, no wrappers — maximum accuracy and trust.

## Current Status
- **Firmware** — CYD, ESP32 e-paper watch, configurable software console (emulates any display size/type for testing).
- **Android App** — v1.0.2 APK building automatically on every tagged commit via GitHub CI (see RaamsesAndroid repo).
- **Desktop Console** — Linux htop-style terminal UI in progress (emulates small displays while remaining terminal-friendly).
- **Gateway/Server** — Python emulator with full XML/JSON protocol, scheduled verifier (30s poll), chat pass-through, `/sethome`, and generic gateway mode. C++ Linux reference implementation starting on Pi 5.
- **Verification Engine** — Live in all versions (Python, planned C++). Supports LocalLLM, FILEbased, auto, and blink modes.
- **Testing** — Hardware-independent with configurable software console + nightly automated test reports.

**Beta tester applications are open.** Email support@raamses.io (especially if you have hardware ready to flash).

**Note:** Pre-launch firmware and APKs are provided at your own risk.

## Technical Foundation
- **Protocol** — Clean XML/JSON envelope with capability negotiation. Consoles declare what they can do; the server chooses the right payload (summary for small displays, fulldata for desktop).
- **Schemas** — Published modular XSDs: https://github.com/texsean/Raamses/tree/master/schemas
- **Emulator** — Full-featured Python reference (XML + JSON, scheduled verification, chat pass-through). Use it to test consoles before the C++ server is complete.
- **Verifier** — Configurable local intelligence. See `verification/ollama_verifier.py` and `raamses-verifier.config`.
- **Repositories**
  - Public (firmware, emulator, schemas, docs): https://github.com/texsean/Raamses
  - Private (server, gateway, internal specs): https://github.com/texsean/RaamsesServer
  - Android: https://github.com/texsean/RaamsesAndroid (CI auto-builds signed APK on versioned commits)

## Quick Start
1. Clone the public repo.
2. Run the emulator: `cd server-emulator && python emulator.py`
3. Run the software console or Android app and point it at the emulator.
4. Test verification by sending agent status with realistic evidence.

**Nightly test reports and 6pm status updates are emailed to support@raamses.io.**

---

**RAAMSES — Evidence-based oversight for the agent economy.**

*Built with independent verification, configurable local intelligence, and a clear path to native agents and a marketplace.*

---
*All images and branding assets are preserved in the `/logos` and `/marketing` folders.*
