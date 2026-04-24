"""
engine.py — Opponent modelling, exploit heuristics, EV, tilt detection
No heavy solver; pure Bayesian-flavoured heuristics + rule engine.
"""

from datetime import datetime, timedelta
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# 1. OPPONENT CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════

class OpponentClassifier:
    """
    Maps raw stats → human-readable player type using threshold-based logic.
    Thresholds tuned for small home-game pools (looser than online norms).
    """

    # VPIP thresholds
    VPIP_TIGHT  = 22
    VPIP_LOOSE  = 40

    # PFR thresholds
    PFR_PASSIVE = 8
    PFR_AGGRO   = 20

    # Aggression Factor thresholds
    AF_PASSIVE  = 1.0
    AF_AGGRO    = 2.5

    # Fold-to-bet
    FTB_STATION = 30   # calls almost everything
    FTB_NITTER  = 65   # folds a lot

    # Overbet frequency
    OVERBET_HIGH = 25  # >25% of bets are overbets → bluff-candidate flag

    @classmethod
    def classify(cls, stats: dict) -> dict:
        """
        Returns a profile dict with style labels, confidence, and flags.
        """
        vpip  = stats.get("vpip", 0)
        pfr   = stats.get("pfr", 0)
        ftb   = stats.get("fold_to_bet_pct", 50)
        cf    = stats.get("call_frequency_pct", 50)
        af    = stats.get("aggression_factor", 1.0)
        sizing = stats.get("bet_sizing", {})
        overbet_pct = sizing.get("overbet", 0)
        hands = stats.get("hands_seen", 0)

        # Confidence — low sample = hedged labels
        confidence = "low" if hands < 10 else "medium" if hands < 25 else "high"

        # Loose / Tight
        if vpip >= cls.VPIP_LOOSE:
            looseness = "Loose"
        elif vpip <= cls.VPIP_TIGHT:
            looseness = "Tight"
        else:
            looseness = "Semi-Loose"

        # Passive / Aggressive (blend VPIP-PFR gap and AF)
        pfr_gap = vpip - pfr   # large gap → limp-caller / passive
        if af >= cls.AF_AGGRO or pfr >= cls.PFR_AGGRO:
            aggression = "Aggressive"
        elif af <= cls.AF_PASSIVE or pfr_gap >= 20:
            aggression = "Passive"
        else:
            aggression = "Balanced"

        # Bluff tendency (overbet + low fold-to-bluff proxy)
        if overbet_pct >= cls.OVERBET_HIGH and af >= cls.AF_AGGRO:
            bluff_tendency = "Bluff-Heavy"
        elif ftb >= cls.FTB_NITTER and af <= 1.2:
            bluff_tendency = "Value-Heavy"
        elif cf >= 70:
            bluff_tendency = "Calling-Station"
        else:
            bluff_tendency = "Balanced"

        # Betting pattern insight
        dominant_size = max(sizing, key=sizing.get) if sizing else "medium"

        return {
            "looseness": looseness,
            "aggression": aggression,
            "bluff_tendency": bluff_tendency,
            "dominant_bet_size": dominant_size,
            "overbet_frequency": overbet_pct,
            "fold_to_bet_pct": ftb,
            "call_frequency_pct": cf,
            "aggression_factor": af,
            "confidence": confidence,
            "hands_sample": hands,
            "label": f"{looseness}-{aggression}",
        }


