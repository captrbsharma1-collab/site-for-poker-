"""
state.py — Dynamic game state tracking
Tracks pot, stacks, street, active players, and hand history
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class HandState:
    """Represents the current hand in progress."""
    hand_number: int = 0
    street: str = "preflop"          # preflop / flop / turn / river
    pot: int = 0
    street_pot: int = 0              # chips added this street
    board: list = field(default_factory=list)   # e.g. ['Ah', 'Kd', '7c']
    active_players: list = field(default_factory=list)
    hero: str = ""
    villain: str = ""                # primary villain being analysed
    hero_hand: list = field(default_factory=list)  # ['As', 'Kh']
    last_action: dict = field(default_factory=dict)
    side_pots: list = field(default_factory=list)


class GameState:
    """
    Manages overall session state:
    - Pot tracking
    - Stack management (delegates writes to Observer)
    - Street progression
    - Rebuy tracking
    """

    STREETS = ["preflop", "flop", "turn", "river"]
    BUYIN_CHIPS = 400   # £2 home-game rebuy

    def __init__(self, observer=None):
        self.observer = observer
        self.session_start = datetime.now()
        self.hand_number = 0
        self.hand = HandState()
        self.history: list[dict] = []   # completed hand summaries

    # ── Hand lifecycle ──────────────────────────────────────────────────────

    def new_hand(self, players: list, hero: str, villain: str = "",
                 small_blind: int = 1, big_blind: int = 2):
        self.hand_number += 1
        self.hand = HandState(
            hand_number=self.hand_number,
            street="preflop",
            pot=small_blind + big_blind,
            active_players=list(players),
            hero=hero,
            villain=villain,
        )
        return self.hand

    def next_street(self, community_cards: list = None):
        """Advance to the next street, optionally adding board cards."""
        idx = self.STREETS.index(self.hand.street)
        if idx < len(self.STREETS) - 1:
            self.hand.street = self.STREETS[idx + 1]
            self.hand.street_pot = 0
        if community_cards:
            self.hand.board.extend(community_cards)

    def set_board(self, cards: list):
        self.hand.board = cards

    def set_hero_hand(self, cards: list):
        self.hand.hero_hand = cards

    # ── Pot & action ───────────────────────────────────────────────────────

    def add_to_pot(self, amount: int):
        self.hand.pot += amount
        self.hand.street_pot += amount

    def record_action(self, player: str, action: str, size: int = 0):
        """Update pot and record last action."""
        self.hand.last_action = {
            "player": player,
            "action": action,
            "size": size,
            "street": self.hand.street,
        }
        if action in ("Bet", "Raise", "Call", "Limp") and size > 0:
            self.add_to_pot(size)

    def player_fold(self, player: str):
        if player in self.hand.active_players:
            self.hand.active_players.remove(player)

    def set_pot(self, chips: int):
        """Manual pot correction."""
        self.hand.pot = chips

    # ── Effective stack ────────────────────────────────────────────────────

    def effective_stack(self) -> int:
        """
        Minimum of hero's and villain's stacks.
        Returns 0 if observer not attached or players not found.
        """
        if not self.observer:
            return 0
        hero = self.hand.hero
        villain = self.hand.villain
        players = self.observer.all_players()
        if hero not in players or villain not in players:
            return 0
        hs = self.observer.get_stats(hero)["stack"]
        vs = self.observer.get_stats(villain)["stack"]
        return min(hs, vs)

    def pot_odds_ratio(self, call_amount: int) -> float:
        """Return pot odds as a fraction: call / (pot + call)."""
        total = self.hand.pot + call_amount
        if total <= 0:
            return 0.0
        return round(call_amount / total, 4)

    # ── SPR ────────────────────────────────────────────────────────────────

    def spr(self) -> float:
        """Stack-to-Pot Ratio (effective stack / pot)."""
        pot = max(self.hand.pot, 1)
        return round(self.effective_stack() / pot, 2)

    # ── Summary ────────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        return {
            "hand_number": self.hand_number,
            "street": self.hand.street,
            "pot": self.hand.pot,
            "board": self.hand.board,
            "hero": self.hand.hero,
            "villain": self.hand.villain,
            "hero_hand": self.hand.hero_hand,
            "active_players": self.hand.active_players,
            "effective_stack": self.effective_stack(),
            "spr": self.spr(),
            "last_action": self.hand.last_action,
        }
