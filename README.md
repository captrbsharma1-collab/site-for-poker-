# ♠ Poker Decision Support Tool — Home Game Edition

A **Python-based, exploitative** poker reasoning assistant for live home games.
Tracks opponent tendencies, detects tilt, calculates pot odds, and delivers structured reasoning — never direct commands.

---

## Architecture

```
poker_tool/
├── observer.py   — Per-player stat tracking (pandas)
├── state.py      — Live game state (pot, stacks, street, SPR)
├── engine.py     — Opponent classifier, tilt detector, EV calc, exploit engine
├── ui.py         — Interactive terminal REPL
├── demo.py       — Simulated session showcase
└── README.md
```

---

## Quick Start

### Install dependency (optional but recommended)
```bash
pip install rich pandas
```
> `rich` enables colour-formatted terminal output. The tool works without it.

### Run the demo
```bash
cd poker_tool
python demo.py
```

### Run the interactive REPL
```bash
python ui.py
```

---

## REPL Command Reference

| Command | Description |
|---|---|
| `add <player> [stack]` | Register player (default 400 chips) |
| `update <player> <action> [size] [pot] [street]` | Log an action |
| `rebuy <player>` | Record rebuy (+400 chips) |
| `stack <player> <chips>` | Manually correct stack |
| `award <player> <chips>` | Award pot winnings |
| `pot <chips>` | Set pot size |
| `newhand <hero> <villain> [others...]` | Start new hand |
| `street [flop\|turn\|river] [cards...]` | Advance street |
| `board <cards...>` | Set community cards (e.g. `Ah Kd 7c`) |
| `herohand <card1> <card2>` | Set hero's hole cards |
| `analyse <villain> [call=N] [hand=strength]` | Full exploit analysis |
| `summary` | Session stats table |
| `json <villain>` | Raw JSON analysis output |
| `help` | Show all commands |

**Hand strength values:** `monster` / `strong` / `medium` / `weak` / `draw`

---

## Example Workflow

```
poker> add Wayne 400
poker> add Tim 400
poker> add Hero 400

poker> newhand Hero Wayne Tim

poker> update Wayne Raise 180 100 preflop
poker> update Tim Call 100 280 preflop
poker> update Hero Call 100 380 preflop

poker> street flop Ah 7d 2c
poker> pot 380

poker> update Wayne Bet 380 380 flop

poker> analyse Wayne call=380 hand=strong
```

---

## Stats Tracked (per player)

| Stat | Description |
|---|---|
| **VPIP** | Voluntarily Put $ In Pot (preflop, excl BB) |
| **PFR** | Preflop Raise % |
| **Fold to Bet %** | How often they fold when facing a bet/raise |
| **Call Frequency %** | How often they call when facing a bet |
| **Aggression Factor** | Bets+Raises / Calls (standard AF formula) |
| **Bet Sizing** | % of bets that are small / medium / large / overbet |
| **Buyins Lost** | Rebuy count (tilt detection input) |
| **Stack** | Current chip count |

---

## Player Classification

Players are classified on three axes:

- **Looseness**: Tight / Semi-Loose / Loose (by VPIP thresholds)
- **Aggression**: Passive / Balanced / Aggressive (by PFR and AF)
- **Bluff Tendency**: Value-Heavy / Balanced / Bluff-Heavy / Calling-Station

Combined label example: **Loose-Aggressive**

---

## Tilt Detection

Tilt is flagged when:
- Player loses **2+ buy-ins within 60 minutes**, OR
- Aggression Factor spikes above **4.0**, OR
- VPIP exceeds **70%**

When tilt is detected, the engine boosts estimated bluff frequency and notes increased exploitability.

---

## Exploit Rules

| Condition | Reasoning Output |
|---|---|
| Fold-to-Bet < 30% | Bluffing noted as low-EV |
| Fold-to-Bet > 65% | Pressure plays gain fold equity |
| Call Frequency ≥ 70% | Larger value bet sizing suggested |
| Overbet Freq > 25% | Polarised range flagged — evaluate carefully |
| Loose-Passive profile | Frequent value betting advised |
| Tilt detected | Bluff frequency boosted in range estimate |

---

## Philosophy

This tool is an **information layer**, not an oracle. It produces:
- Structured reasoning
- Probability brackets
- Contextual insights

It does **not** tell you to call, fold, or raise. Decisions remain yours.

---

## Home Game Settings

- Default buy-in: **400 chips = £2**
- Rebuy command adds exactly 400 chips
- Thresholds calibrated for **looser home-game pools** (higher VPIP norms)
