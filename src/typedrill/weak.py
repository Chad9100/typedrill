"""Weak-key analysis over saved history, and drills built from it."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from typedrill import words

MIN_ATTEMPTS = 5


@dataclass(frozen=True)
class KeyStat:
    key: str
    attempts: int
    errors: int

    @property
    def error_rate(self) -> float:
        return 100.0 * self.errors / self.attempts if self.attempts else 0.0


def aggregate(history: list[dict[str, Any]], last: int | None = None) -> dict[str, tuple[int, int]]:
    """Sum (attempts, errors) per key over the last ``last`` sessions."""
    records = history[-last:] if last else history
    totals: dict[str, list[int]] = {}
    for rec in records:
        for key, pair in rec.get("keys", {}).items():
            try:
                attempts, errors = int(pair[0]), int(pair[1])
            except (TypeError, ValueError, IndexError):
                continue
            t = totals.setdefault(key, [0, 0])
            t[0] += attempts
            t[1] += errors
    return {k: (a, e) for k, (a, e) in totals.items()}


def weak_keys(
    history: list[dict[str, Any]],
    limit: int = 8,
    min_attempts: int = MIN_ATTEMPTS,
    last: int | None = None,
) -> list[KeyStat]:
    """Keys with errors, worst error rate first. Keys tried fewer than
    ``min_attempts`` times are ignored so one lucky miss is not "weak"."""
    stats = [
        KeyStat(k, a, e)
        for k, (a, e) in aggregate(history, last).items()
        if e > 0 and a >= min_attempts
    ]
    stats.sort(key=lambda s: (-s.error_rate, -s.errors, s.key))
    return stats[:limit]


def drill_pool(keys: list[str]) -> list[str]:
    """Words that contain a weak key. A key no built-in word contains
    (punctuation, say) gets a short repeated token instead."""
    pool: list[str] = []
    for key in keys:
        low = key.lower()
        hits = [w for w in words.WORDS if low in w]
        if hits:
            pool.extend(hits)
        elif key.strip():
            pool.append(key * 3)
    return list(dict.fromkeys(pool))


def weak_drill(keys: list[str], count: int, rng: random.Random | None = None) -> str:
    """Practice text of ``count`` words biased to the given weak keys."""
    pool = drill_pool(keys)
    if not pool:
        return words.generate(count, rng)
    return words.generate(count, rng, pool)
