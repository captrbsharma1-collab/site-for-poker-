"""
demo.py — Demonstrates the Poker Decision Support Tool with a simulated session
Run: python demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from observer import Observer
from state import GameState
from engine import PokerEngine, OpponentClassifier, TiltDetector
from datetime import datetime, timedelta


def run_demo():
    print("=" * 65)
    print("  ♠ POKER DECISION SUPPORT TOOL — Demo Session")
    print("=" * 65)

    # ── Setup ────────────────────────────────────────────────────────────────
    obs   = Observer(buyin_chips=400)
    state = GameState(observer=obs)
    eng   = PokerEngine(observer=obs, game_state=state)

    players = ["Hero", "Wayne", "Tim", "JJ", "Dave"]
    for p in players:
        obs.add_player(p, 400)

    # ── Simulate Wayne: Loose-Aggressive, overbet-happy ─────────────────────
    print("\n[Simulating Wayne — Loose-Aggressive, overbet frequency]")
    for i in range(20):
        pot = 100
        obs.update_game("Wayne", "Raise", size=180, pot=pot, street="preflop", voluntary=True)
    for i in range(6):
        obs.update_game("Wayne", "Bet",   size=400, pot=300, street="flop")   # overbets
    for i in range(4):
        obs.update_game("Wayne", "Bet",   size=180, pot=300, street="flop")   # large
    for i in range(5):
        obs.update_game("Wayne", "Call",  size=100, pot=200, street="flop")
    for i in range(3):
        obs.update_game("Wayne", "Fold",  street="flop")

    # ── Simulate Tim: Calling station ────────────────────────────────────────
    print("[Simulating Tim — Loose-Passive, calling station]")
    for i in range(18):
        obs.update_game("Tim", "Call",  size=100, pot=200, street="preflop", voluntary=True)
    for i in range(2):
        obs.update_game("Tim", "Raise", size=120, pot=200, street="preflop", voluntary=True)
    for i in range(15):
        obs.update_game("Tim", "Call",  size=150, pot=300, street="flop")
    for i in range(3):
        obs.update_game("Tim", "Fold",  street="flop")

    # ── Simulate JJ: Tight-Aggressive ────────────────────────────────────────
    print("[Simulating JJ — Tight-Aggressive]")
    for i in range(6):
        obs.update_game("JJ", "Raise", size=150, pot=100, street="preflop", voluntary=True)
    for i in range(14):
        obs.update_game("JJ", "Fold",  street="preflop")
    for i in range(4):
        obs.update_game("JJ", "Bet",   size=200, pot=300, street="flop")
    for i in range(2):
        obs.update_game("JJ", "Fold",  street="flop")

    # ── Simulate Dave: Tilt scenario ─────────────────────────────────────────
    print("[Simulating Dave — on Tilt after losing 2 buy-ins]")
    obs._df.at["Dave", "buyins_lost"] = 2
    obs._df.at["Dave", "last_buyin_time"] = datetime.now() - timedelta(minutes=35)
    obs._df.at["Dave", "stack"] = 150   # short-stacked
    for i in range(15):
        obs.update_game("Dave", "Raise", size=200, pot=150, street="preflop", voluntary=True)
    for i in range(5):
        obs.update_game("Dave", "Call",  size=100, pot=200, street="flop")
    for i in range(2):
        obs.update_game("Dave", "Fold",  street="flop")

    # ── New hand setup ────────────────────────────────────────────────────────
    print("\n[Starting Hand #1 — Hero vs Wayne]")
    state.new_hand(
        players=["Hero", "Wayne", "Tim"],
        hero="Hero",
        villain="Wayne",
        small_blind=1,
        big_blind=2,
    )
    state.set_pot(350)     # after some preflop action
    state.set_board(["Ah", "7d", "2c"])
    state.set_hero_hand(["As", "Kh"])
    state.next_street(["Ah", "7d", "2c"])  # flop

    # ── Analysis 1: Hero faces Wayne's overbet on the flop ───────────────────
    print("\n" + "─" * 65)
    print("SCENARIO: Wayne overbets 400 into pot 350 on Ah-7d-2c. Hero has As-Kh.")
    print("─" * 65)
    analysis = eng.analyse_villain(
        villain="Wayne",
        call_amount=400,
        hand_strength="strong",
    )
    _print_analysis(analysis)

    # ── Analysis 2: Tim as calling station ───────────────────────────────────
    state.hand.villain = "Tim"
    state.set_pot(280)
    print("\n" + "─" * 65)
    print("SCENARIO: Hero has top pair on flop — Tim faces a value bet of 200.")
    print("─" * 65)
    analysis2 = eng.analyse_villain(
        villain="Tim",
        call_amount=0,
        hand_strength="strong",
    )
    _print_analysis(analysis2)

    # ── Analysis 3: Dave on tilt ──────────────────────────────────────────────
    state.hand.villain = "Dave"
    state.set_pot(200)
    obs.set_stack("Dave", 150)
    print("\n" + "─" * 65)
    print("SCENARIO: Dave shoves 150 into pot 200. Hero has medium hand.")
    print("─" * 65)
    analysis3 = eng.analyse_villain(
        villain="Dave",
        call_amount=150,
        hand_strength="medium",
    )
    _print_analysis(analysis3)

    # ── Session summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  SESSION SUMMARY")
    print("=" * 65)
    summaries = eng.session_summary()
    header = f"{'Player':<10} {'Style':<22} {'VPIP':>5} {'PFR':>4} {'AF':>5} {'FtB%':>5} {'Stack':>6} {'Tilt':>10}"
    print(header)
    print("-" * len(header))
    for p in summaries:
        tilt_str = f"⚠ {p['tilt']}" if p['tilt'] != "None" else "—"
        print(f"{p['player']:<10} {p['label']:<22} {p['vpip']:>5} {p['pfr']:>4} {p['af']:>5} {p['ftb']:>5} {p['stack']:>6} {tilt_str:>10}")
    print("=" * 65)


def _print_analysis(analysis: dict):
    print(f"\n  ▸ Profile   : {analysis['player_profile']}")
    print(f"  ▸ Tendency  : {analysis['tendency']}")

    tilt = analysis.get("tilt", {})
    if tilt.get("active"):
        print(f"\n  ⚠ TILT ({tilt['level']})")
        for note in tilt.get("notes", []):
            print(f"    • {note}")

    if analysis.get("bluff_guidance"):
        print("\n  ▸ Bluff Assessment:")
        for g in analysis["bluff_guidance"]:
            print(f"    • {g}")

    if analysis.get("betting_guidance"):
        print("\n  ▸ Value Betting:")
        for g in analysis["betting_guidance"]:
            print(f"    • {g}")

    if analysis.get("sizing_guidance"):
        print("\n  ▸ Sizing Guidance:")
        for g in analysis["sizing_guidance"]:
            print(f"    • {g}")

    if analysis.get("overbet_insight"):
        print("\n  ▸ Range Insights:")
        for g in analysis["overbet_insight"]:
            print(f"    • {g}")

    pot_odds = analysis.get("pot_odds", {})
    equity   = analysis.get("estimated_equity", {})
    ev       = analysis.get("ev_assessment", "")
    if isinstance(pot_odds, dict) and pot_odds:
        print(f"\n  ▸ Pot Odds & EV:")
        print(f"    Required equity : {pot_odds.get('required_equity_pct')}%")
        if isinstance(equity, dict):
            print(f"    Estimated equity: {equity.get('estimated_equity_label')} ({equity.get('hand_strength')} hand)")
        print(f"    Assessment      : {ev}")

    print(f"\n  ▸ Stack Context: {analysis.get('spr_context', '')}")


if __name__ == "__main__":
    run_demo()
