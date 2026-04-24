"""
ui.py — Terminal UI for the Poker Decision Support Tool
Rich-formatted output; no external TUI libraries required beyond 'rich'.
Falls back to plain text if rich is not installed.
"""

import json
import sys

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH = True
except ImportError:
    RICH = False

from observer import Observer
from state import GameState
from engine import PokerEngine

console = Console() if RICH else None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _print(text, style=""):
    if RICH:
        console.print(text, style=style)
    else:
        print(text)

def _panel(content, title="", style="cyan"):
    if RICH:
        console.print(Panel(content, title=title, border_style=style))
    else:
        print(f"\n=== {title} ===\n{content}\n")

def _rule(title=""):
    if RICH:
        console.rule(title, style="dim")
    else:
        print(f"\n--- {title} ---")


# ── Display functions ──────────────────────────────────────────────────────────

def display_analysis(analysis: dict):
    """Render a full analysis result to the terminal."""
    _rule("DECISION SUPPORT ANALYSIS")

    # Player profile
    _print(f"\n[bold cyan]▸ Player Profile[/bold cyan]\n  {analysis['player_profile']}" if RICH
           else f"\n▸ Player Profile\n  {analysis['player_profile']}")
    _print(f"  {analysis['tendency']}" if RICH
           else f"  {analysis['tendency']}")

    # Tilt
    tilt = analysis.get("tilt", {})
    if tilt.get("active"):
        tilt_text = f"[bold red]⚠ TILT DETECTED — {tilt['level']} level[/bold red]" if RICH \
                    else f"⚠ TILT DETECTED — {tilt['level']} level"
        _print(f"\n{tilt_text}")
        for note in tilt.get("notes", []):
            _print(f"  • {note}")

    # Bluff guidance
    if analysis.get("bluff_guidance"):
        _print("\n[bold yellow]▸ Bluff Frequency Assessment[/bold yellow]" if RICH
               else "\n▸ Bluff Frequency Assessment")
        for g in analysis["bluff_guidance"]:
            _print(f"  • {g}")

    # Betting / value
    if analysis.get("betting_guidance"):
        _print("\n[bold green]▸ Value Betting Guidance[/bold green]" if RICH
               else "\n▸ Value Betting Guidance")
        for g in analysis["betting_guidance"]:
            _print(f"  • {g}")

    # Sizing
    if analysis.get("sizing_guidance"):
        _print("\n[bold blue]▸ Sizing Considerations[/bold blue]" if RICH
               else "\n▸ Sizing Considerations")
        for g in analysis["sizing_guidance"]:
            _print(f"  • {g}")

    # Overbet / range insights
    if analysis.get("overbet_insight"):
        _print("\n[bold magenta]▸ Range / Overbet Insights[/bold magenta]" if RICH
               else "\n▸ Range / Overbet Insights")
        for g in analysis["overbet_insight"]:
            _print(f"  • {g}")

    # SPR
    spr = analysis.get("spr_context", "")
    if spr:
        _print(f"\n[dim]▸ Stack Context: {spr}[/dim]" if RICH
               else f"\n▸ Stack Context: {spr}")

    # Pot odds + EV
    pot_odds = analysis.get("pot_odds", {})
    equity   = analysis.get("estimated_equity", {})
    ev       = analysis.get("ev_assessment", "")

    if isinstance(pot_odds, dict) and pot_odds:
        _print("\n[bold]▸ Pot Odds & EV[/bold]" if RICH else "\n▸ Pot Odds & EV")
        _print(f"  Call amount : {pot_odds.get('call_amount')} chips")
        _print(f"  Pot after call: {pot_odds.get('pot_after_call')} chips")
        _print(f"  Required equity: {pot_odds.get('required_equity_pct')}%")
        if isinstance(equity, dict) and equity:
            _print(f"  Estimated equity vs range: {equity.get('estimated_equity_label')} "
                   f"({equity.get('hand_strength')} hand vs {analysis['raw_profile'].get('label')} range)")
        if ev:
            _print(f"  [italic]{ev}[/italic]" if RICH else f"  → {ev}")

    _rule()


