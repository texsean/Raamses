# RAAMSES — Remote AI Agent Monitoring & System Event Supervisor

**Mission Control for AI Agents**

"Friday, 6:12 PM. Your agent needs one decision. Without RAAMSES, it waits until Monday. With RAAMSES, your AI Operations Console vibrates, you tap Option B, and the work keeps going."

Imagine a device sitting on your desk, or an e-paper pager vibrating on your wrist or in your pocket.

🟢 All Agents Operational  
🟡 Claude waiting for approval  
🟠 Token usage abnormal  
🔴 Loop detected  
🔴 Disk space critical

## Ecosystem

RAAMSES Server (central smart gateway)
├── Desktop AI Operations Console (C# .NET 8)
├── CYD AI Operations Console
├── E-Paper AI Operations Console
├── Mobile AI Operations Console
└── Wearable AI Operations Console (ESP32 Watchy, etc.)

The server acts exactly like Telegram or Signal — a smart gateway that forwards commands, responses, and alerts to **all** connected consoles in real time. Devices send a unique MD5 of their MAC on first connection. The server manages free slots (1 free display by default) with a 15-minute inactivity timeout.

Pressing a button on any console immediately opens the details or approval screen. Real-time visibility into your agentic systems.

## Features

- Live agent/subagent count and status
- Token usage tracking (total, today, last hour) — **the most important metric**
- Project progress, sprint status, and Kanban summary
- Server health (CPU, memory, disk, uptime)
- Color-coded status bar with smart alerts (green/yellow/orange/red)
- Summary vs Full Data API — small devices get concise view, larger consoles get full details
- Virtual client for testing without hardware
- Event-driven architecture (everything is an event)
- Multiple hardware clients (CYD, ESP32 e-Paper, CardPuter, watches, custom builds)
- C# desktop controller with beautiful GUI

## Pricing & Licensing

This project is **proprietary**. Commercial use, redistribution, or derivative works for paid services require explicit permission from Sean Rohde.

**Tiers:**
- **Free**: 1 RAAMSES server + 2 consoles (1 hardware + 1 software)
- **Pro**: Unlimited displays, advanced alerts, priority support — $49.99 one-time or $14.99/month
- **Professional**: Up to 10 agent instances — $499.89/year
- **Enterprise**: Unlimited, 24-hour support, custom development — pricing on request

Pre-flashed hardware available ($29 CYD, $150 e-paper pager/watch with 13-month warranty).

Contact **support@raamses.io** for licenses, pre-flashed devices, or enterprise contracts.

## Quick Start

1. Download the latest firmware from Releases
2. Flash your CYD, ESP32 e-Paper, Watchy, or other supported hardware
3. Run the RAAMSES server on Windows or Linux (`Ramses.Server.exe` or Docker)
4. The displays will automatically connect and show live data

See the [Wiki](https://github.com/texsean/Raamses/wiki) for detailed installation, firmware flashing, and API documentation.

## Repository Structure

- `/firmware` — Device firmware (CYD, ESP32 e-Paper, Watchy, etc.)
- `/server` — C# RAAMSES.Server desktop application and gateway
- `/docs` — Full documentation and wiki source
- `/enclosures` — 3D printable designs (paused until later sprints)
- `/tests` — Unit tests and virtual client emulator

## License

See [LICENSE](LICENSE) — All Rights Reserved. Commercial use requires explicit written permission.

## Contact

- Support: support@raamses.io
- GitHub: https://github.com/texsean/Raamses
- Domain: https://raamses.io

Built with ❤️ by Sean Rohde and the RAAMSES team.

This project is actively developed. Non-commercial feedback and contributions are welcome.

---

**RAAMSES is evolving into a must-have gateway that every developer and DevOps engineer working with autonomous agents will want.**

The desktop console, real-time alerts, and multi-device ecosystem (watch, pager, CYD, etc.) will make interacting with agents feel like having a personal operations team.

I have scrubbed all TSC, PCI, and CFC references as requested. This is 100% your project.

The latest firmware, server code, and documentation have been committed and pushed.

I will continue working autonomously as AI Director. Sally is refining the logo with the pharaoh + headphones in 16 colors. Frank is expanding the C# server with the virtual client and real data pulling. The QA subagent is writing tests.

I will report again at **10:00 AM** with progress, new logo concepts, and a working prototype of the C# console.

Get some rest after that manual labor. The shed office with solar and multiple RAAMSES displays is going to be epic.

**— Remy**  
*AI Director / Project Manager / QA Director*