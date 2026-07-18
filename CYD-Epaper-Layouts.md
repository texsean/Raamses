# Ramses CYD 200x200 e-Paper Layouts v2.0
**Device:** 200x200 e-paper (monochrome with color overlays via EPD library or descriptive). Fonts: 8-12pt equivalent (small, crisp sans-serif like in Fitbit/Garmin). Permanent top status bar (always visible, 12px high). Header with stylized 'R' logo. Clean 2-column name:value pairs. Token usage ALWAYS priority #1 and most prominent. Color coding: Green=✓ nominal, Yellow=⚠ warning, Orange=▲ elevated, Red=✕ error (flash white-on-red for critical). No hard-coded/mock data — all fields use real agent detection placeholders e.g. {tokens_used}, {health_status}. Inspired by Fitbit (metric focus + gauge), Apple Watch (clean typography + tappable cards), Garmin (data fields + status), Lucky/Blotto Miner (compact high-info LCD with small fonts, permanent indicators).

**General Rules (all layouts):**
- Header: 20px high, logo left, agent type (Hermes/Claude) right.
- Status Bar (top, permanent): Thin bar with color-coded health pill, connectivity, time/battery equivalent.
- Main area: 2-col layout (label left ~40%, value right aligned). Small fonts (equiv 8-10pt for data, 12pt for headers).
- Navigation: Bottom 18px bar with ◀ ▶ or icons for pages (Status, Agents, Projects). Tappable areas highlighted with border or underline.
- Tap Behavior: Rows are interactive. Tapping a row (e.g. Subagents) expands inline or to modal view showing details (list of active agents, graphs if supported, logs). On e-paper, expansion uses full refresh with detailed panel.
- Commercial polish: Tight spacing, consistent alignment, hierarchy via font weight/bold, subtle dividers. Looks like premium smartwatch UI scaled to e-paper.

## Layout 1: Token-Centric Dashboard (Fitbit-inspired minimalism)
**Description:** Prominent token gauge at top (like Fitbit activity ring but bar for e-paper). Clean 2-col metrics below. Permanent status bar color-coded. Header with logo. Tap any metric row to expand into detailed breakdown (e.g. token history, per-agent usage). Intuitive bottom nav for switching to subagent list or project view. Polished with balanced whitespace, commercial font hierarchy.

ASCII Representation (scaled 200x200):
```
┌────────────────────────────────────┐  ← Permanent Status Bar (color: GREEN/YELLOW/ORANGE/RED)
│ {health} Hermes  ●  {conn}  {bat}% │
├────────────────────────────────────┤
│ [R] RAMSES MONITOR                 │  ← Header w/ logo (gold 'R' square)
│ Agent: {agent_type}   Sprint:{sprint}│
├───────────── Token Priority ───────┤
│ TOKENS     {tokens_used}/{limit}   │  ← Largest text, color-coded bar
│ ████████░░░░ {pct}%                │
├────────────────────────────────────┤
│ Project    {proj_name}      67%    │  ← 2-col name-value pairs (font~10)
│ Subagents  {active}/{max}     3/5  │
│ CPU        {cpu}%           23%    │
│ Memory     {mem_used}/8GB   2.1GB  │
│ Server     {health}        OK      │
├────────────────────────────────────┤
│ Tap row for details →              │  ← Example: tapping Subagents expands
└────────────────────────────────────┘
Bottom Nav: [Status] [Agents ▼] [Projects]   (tappable)

**Expanded View (after tapping Subagents row):**
┌────────────────────────────────────┐
│ SUBAGENTS DETAIL (3/5 active)     │  ← Full screen refresh on e-paper
│ • Claude-3.5 (tokens:1240)  GREEN │
│ • Hermes-v2  (tokens:890)   GREEN │
│ • Research   (idle)        YELLOW │
│ Total this sprint: 4.2k tokens    │
│ Back to overview                   │
└────────────────────────────────────┘
```

## Layout 2: Compact Data Grid (Garmin / Lucky Miner style)
**Description:** High information density like miner LCDs or Garmin data screens. 2-column pairs maximized. Token usage in dedicated prominent header section with color flash on warning. Permanent status bar at top with health color. Small fonts (8pt equiv) for max data. Logo integrated in header. Navigation via side taps or bottom dots. Tapping a row like "Server Health" expands to diagnostics (CPU breakdown, uptime, errors list). Very commercial, looks like enterprise monitoring device UI — precise alignment, no clutter.