def display_session_summary(summaries: list):
    """Render session leaderboard / stats table."""
    if not summaries:
        _print("No players tracked yet.")
        return

    _rule("SESSION SUMMARY")

    if RICH:
        table = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan")
        table.add_column("Player",   style="bold white")
        table.add_column("Style",    style="yellow")
        table.add_column("Bluff?",   style="magenta")
        table.add_column("VPIP%")
        table.add_column("PFR%")
        table.add_column("AF")
        table.add_column("FtB%")
        table.add_column("Stack",    style="green")
        table.add_column("Tilt",     style="red")

        for p in summaries:
            tilt_str = f"⚠ {p['tilt']}" if p['tilt'] != "None" else "—"
            table.add_row(
                p["player"], p["label"], p["bluff_t"],
                str(p["vpip"]), str(p["pfr"]), str(p["af"]),
                str(p["ftb"]), str(p["stack"]), tilt_str,
            )
        console.print(table)
    else:
        header = f"{'Player':<12} {'Style':<22} {'VPIP':>5} {'PFR':>4} {'AF':>5} {'FtB%':>5} {'Stack':>6} {'Tilt':>8}"
        print(header)
        print("-" * len(header))
        for p in summaries:
            tilt_str = p['tilt'] if p['tilt'] != "None" else "—"
            print(f"{p['player']:<12} {p['label']:<22} {p['vpip']:>5} {p['pfr']:>4} {p['af']:>5} {p['ftb']:>5} {p['stack']:>6} {tilt_str:>8}")

    _rule()


# ── Interactive REPL ───────────────────────────────────────────────────────────

HELP_TEXT = """
COMMANDS
  add <player> [stack]          — Register a player (optional starting stack)
  update <player> <action> [size] [pot] [street]
                                — Log an action
                                  actions: Raise Bet Call Fold Check Limp
                                  streets: preflop flop turn river
  rebuy <player>               — Record a rebuy (+400 chips)
  stack <player> <chips>       — Manually set stack
  award <player> <chips>       — Award pot to player
  pot <chips>                  — Set pot size manually
  newhand <hero> <villain> [p1 p2 ...]  — Start new hand
  street [flop|turn|river] [cards...]   — Advance street (cards optional)
  board <cards...>             — Set community cards (e.g. Ah Kd 7c)
  herohand <card1> <card2>     — Set hero's hole cards
  analyse <villain> [call=N] [hand=strength]
                                — Full exploit analysis
                                  hand strengths: monster strong medium weak draw
  summary                      — Session stats table
  json <villain>               — Raw JSON analysis output
  help                         — Show this help
  quit / exit                  — Exit
"""

