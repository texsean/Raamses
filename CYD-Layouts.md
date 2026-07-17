# Ramses CYD Screen Layouts v1.0
**Screen:** 240x320 TFT (rotation 1, landscape effective). Fonts: TFT_eSPI textSize(1)=8px height, (2)=16px. Prioritizes density per Lucky Miner reference (small fonts, high data). Tan = #D2B48C (TFT_ORANGE approx). Logo: 38x38px gold square with 'R'.

## Layout 1: Token & Agent Density (Max Data)
```
[ y=0-48 HEADER - bg #1a1a1a ]
[38x38 GOLD LOGO @ (5,5)]   RAMSES AGENT VIEW   [textSize=2, color TFT_CYAN @ (55,12)]

Tan separator: drawLine(0,56,239,56, TFT_ORANGE)  // thickness=3

[ y=68-200 DATA - textSize=1 (8px), labels TFT_LIGHTGREY, values TFT_WHITE, left x=8 right x=125 ]
Tokens Today     8740 (62%)     | Agents Active    3 (of 5)
Token Rate/hr    1240            | Subagents        14 (max 24)
Project Comp.    67%             | Sprint Prog.     4/7 (on track)
Last Alert       2h ago (low)    | Stuck Agents     0
Server           EPS-01 OK       | Mem Usage        41%

[ y=212-239 STATUS BAR ]
bg= TFT_DARKGREEN, text=TFT_WHITE, textSize=1
ALL AGENTS NOMINAL • 14:28 • WIFI OK • 41°C
```
**Colors:** Header cyan/white, data grey/white, status green. Font sizes: header 16px, data 8px. 10+ metrics.

## Layout 2: Sprint & Project Focus (Warning State)
```
[ y=0-48 HEADER - bg #1a1a1a ]
[38x38 GOLD LOGO @ (5,5)]   RAMSES AGENT VIEW   [textSize=2, color TFT_CYAN @ (55,12)]

Tan separator: drawLine(0,56,239,56, TFT_ORANGE)

[ y=68-190 DATA - textSize=1, labels TFT_LIGHTGREY @x=10, values dynamic color @x=130 ]
Project          PCI-SSS-2.0     | Completion     67% [yellow]
Sprint Status    5 of 8          | Days Left       3 [yellow]
Tokens (80%+)    18.4k / 23k     | Usage Trend     ↑↑ [orange]
Agents           4/5             | Subagents      19 active
Last Alert       High token use   | 11m ago        [orange]

[ y=205-239 STATUS BAR - ORANGE ]
bg=TFT_ORANGE, text=TFT_BLACK, textSize=1 @ center
WARNING: 82% TOKEN CAP • 3 SUBAGENTS STALLED • 14:29
```
**Colors:** Dynamic per metric (green/yellow/orange/red), status orange for 80%+ tokens. Emphasizes warnings per spec.

## Layout 3: Alert & Status Heavy (Error State)
```
[ y=0-48 HEADER - bg #1a1a1a ]
[38x38 GOLD LOGO @ (5,5)]   RAMSES AGENT VIEW   [textSize=2, color TFT_CYAN @ (55,12)]

Tan separator: drawLine(0,56,239,56, TFT_ORANGE)

[ y=68-195 DATA - textSize=1 (labels x=12 width=105 align right, values x=125), tight 11px line spacing ]
Agent Count      5               | Subagents     11/24
Token Usage      21.4k (93%)     | Peak Today    2.1k/hr [red]
Project          78%             | Sprint        6/7
Last Alert       Subagent #3 stuck 42m ago [red]
Server Health    DEGRADED        | Last Sync     8s ago
Active Projects  2               | Errors        1

[ y=208-239 STATUS BAR - RED ]
bg=TFT_RED, text=TFT_WHITE, textSize=1
ERROR: 1 STUCK AGENT • HIGH TOKEN 93% • CHECK SERVER • 14:30
```
**Colors:** Red for errors/stuck (status bar + affected values), orange for high usage. Max readability at 8-9px font. 3 status colors demonstrated.
```

**Implementation Notes (for CYD-Ramses.ino):**
- Use tft.setTextSize(1) for all data lines (best density, matches Lucky Miner).
- Exact y-positions above assume 240px height in rotation 1.
- Status bar height 32px, full width, color mapped: green=TFT_DARKGREEN, yellow=TFT_YELLOW, orange=TFT_ORANGE, red=TFT_RED.
- Update drawStatusBar() and updateDisplay() to match chosen layout. No fluff elements.