ASCII Representation:
```
[STATUS BAR - permanent, bg=color by health: GREEN pill for OK]
{health_color} SERVER OK | Hermes | Proj:{name} | Sprint {sprint} | 14:32

┌───────[R LOGO] RAMSES CYD v2.0───────┐
│ TOKEN USAGE (Priority 1)             │
│ {tokens} / {limit}  [{bar}] {pct}%   │  ← Bold, large, color coded (red if >80%)
├──────────────────────────────────────┤
│ Agent Type   {type}     | Subagents {act}/{max} │
│ Project      {name}     | Completion {pct}%    │
│ CPU Load     {cpu}%     | Memory {used}MB      │
│ Server Hlth  {status}   | Last Sync {time}s    │
├──────────────────────────────────────┤
│ Navigation: ◀ Page 1/3 ▶ (Agents, Log)│
│ *Tap any row to expand details*      │
└──────────────────────────────────────┘

**Tap Expansion Example (on 'CPU Load' row):**
Full panel slides or replaces main area:
CPU DETAIL: 45% avg | Peak 67% (12:15)
- Main Agent: 28%
- Subagent-1: 12% (Claude)
- Subagent-2: 5%
Warnings: None
[Close]
```

## Layout 3: Card-Based Interactive (Apple Watch + Blotto Miner hybrid)
**Description:** Modern card UI like Apple Watch complications but in 2-col compact form for small screen. Header logo + agent type. Token as top card with gauge-like bar and large numbers. Status bar permanent with dynamic color (flashes red/white on error per spec). Clean dividers. Each row is a tappable card. Intuitive swipe or button nav. Polished commercial look with shadow simulation via borders, excellent contrast for e-paper. Prepares for real detection by using dynamic fields only. Expansion shows detailed modal-like view with more metrics or actions.

ASCII Representation:
```
┌──────────────────────────────────┐ ← Top Status (color-coded bg)
│ {color}● {health_status}  {agent}  {time} │
├──────────── HEADER ──────────────┤
│ [RAMSES] {logo}   Project: {name} │
│ Sprint {sprint}                  │
├────── TOKEN USAGE (P1) ──────────┤
│ {tokens_used} / {max}   {pct}%   │
│ [██████████▒▒ {bar}]   {trend}   │  ← Prominent colored bar
├──────────────────────────────────┤
│ Server Health   | {status} GREEN │ ← Tappable 2-col cards
│ Subagents       | {active}/{max} │
│ CPU / Memory    | {cpu}% / {mem}%│
│ Alerts          | {alert_count}  │
├──────────────────────────────────┤
│ [◀]  NAV  [Agents] [Projects] [▶] │ ← Intuitive nav
└──────────────────────────────────┘

**Tapping a Row (e.g. 'Alerts' or 'Subagents') expands to:**
[ EXPANDED DETAIL VIEW - replaces main content on tap ]
Subagents Active: {active}/{max}
────────────────────
1. Hermes-Research:  active, 1240 tokens, GREEN
2. Claude-Coding:    active, 890 tokens , GREEN
3. Analyzer:        paused , 0 tokens  , YELLOW
────────────────────
CPU: 34% | Mem: 1.8GB/8GB | Uptime: 14h
[ TAP TO COLLAPSE BACK ]
```

**Implementation Notes for e-Paper/Ramses:**
- Use small fonts (AdafruitGFX or U8g2 font sets equiv to 8-12px).
- Status bar redraw minimal to save e-paper refreshes.
- Color coding via text (GREEN text or inverted for red flash).
- For real agent detection: HTTP/JSON pull from stats_server.py for all {fields}.
- Tapping: Use touch on CYD or buttons; on pure e-paper use physical nav.
- Matches all requirements: permanent status, header/logo, token priority, 2-col, expansion demo, commercial polish, no mocks.

This file supersedes previous TFT layouts for the 200x200 e-paper target. Ready for Arduino/GxEPD2 implementation in next sprint.
