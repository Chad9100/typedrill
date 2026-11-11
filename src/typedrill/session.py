"""The drill state machine. UI-independent; time comes from an injected clock."""

from __future__ import annotations

import time
from typing import Callable

from typedrill import scoring

CORRECT, WRONG, PENDING = "correct", "wrong", "pending"
EXTEND_MARGIN = 40  # extend the text when this close to its end


class DrillSession:
    """Typing against a fixed target.

    The timer starts at the first keystroke. In ``words`` mode the drill ends
    when the whole target is typed; in ``time`` mode it ends when the time
    limit passes (``extend`` supplies more text so the typist never runs out).
    Mistakes do not block progress; backspace fixes the text but the miss
    still counts against accuracy and the key.
    """

    def __init__(
        self,
        target: str,
        limit_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
        extend: Callable[[], str] | None = None,
    ):
        if not target:
            raise ValueError("target text is empty")
        self.target = target
        self.limit = limit_seconds
        self.clock = clock
        self.extend = extend
        self.typed: list[str] = []
        self.keystrokes: list[tuple[str, str]] = []
        self.started_at: float | None = None
        self.ended_at: float | None = None

    # -- input -----------------------------------------------------------
    def type_char(self, ch: str) -> bool:
        """Type one character; returns False if the drill is over."""
        if self.finished:
            return False
        if self.started_at is None:
            self.started_at = self.clock()
        if self.extend and len(self.typed) >= len(self.target) - EXTEND_MARGIN:
            self.target += " " + self.extend()
        pos = len(self.typed)
        if pos >= len(self.target):
            return False
        self.keystrokes.append((self.target[pos], ch))
        self.typed.append(ch)
        if self.limit is None and len(self.typed) >= len(self.target):
            self.ended_at = self.clock()
        return True

    def backspace(self) -> bool:
        if self.finished or not self.typed:
            return False
        self.typed.pop()
        return True

    # -- state -----------------------------------------------------------
    @property
    def started(self) -> bool:
        return self.started_at is not None

    @property
    def finished(self) -> bool:
        if self.ended_at is not None:
            return True
        if self.limit is not None and self.started_at is not None:
            if self.clock() - self.started_at >= self.limit:
                self.ended_at = self.started_at + self.limit
                return True
        return False

    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at if self.ended_at is not None else self.clock()
        elapsed = end - self.started_at
        if self.limit is not None:
            elapsed = min(elapsed, self.limit)
        return max(0.0, elapsed)

    def remaining(self) -> float | None:
        if self.limit is None:
            return None
        return max(0.0, self.limit - self.elapsed())

    def char_states(self) -> list[str]:
        """State of each target character: correct, wrong or pending."""
        states = []
        for i in range(len(self.target)):
            if i < len(self.typed):
                states.append(CORRECT if self.typed[i] == self.target[i] else WRONG)
            else:
                states.append(PENDING)
        return states

    @property
    def cursor(self) -> int:
        return len(self.typed)

    def correct_chars(self) -> int:
        return sum(1 for i, c in enumerate(self.typed) if c == self.target[i])

    def result(self) -> scoring.Result:
        return scoring.score(self.elapsed(), self.correct_chars(), self.keystrokes)

    def live_wpm(self) -> float:
        return scoring.wpm(self.correct_chars(), self.elapsed())

    def live_accuracy(self) -> float:
        return self.result().accuracy
