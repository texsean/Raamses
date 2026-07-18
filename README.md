# RAAMSES - Remote AI Agent Monitoring & System Event Supervisor

**Today's date: 7/18/2026**

**Welcome to raamses.io**

We're planning on going live **9-01-2026**. 

**We're accepting beta tester applications!** Email support@raamses.io. We need testers with hardware already ready to be flashed.

**Note:** If you download any firmware prior to launch, do so at your own risk.

I'll have a Python server emulator soon (see `server-emulator/` folder). This allows you to download firmware, install it on your devices, and test against the local Python mock without waiting for the full live service.

## Project Structure

- **firmware/** - All device firmware (CYD, ESP32 e-Paper watch, etc.) + public API specifications for talking to the server.
- **server-emulator/** - Python mock server (returns summary/fulldata JSON and XML, system metrics, token tracking, status bar logic). Use this for pre-launch testing.
- **logos/** - Official assets including the new 16-color version for e-paper.
- **docs/** - Public documentation and API guides.

The full smart gateway (C# .NET 8 for Windows/Linux, Hermes/Claude integration, device communication, private API details) lives in a **separate private repository/folder** (`RaamsesServer-Private`).

**Private repo contains:**
- Production server code (Windows service + Linux daemon versions)
- `internal-docs/` - Secret API specification (data formats, payload structures for summary vs fulldata, Hermes registration & forwarding, Claude messaging gateway, display command/response protocol, registration by connection status only — 1 hardware + 1 software free tier).

The public firmware can talk to either the Python emulator or the private production server using the same public API.

**Almost live!** Beta applications now open.

Contact: support@raamses.io

---
*RAAMSES — Powerful oversight for autonomous AI agents.*
