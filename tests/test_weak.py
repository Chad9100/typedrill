import random

from typedrill import weak
from typedrill.report import format_stats, format_summary, format_weak_keys, key_label
from typedrill.scoring import score


def rec(keys, wpm=40.0, accuracy=95.0, **extra):
    return {"wpm": wpm, "accuracy": accuracy, "keys": keys, **extra}


def test_aggregate_sums_across_sessions():
    h = [rec({"a": [5, 1]}), rec({"a": [3, 2], "b": [4, 0]})]
    assert weak.aggregate(h) == {"a": (8, 3), "b": (4, 0)}


def test_aggregate_last_n():
    h = [rec({"a": [5, 5]}), rec({"b": [5, 1]})]
    assert weak.aggregate(h, last=1) == {"b": (5, 1)}


def test_aggregate_skips_malformed_pairs():
    assert weak.aggregate([rec({"a": "x", "b": [1]})]) == {}


def test_weak_keys_ranked_by_rate_then_errors():
    h = [rec({"a": [10, 5], "b": [20, 10], "c": [10, 2], "d": [10, 0]})]
    got = weak.weak_keys(h)
    assert [s.key for s in got] == ["b", "a", "c"]  # b ties a on rate but has more errors
    assert got[0].error_rate == 50.0


def test_weak_keys_ignores_rarely_tried():
    h = [rec({"q": [2, 2], "e": [10, 1]})]
    assert [s.key for s in weak.weak_keys(h)] == ["e"]


def test_weak_keys_limit_and_empty():
    h = [rec({c: [10, 1] for c in "abcdef"})]
    assert len(weak.weak_keys(h, limit=3)) == 3
    assert weak.weak_keys([]) == []


def test_drill_pool_words_contain_key():
    pool = weak.drill_pool(["z"])
    assert pool and all("z" in w for w in pool)


def test_drill_pool_uppercase_key_matches_lowercase_words():
    assert weak.drill_pool(["Q"]) == weak.drill_pool(["q"])


def test_drill_pool_punctuation_fallback_token():
    assert weak.drill_pool([";"]) == [";;;"]


def test_drill_pool_space_key_ignored():
    assert weak.drill_pool([" "]) == []


def test_weak_drill_biased_to_keys():
    text = weak.weak_drill(["x"], 30, random.Random(2))
    assert len(text.split()) == 30
    assert all("x" in w for w in text.split())


def test_weak_drill_falls_back_to_general_words():
    assert len(weak.weak_drill([], 10, random.Random(2)).split()) == 10


def test_key_label():
    assert key_label(" ") == "space" and key_label("a") == "a"


def test_format_stats_empty():
    assert "No drills" in format_stats([])


def test_format_stats_numbers():
    h = [
        rec({}, wpm=30, accuracy=90, seconds=60, mode="time", ts="2026-01-01T10:00:00Z"),
        rec({}, wpm=50, accuracy=100, seconds=60, mode="words", ts="2026-01-02T10:00:00Z"),
    ]
    out = format_stats(h)
    assert "Sessions:        2" in out
    assert "Best WPM:        50.0" in out
    assert "Average WPM:     40.0" in out
    assert "2026-01-02 10:00:00" in out


def test_format_weak_keys():
    out = format_weak_keys(weak.weak_keys([rec({" ": [10, 5]})]))
    assert "space" in out and "50.0%" in out and "--weak" in out
    assert "No weak keys" in format_weak_keys([])


def test_format_summary():
    r = score(60, 100, [("a", "a")] * 9 + [("a", "b")])
    assert format_summary(r, "words") == "words: 20.0 wpm, 90.0% accuracy, 1 errors in 60.0s"