def run_repl():
    obs   = Observer(buyin_chips=400)
    state = GameState(observer=obs)
    eng   = PokerEngine(observer=obs, game_state=state)

    _print("[bold green]♠ Poker Decision Support Tool — Home Game Edition[/bold green]\n"
           "  Type [cyan]help[/cyan] for commands.\n" if RICH
           else "♠ Poker Decision Support Tool — Home Game Edition\n  Type 'help' for commands.\n")

    while True:
        try:
            raw = input("poker> ").strip()
        except (EOFError, KeyboardInterrupt):
            _print("\nGoodbye.")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd   = parts[0].lower()

        # ── add ─────────────────────────────────────────────────────────────
        if cmd == "add":
            if len(parts) < 2:
                _print("Usage: add <player> [stack]")
                continue
            player = parts[1]
            stack  = int(parts[2]) if len(parts) > 2 else 400
            obs.add_player(player, stack)
            _print(f"  Registered [bold]{player}[/bold] (stack: {stack})" if RICH
                   else f"  Registered {player} (stack: {stack})")

        # ── update ──────────────────────────────────────────────────────────
        elif cmd == "update":
            # update <player> <action> [size] [pot] [street]
            if len(parts) < 3:
                _print("Usage: update <player> <action> [size] [pot] [street]")
                continue
            player = parts[1]
            action = parts[2]
            size   = float(parts[3]) if len(parts) > 3 else 0
            pot    = float(parts[4]) if len(parts) > 4 else state.hand.pot
            street = parts[5].lower() if len(parts) > 5 else state.hand.street
            obs.update_game(player, action, size, pot, street)
            state.record_action(player, action, int(size))
            _print(f"  Logged: {player} → {action} ({size} chips, pot {pot})")

        # ── rebuy ────────────────────────────────────────────────────────────
        elif cmd == "rebuy":
            if len(parts) < 2:
                _print("Usage: rebuy <player>")
                continue
            obs.record_rebuy(parts[1])
            _print(f"  Rebuy recorded for {parts[1]} (+400 chips)")

        # ── stack ────────────────────────────────────────────────────────────
        elif cmd == "stack":
            if len(parts) < 3:
                _print("Usage: stack <player> <chips>")
                continue
            obs.set_stack(parts[1], int(parts[2]))
            _print(f"  Stack set: {parts[1]} = {parts[2]} chips")

        # ── award ────────────────────────────────────────────────────────────
        elif cmd == "award":
            if len(parts) < 3:
                _print("Usage: award <player> <chips>")
                continue
            obs.award_pot(parts[1], int(parts[2]))
            _print(f"  Awarded {parts[2]} chips to {parts[1]}")

        # ── pot ──────────────────────────────────────────────────────────────
        elif cmd == "pot":
            if len(parts) < 2:
                _print("Usage: pot <chips>")
                continue
            state.set_pot(int(parts[1]))
            _print(f"  Pot set to {parts[1]} chips")

        # ── newhand ──────────────────────────────────────────────────────────
        elif cmd == "newhand":
            if len(parts) < 3:
                _print("Usage: newhand <hero> <villain> [other_players...]")
                continue
            hero    = parts[1]
            villain = parts[2]
            players = parts[1:]
            state.new_hand(players, hero, villain)
            _print(f"  New hand #{state.hand_number} — Hero: {hero}, Villain: {villain}")

        # ── street ───────────────────────────────────────────────────────────
        elif cmd == "street":
            cards = parts[2:] if len(parts) > 2 else []
            state.next_street(cards if cards else None)
            _print(f"  Street → {state.hand.street}" + (f"  Board: {state.hand.board}" if state.hand.board else ""))

        # ── board ────────────────────────────────────────────────────────────
        elif cmd == "board":
            state.set_board(parts[1:])
            _print(f"  Board: {state.hand.board}")

        # ── herohand ─────────────────────────────────────────────────────────
        elif cmd == "herohand":
            state.set_hero_hand(parts[1:])
            _print(f"  Hero hand: {state.hand.hero_hand}")

        # ── analyse ──────────────────────────────────────────────────────────
        elif cmd == "analyse":
            if len(parts) < 2:
                _print("Usage: analyse <villain> [call=N] [hand=strength]")
                continue
            villain = parts[1]
            call_amount  = 0
            hand_strength = "medium"
            for p in parts[2:]:
                if p.startswith("call="):
                    call_amount = float(p.split("=")[1])
                elif p.startswith("hand="):
                    hand_strength = p.split("=")[1]
            analysis = eng.analyse_villain(villain, call_amount, hand_strength)
            display_analysis(analysis)

        # ── summary ──────────────────────────────────────────────────────────
        elif cmd == "summary":
            display_session_summary(eng.session_summary())

        # ── json ─────────────────────────────────────────────────────────────
        elif cmd == "json":
            if len(parts) < 2:
                _print("Usage: json <villain>")
                continue
            analysis = eng.analyse_villain(parts[1])
            # Remove non-serialisable fields
            safe = {k: v for k, v in analysis.items()
                    if k not in ("raw_profile", "raw_tilt")}
            print(json.dumps(safe, indent=2, default=str))

        # ── help ─────────────────────────────────────────────────────────────
        elif cmd in ("help", "?"):
            _print(HELP_TEXT)

        # ── quit ─────────────────────────────────────────────────────────────
        elif cmd in ("quit", "exit", "q"):
            _print("Goodbye. Good luck at the tables.")
            break

        else:
            _print(f"Unknown command '{cmd}'. Type 'help' for options.")


if __name__ == "__main__":
    run_repl()