# ══════════════════════════════════════════════════════════════════════════════
# 2. TILT DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class TiltDetector:
    """
    Flags tilt based on:
    - Multiple buy-ins lost in a short window
    - Sudden spike in aggression (tracked externally via observer)
    """

    TILT_BUYIN_THRESHOLD = 2          # lost this many buy-ins…
    TILT_WINDOW_MINUTES  = 60         # …within this many minutes

    @classmethod
    def check_tilt(cls, stats: dict) -> dict:
        buyins_lost = stats.get("buyins_lost", 0)
        last_buyin  = stats.get("last_buyin_time")
        af          = stats.get("aggression_factor", 1.0)
        vpip        = stats.get("vpip", 0)

        tilt_mode = False
        tilt_reasons = []
        tilt_level = "None"

        if buyins_lost >= cls.TILT_BUYIN_THRESHOLD:
            if last_buyin is not None:
                elapsed = (datetime.now() - last_buyin).total_seconds() / 60
                if elapsed <= cls.TILT_WINDOW_MINUTES:
                    tilt_mode = True
                    tilt_reasons.append(
                        f"Lost {buyins_lost} buy-ins within ~{int(elapsed)} minutes"
                    )

        if af > 4.0:
            tilt_mode = True
            tilt_reasons.append(f"Aggression Factor spiked to {af} (very high)")

        if vpip > 70:
            tilt_mode = True
            tilt_reasons.append(f"VPIP at {vpip}% — playing almost every hand")

        if tilt_mode:
            tilt_level = "High" if len(tilt_reasons) >= 2 else "Moderate"

        # Tilt adjustments to apply to profile
        aggression_boost = 15 if tilt_level == "High" else 7 if tilt_level == "Moderate" else 0
        bluff_boost = 20 if tilt_level == "High" else 10 if tilt_level == "Moderate" else 0

        return {
            "tilt_mode": tilt_mode,
            "tilt_level": tilt_level,
            "tilt_reasons": tilt_reasons,
            "aggression_adjustment": aggression_boost,
            "bluff_likelihood_boost": bluff_boost,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 3. POT ODDS + EV CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

class EVCalculator:
    """
    Lightweight pot-odds and EV reasoning.
    Does NOT claim exact equity — estimates a range bracket.
    """

    @staticmethod
    def pot_odds(call_amount: float, pot_before_call: float) -> dict:
        """
        Returns required equity and break-even threshold.
        pot_before_call: the pot size BEFORE hero's call is added.
        """
        total = pot_before_call + call_amount
        if total <= 0:
            return {"error": "Invalid pot/call values"}
        required_equity = call_amount / total
        return {
            "call_amount": call_amount,
            "pot_before_call": pot_before_call,
            "pot_after_call": total,
            "required_equity_pct": round(required_equity * 100, 1),
            "implied_odds_note": "Adjust upward if stacks are deep and villain will pay off.",
        }

    @staticmethod
    def estimate_equity_vs_range(hand_strength: str, profile: dict, tilt: dict) -> dict:
        """
        Heuristic equity estimate based on hand strength descriptor + opponent profile.
        hand_strength: 'monster', 'strong', 'medium', 'weak', 'draw'
        Returns an estimated equity bracket (not a solver output).
        """
        # Base equity brackets
        base = {
            "monster": (75, 90),
            "strong":  (55, 75),
            "medium":  (40, 55),
            "weak":    (25, 40),
            "draw":    (30, 50),
        }.get(hand_strength.lower(), (40, 55))

        lo, hi = base

        # Adjust for opponent looseness (loose = wider range = hero equity improves)
        looseness = profile.get("looseness", "Semi-Loose")
        if looseness == "Loose":
            lo += 5; hi += 5
        elif looseness == "Tight":
            lo -= 8; hi -= 8

        # Adjust for bluff tendency (bluff-heavy = range is weaker = hero equity improves)
        bluff_t = profile.get("bluff_tendency", "Balanced")
        if bluff_t == "Bluff-Heavy":
            lo += 5; hi += 8
        elif bluff_t == "Value-Heavy":
            lo -= 5; hi -= 5
        elif bluff_t == "Calling-Station":
            lo -= 3; hi -= 3   # stations usually have real hands when they raise

        # Tilt boost
        lo += tilt.get("bluff_likelihood_boost", 0) // 2
        hi += tilt.get("bluff_likelihood_boost", 0) // 2

        lo = max(5, min(lo, 95))
        hi = max(lo + 1, min(hi, 95))

        return {
            "hand_strength": hand_strength,
            "estimated_equity_lo": lo,
            "estimated_equity_hi": hi,
            "estimated_equity_label": f"~{lo}–{hi}%",
            "note": "Heuristic estimate only — not a solver result.",
        }

    @staticmethod
    def ev_insight(required_equity: float, est_lo: float, est_hi: float) -> str:
        mid = (est_lo + est_hi) / 2
        margin = mid - required_equity
        if margin > 15:
            return "Strong +EV territory — range estimate comfortably clears pot odds."
        elif margin > 5:
            return "Likely +EV — range estimate clears pot odds with moderate margin."
        elif margin > -5:
            return "Marginal — pot odds and equity estimate are close; implied odds matter."
        else:
            return "Likely -EV without strong implied odds or read adjustment."


# ══════════════════════════════════════════════════════════════════════════════
# 4. EXPLOIT HEURISTIC ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ExploitEngine:
    """
    Rule-based exploit suggestions.
    Returns reasoning text and structured insights — never direct commands.
    """

    @staticmethod
    def analyse(
        stats: dict,
        profile: dict,
        tilt: dict,
        game_state_snapshot: dict,
        call_amount: float = 0,
        hand_strength: str = "medium",
    ) -> dict:

        player = stats.get("player", "Villain")
        ftb    = profile.get("fold_to_bet_pct", 50)
        cf     = profile.get("call_frequency_pct", 50)
        af     = profile.get("aggression_factor", 1.0)
        overbet_freq = profile.get("overbet_frequency", 0)
        looseness    = profile.get("looseness", "Semi-Loose")
        aggression   = profile.get("aggression", "Balanced")
        bluff_t      = profile.get("bluff_tendency", "Balanced")
        dominant_size = profile.get("dominant_bet_size", "medium")
        label        = profile.get("label", "Unknown")
        confidence   = profile.get("confidence", "low")
        tilt_mode    = tilt.get("tilt_mode", False)
        tilt_level   = tilt.get("tilt_level", "None")
        pot          = game_state_snapshot.get("pot", 0)
        spr          = game_state_snapshot.get("spr", 5)
        street       = game_state_snapshot.get("street", "unknown")

        insights = []
        betting_guidance = []
        bluff_guidance = []
        sizing_guidance = []

        # ── Bluffing guidance ───────────────────────────────────────────────
        if ftb < 30:
            bluff_guidance.append(
                f"{player} folds only {ftb}% of the time vs bets — bluffing is low-EV against this player."
            )
        elif ftb > 65:
            bluff_guidance.append(
                f"{player} folds {ftb}% vs bets — a strong candidate for well-timed bluffs and pressure plays."
            )
        else:
            bluff_guidance.append(
                f"{player} folds {ftb}% vs bets — selectively apply pressure; avoid over-bluffing."
            )

        # ── Value betting guidance ──────────────────────────────────────────
        if bluff_t == "Calling-Station" or cf >= 70:
            betting_guidance.append(
                f"{player} calls {cf}% of bets — extract maximum value with strong hands; reduce bluff frequency significantly."
            )
            sizing_guidance.append(
                "Consider larger value bet sizes (75–100% pot) since this player rarely folds."
            )
        elif looseness == "Loose" and aggression == "Passive":
            betting_guidance.append(
                f"{player} is a loose-passive player (VPIP {stats.get('vpip')}%, PFR {stats.get('pfr')}%) — bet for value frequently; they likely call with weak holdings."
            )
            sizing_guidance.append(
                "Use medium-large sizing (50–75% pot) to build pot without scaring them away."
            )
        elif looseness == "Tight" and aggression == "Aggressive":
            betting_guidance.append(
                f"{player} is tight-aggressive — their bets are polarised; give strong hands full credit; thin-value bet cautiously."
            )
            sizing_guidance.append(
                "Smaller value bets (33–50% pot) keep their range wider and induces lighter calls."
            )

        # ── Overbet / bluff-range analysis ─────────────────────────────────
        if overbet_freq > 25:
            insights.append(
                f"{player} overbets {overbet_freq}% of their bets — this is often a polarised range "
                f"(strong hands or bluffs). Evaluate hand strength carefully before calling large bets."
            )
        elif dominant_size in ("large", "overbet"):
            insights.append(
                f"{player} predominantly uses {dominant_size} bet sizes — expect pressure; "
                f"check whether aggression is backed by AF ({af})."
            )

        # ── Aggression Factor interpretation ───────────────────────────────
        if af > 3:
            insights.append(
                f"High Aggression Factor ({af}) suggests {player} bets/raises frequently relative to calls — "
                f"they may be bluffing at elevated frequency or have strong hands; context matters."
            )
        elif af < 0.8:
            insights.append(
                f"Low AF ({af}) — {player} prefers calling over betting; hands they bet are likely strong."
            )

        # ── Tilt adjustments ───────────────────────────────────────────────
        tilt_notes = []
        if tilt_mode:
            tilt_notes.append(
                f"⚠ TILT ALERT ({tilt_level}): {'; '.join(tilt.get('tilt_reasons', []))}."
            )
            tilt_notes.append(
                "Increase estimated bluff frequency. Tilt reduces range discipline — "
                "expect wider, weaker holdings in aggressive spots."
            )
            if ftb < 40:
                tilt_notes.append(
                    "Even though this player normally calls a lot, tilt may cause impulsive raises — "
                    "re-raising and pressure plays carry more fold equity now."
                )

        # ── SPR context ────────────────────────────────────────────────────
        spr_note = ""
        if spr < 2:
            spr_note = f"SPR is {spr} — very short; pot commitment is high. Strong made hands are likely ahead."
        elif spr < 5:
            spr_note = f"SPR is {spr} — medium; one-pair hands are playable but vulnerable to pressure."
        else:
            spr_note = f"SPR is {spr} — deep stacks; implied odds and multi-street thinking are important."

        # ── Pot odds & EV ──────────────────────────────────────────────────
        pot_odds_data = {}
        equity_data   = {}
        ev_note       = ""
        if call_amount > 0 and pot > 0:
            pot_odds_data = EVCalculator.pot_odds(call_amount, pot)
            equity_data   = EVCalculator.estimate_equity_vs_range(hand_strength, profile, tilt)
            ev_note = EVCalculator.ev_insight(
                pot_odds_data["required_equity_pct"],
                equity_data["estimated_equity_lo"],
                equity_data["estimated_equity_hi"],
            )

        # ── Assemble output ─────────────────────────────────────────────────
        return {
            "player_profile": f"{player} is classified as {label} (confidence: {confidence}, {stats.get('hands_seen', 0)} hands observed)",
            "tendency": f"Bluff tendency: {bluff_t} | Dominant sizing: {dominant_size} | AF: {af}",
            "tilt": {
                "active": tilt_mode,
                "level": tilt_level,
                "notes": tilt_notes,
            },
            "bluff_guidance": bluff_guidance,
            "betting_guidance": betting_guidance,
            "sizing_guidance": sizing_guidance,
            "overbet_insight": insights,
            "spr_context": spr_note,
            "pot_odds": pot_odds_data if pot_odds_data else "No call scenario provided.",
            "estimated_equity": equity_data if equity_data else "No hand strength provided.",
            "ev_assessment": ev_note if ev_note else "No EV calculation performed.",
            "raw_profile": profile,
            "raw_tilt": tilt,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 5. TOP-LEVEL ANALYSIS FAÇADE
# ══════════════════════════════════════════════════════════════════════════════

class PokerEngine:
    """
    Orchestrates Observer → Classifier → TiltDetector → ExploitEngine.
    Single entry point for the UI layer.
    """

    def __init__(self, observer, game_state):
        self.observer   = observer
        self.game_state = game_state
        self.classifier = OpponentClassifier()
        self.tilt_det   = TiltDetector()
        self.exploit    = ExploitEngine()

    def analyse_villain(
        self,
        villain: str,
        call_amount: float = 0,
        hand_strength: str = "medium",
    ) -> dict:
        """
        Full analysis pipeline for a named villain.
        Returns structured reasoning dict.
        """
        stats   = self.observer.get_stats(villain)
        profile = OpponentClassifier.classify(stats)
        tilt    = TiltDetector.check_tilt(stats)
        snap    = self.game_state.snapshot()

        analysis = ExploitEngine.analyse(
            stats=stats,
            profile=profile,
            tilt=tilt,
            game_state_snapshot=snap,
            call_amount=call_amount,
            hand_strength=hand_strength,
        )
        analysis["stats_snapshot"] = stats
        analysis["game_state"]     = snap
        return analysis

    def session_summary(self) -> list:
        """Return a summary of all tracked players."""
        summaries = []
        for p in self.observer.all_players():
            stats   = self.observer.get_stats(p)
            profile = OpponentClassifier.classify(stats)
            tilt    = TiltDetector.check_tilt(stats)
            summaries.append({
                "player":  p,
                "label":   profile["label"],
                "bluff_t": profile["bluff_tendency"],
                "vpip":    stats["vpip"],
                "pfr":     stats["pfr"],
                "af":      stats["aggression_factor"],
                "ftb":     stats["fold_to_bet_pct"],
                "stack":   stats["stack"],
                "tilt":    tilt["tilt_level"],
            })
        return summaries
