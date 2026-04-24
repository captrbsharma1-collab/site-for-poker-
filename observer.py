"""
observer.py — Per-player statistics tracking using pandas
Tracks VPIP, PFR, Fold-to-Bet, Call Frequency, Aggression, Bet Sizing
"""

import pandas as pd
from datetime import datetime


# ── Column schema ──────────────────────────────────────────────────────────────
STAT_COLUMNS = [
    "player",
    "hands_seen",           # total hands observed
    "vpip_count",           # voluntarily put $ in pot (preflop, excl BB)
    "pfr_count",            # preflop raises
    "fold_to_bet_count",    # folded when facing a bet/raise
    "faced_bet_count",      # total times faced a bet/raise
    "call_count",           # total calls
    "aggression_bets",      # bets + raises made
    "aggression_calls",     # calls made (for AF calc)
    "bet_small",            # bets ≤ 33% pot
    "bet_medium",           # bets 34–66% pot
    "bet_large",            # bets 67–99% pot
    "bet_overbet",          # bets ≥ 100% pot
    "total_bets_sized",     # total sized bets recorded
    "buyins_lost",          # number of buy-in amounts lost
    "last_buyin_time",      # timestamp of last buy-in (for tilt detection)
    "stack",                # current chip stack
]


class Observer:
    """
    Tracks per-player action history and computes derived statistics.
    All raw counts stored in a pandas DataFrame; stats computed on demand.
    """

    def __init__(self, buyin_chips: int = 400):
        self.buyin_chips = buyin_chips
        self._df = pd.DataFrame(columns=STAT_COLUMNS).set_index("player")

    # ── Internal helpers ────────────────────────────────────────────────────

    def _ensure_player(self, player: str):
        if player not in self._df.index:
            row = {col: 0 for col in STAT_COLUMNS if col != "player"}
            row["last_buyin_time"] = None
            row["stack"] = self.buyin_chips
            self._df.loc[player] = row

    def _classify_bet_size(self, size: float, pot: float) -> str:
        if pot <= 0:
            return "medium"
        ratio = size / pot
        if ratio <= 0.33:
            return "small"
        elif ratio <= 0.66:
            return "medium"
        elif ratio < 1.0:
            return "large"
        else:
            return "overbet"

    # ── Public API ──────────────────────────────────────────────────────────

    def add_player(self, player: str, starting_stack: int = None):
        """Register a player before the game starts."""
        self._ensure_player(player)
        if starting_stack is not None:
            self._df.at[player, "stack"] = starting_stack

    def update_game(self, player: str, action: str, size: float = 0, pot: float = 0,
                    street: str = "preflop", voluntary: bool = True):
        """
        Record a single player action.

        Parameters
        ----------
        player   : player name
        action   : 'Raise', 'Bet', 'Call', 'Fold', 'Check', 'Limp'
        size     : chip amount (for bets/raises/calls)
        pot      : pot size *before* the action
        street   : 'preflop', 'flop', 'turn', 'river'
        voluntary: False for forced blinds
        """
        self._ensure_player(player)
        action = action.strip().title()

        p = self._df.loc[player]

        # Hands seen — increment on preflop voluntary or forced
        if street == "preflop":
            self._df.at[player, "hands_seen"] += 1

        # VPIP: any voluntary money in preflop (limp, call, raise)
        if street == "preflop" and voluntary and action in ("Raise", "Call", "Limp"):
            self._df.at[player, "vpip_count"] += 1

        # PFR
        if street == "preflop" and action == "Raise":
            self._df.at[player, "pfr_count"] += 1

        # Fold to bet
        if action == "Fold":
            self._df.at[player, "faced_bet_count"] += 1
            self._df.at[player, "fold_to_bet_count"] += 1

        # Call frequency tracking
        if action == "Call":
            self._df.at[player, "call_count"] += 1
            self._df.at[player, "faced_bet_count"] += 1
            self._df.at[player, "aggression_calls"] += 1

        # Aggression: bets and raises
        if action in ("Bet", "Raise"):
            self._df.at[player, "aggression_bets"] += 1
            # Bet sizing
            if size > 0 and pot > 0:
                cat = self._classify_bet_size(size, pot)
                self._df.at[player, f"bet_{cat}"] += 1
                self._df.at[player, "total_bets_sized"] += 1
            # Facing a raise also counts as faced_bet for the *raiser's* prior
            # (skip — handled by the player who faces this raise separately)

        # Stack adjustment
        if action in ("Bet", "Raise", "Call", "Limp") and size > 0:
            self._df.at[player, "stack"] = max(0, self._df.at[player, "stack"] - size)

    def record_rebuy(self, player: str):
        """Record a rebuy event (£2 = 400 chips in this home game)."""
        self._ensure_player(player)
        self._df.at[player, "buyins_lost"] += 1
        self._df.at[player, "last_buyin_time"] = datetime.now()
        self._df.at[player, "stack"] += self.buyin_chips

    def set_stack(self, player: str, chips: int):
        """Manually correct a player's stack."""
        self._ensure_player(player)
        self._df.at[player, "stack"] = chips

    def award_pot(self, player: str, amount: int):
        """Award pot winnings to a player."""
        self._ensure_player(player)
        self._df.at[player, "stack"] += amount

    # ── Derived statistics ──────────────────────────────────────────────────

    def get_stats(self, player: str) -> dict:
        """Return a dict of computed statistics for a player."""
        self._ensure_player(player)
        p = self._df.loc[player]

        hands = max(p["hands_seen"], 1)
        faced = max(p["faced_bet_count"], 1)
        total_sized = max(p["total_bets_sized"], 1)
        ag_denom = max(p["aggression_calls"] + p["aggression_bets"], 1)  # avoid /0 with 0 calls

        vpip = round(p["vpip_count"] / hands * 100, 1)
        pfr = round(p["pfr_count"] / hands * 100, 1)
        fold_to_bet = round(p["fold_to_bet_count"] / faced * 100, 1)
        call_freq = round(p["call_count"] / faced * 100, 1)
        # Aggression Factor: (bets + raises) / calls  — standard poker metric
        af = round(p["aggression_bets"] / max(p["aggression_calls"], 1), 2)

        bet_sizing = {
            "small":   round(p["bet_small"] / total_sized * 100, 1),
            "medium":  round(p["bet_medium"] / total_sized * 100, 1),
            "large":   round(p["bet_large"] / total_sized * 100, 1),
            "overbet": round(p["bet_overbet"] / total_sized * 100, 1),
        }

        return {
            "player": player,
            "hands_seen": int(p["hands_seen"]),
            "vpip": vpip,
            "pfr": pfr,
            "fold_to_bet_pct": fold_to_bet,
            "call_frequency_pct": call_freq,
            "aggression_factor": af,
            "bet_sizing": bet_sizing,
            "stack": int(p["stack"]),
            "buyins_lost": int(p["buyins_lost"]),
            "last_buyin_time": p["last_buyin_time"],
            # raw counts (useful for engine)
            "_faced_bet_count": int(p["faced_bet_count"]),
            "_total_bets_sized": int(p["total_bets_sized"]),
        }

    def all_players(self) -> list:
        return list(self._df.index)

    def get_dataframe(self) -> pd.DataFrame:
        """Return raw tracking DataFrame (for inspection / export)."""
        return self._df.copy()
