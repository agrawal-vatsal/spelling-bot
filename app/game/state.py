"""Game state machine for a Spell Bee session.

Pure Python — no Pipecat imports so this stays unit-testable in isolation.
"""

import random
from typing import Sequence

from app.game.words import WORDS

SESSION_LENGTH = 5  # number of words per game session


class SpellBeeGame:
    """Tracks one session: word selection, scoring, and progression.

    The session consists of SESSION_LENGTH words drawn randomly from the
    full word list.  Call current_word() to get the active target, call
    record_result() + advance() after each judgment.
    """

    def __init__(self, word_pool: Sequence[str] | None = None) -> None:
        pool = list(word_pool or WORDS)
        random.shuffle(pool)
        self._words: list[str] = pool[:SESSION_LENGTH]
        self._index: int = 0
        self._score: int = 0

    # ------------------------------------------------------------------ #
    # Read-only properties
    # ------------------------------------------------------------------ #

    @property
    def score(self) -> int:
        return self._score

    @property
    def word_number(self) -> int:
        """1-based index of the current (or last) word, clamped to total_words."""
        return min(self._index + 1, SESSION_LENGTH)

    @property
    def total_words(self) -> int:
        return SESSION_LENGTH

    # ------------------------------------------------------------------ #
    # Methods
    # ------------------------------------------------------------------ #

    def current_word(self) -> str:
        """Return the word the player must spell next.

        Raises:
            IndexError: if the session is already finished (is_finished() is True).
        """
        if self.is_finished():
            raise IndexError("Session is already finished")
        return self._words[self._index]

    def record_result(self, correct: bool) -> None:
        """Update the score for the current word."""
        if correct:
            self._score += 1

    def advance(self) -> None:
        """Move to the next word (or mark session finished)."""
        self._index += 1

    def is_finished(self) -> bool:
        """True once all SESSION_LENGTH words have been judged."""
        return self._index >= SESSION_LENGTH
