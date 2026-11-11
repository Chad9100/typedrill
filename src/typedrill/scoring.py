"""Pure scoring: WPM, accuracy and per-key error counts. No I/O, no clock."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

CHARS_PER_WORD = 5  # the usual typing-test convention


def wpm(correct_chars: int, seconds: float) -> float:
    """Words per minute, counting five correct characters as one word."""
    if seconds <= 0 or correct_chars <= 0:
        return 0.0
    return (correct_chars / CHARS_PER_WORD) / (seconds / 60.0)


def accuracy(correct_keystrokes: int, total_keystrokes: int) -> float:
    """Percentage of keystrokes that matched; 100.0 before anything is typed."""
    if total_keystrokes <= 0:
        return 100.0
    return 100.0 * correct_keystrokes / total_keystrokes


def key_counts(keystrokes: Iterable[tuple[str, str]]) -> tuple[dict[str, int], dict[str, int]]:
    """Return (attempts, errors) per *expected* key.

    Each keystroke is ``(expected, typed)``. A miss is charged to the key the
    typist should have hit, which is what a weak-key report needs.
    """
    attempts: dict[str, int] = {}
    errors: dict[str, int] = {}
    for expected, typed in keystrokes:
        attempts[expected] = attempts.get(expected, 0) + 1
        if typed != expected:
            errors[expected] = errors.get(expected, 0) + 1
    return attempts, errors


@dataclass(frozen=True)
class Result:
    seconds: float
    correct_chars: int  # characters that are correct in the final text
    keystrokes: int
    correct_keystrokes: int
    key_attempts: dict[str, int] = field(default_factory=dict)
    key_errors: dict[str, int] = field(default_factory=dict)

    @property
    def wpm(self) -> float:
        return wpm(self.correct_chars, self.seconds)

    @property
    def accuracy(self) -> float:
        return accuracy(self.correct_keystrokes, self.keystrokes)

    @property
    def errors(self) -> int:
        return self.keystrokes - self.correct_keystrokes


def score(seconds: float, correct_chars: int, keystrokes: list[tuple[str, str]]) -> Result:
    attempts, errors = key_counts(keystrokes)
    wrong = sum(errors.values())
    return Result(
        seconds=seconds,
        correct_chars=correct_chars,
        keystrokes=len(keystrokes),
        correct_keystrokes=len(keystrokes) - wrong,
        key_attempts=attempts,
        key_errors=errors,
    )
