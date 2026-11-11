import pytest

from typedrill.scoring import accuracy, key_counts, score, wpm


def test_wpm_five_chars_per_word():
    assert wpm(50, 60) == pytest.approx(10.0)
    assert wpm(300, 60) == pytest.approx(60.0)


def test_wpm_scales_with_time():
    assert wpm(100, 30) == pytest.approx(40.0)


def test_wpm_zero_guards():
    assert wpm(10, 0) == 0.0
    assert wpm(0, 10) == 0.0
    assert wpm(10, -1) == 0.0


def test_accuracy_basic():
    assert accuracy(9, 10) == pytest.approx(90.0)
    assert accuracy(0, 4) == 0.0


def test_accuracy_empty_is_perfect():
    assert accuracy(0, 0) == 100.0


def test_key_counts_charges_expected_key():
    attempts, errors = key_counts([("a", "a"), ("b", "v"), ("b", "b"), ("b", "n")])
    assert attempts == {"a": 1, "b": 3}
    assert errors == {"b": 2}


def test_key_counts_empty():
    assert key_counts([]) == ({}, {})


def test_score_result_properties():
    r = score(60, 40, [("a", "a")] * 8 + [("b", "x")] * 2)
    assert r.keystrokes == 10
    assert r.errors == 2
    assert r.accuracy == pytest.approx(80.0)
    assert r.wpm == pytest.approx(8.0)
    assert r.key_errors == {"b": 2}


def test_score_no_keystrokes():
    r = score(0, 0, [])
    assert r.wpm == 0.0 and r.accuracy == 100.0 and r.errors == 0
