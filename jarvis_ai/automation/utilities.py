from __future__ import annotations

import random

from ai.personality import FACTS, JOKES, QUOTES


class Utilities:
    def joke(self) -> str:
        return random.choice(JOKES)

    def quote(self) -> str:
        return random.choice(QUOTES)

    def fact(self) -> str:
        return random.choice(FACTS)

    def coin_toss(self) -> str:
        return random.choice(("Heads.", "Tails."))

    def dice_roll(self) -> str:
        return f"You rolled {random.randint(1, 6)}."

    def rock_paper_scissors(self, user_choice: str) -> str:
        choices = ("rock", "paper", "scissors")
        cleaned = user_choice.strip().lower()
        if cleaned not in choices:
            return "I need rock, paper, or scissors."
        mine = random.choice(choices)
        if mine == cleaned:
            result = "It is a draw."
        elif (mine, cleaned) in (("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")):
            result = "I win."
        else:
            result = "You win."
        return f"I chose {mine}. {result}"
