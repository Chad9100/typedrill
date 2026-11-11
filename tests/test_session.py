import pytest

from typedrill.session import CORRECT, PENDING, WRONG, DrillSession


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def make(target="cat dog", limit=None, extend=None):
    clock = Clock()
    return DrillSession(target, limit, clock, extend), clock


def type_all(s, text):
    for ch in text:
        s.type_char(ch)


def test_empty_target_rejected():
    with pytest.raises(ValueError):
        DrillSession("")


def test_timer_starts_on_first_key():
    s, clock = make()
    clock.t += 50
    assert s.elapsed() == 0.0 and not s.started
    s.type_char("c")
    clock.t += 3
    assert s.started and s.elapsed() == 3.0


def test_words_mode_finishes_when_target_typed():
    s, clock = make("ab")
    s.type_char("a")
    clock.t += 6
    assert not s.finished
    s.type_char("b")
    assert s.finished
    clock.t += 100
    assert s.elapsed() == 6.0


def test_typing_after_finish_ignored():
    s, _ = make("a")
    s.type_char("a")
    assert s.type_char("a") is False
    assert len(s.keystrokes) == 1


def test_char_states():
    s, _ = make("abc")
    type_all(s, "ax")
    assert s.char_states() == [CORRECT, WRONG, PENDING]


def test_backspace_fixes_text_but_error_counts():
    s, _ = make("abc")
    type_all(s, "ax")
    assert s.backspace()
    s.type_char("b")
    assert s.char_states()[:2] == [CORRECT, CORRECT]
    r = s.result()
    assert r.keystrokes == 3 and r.errors == 1
    assert r.key_errors == {"b": 1}


def test_backspace_at_start_is_noop():
    s, _ = make()
    assert s.backspace() is False


def test_correct_chars_counts_final_text_only():
    s, _ = make("abc")
    type_all(s, "axc")
    assert s.correct_chars() == 2


def test_time_mode_ends_at_limit():
    s, clock = make("a" * 100, limit=30)
    s.type_char("a")
    clock.t += 29
    assert not s.finished
    clock.t += 5
    assert s.finished
    assert s.elapsed() == 30.0
    assert s.remaining() == 0.0
    assert s.type_char("a") is False


def test_remaining_counts_down():
    s, clock = make("a" * 100, limit=30)
    assert s.remaining() == 30
    s.type_char("a")
    clock.t += 10
    assert s.remaining() == 20


def test_time_mode_extends_text():
    s, _ = make("a" * 50, limit=60, extend=lambda: "zzz")
    type_all(s, "a" * 50)
    assert not s.finished
    assert s.target.endswith(" zzz")


def test_words_mode_no_extend_runs_out():
    s, _ = make("aa")
    type_all(s, "aa")
    assert s.finished


def test_live_stats():
    s, clock = make("abcde" * 4)
    type_all(s, "abcde")
    clock.t += 60
    s.type_char("x")  # wrong
    assert s.live_wpm() == pytest.approx(1.0)
    assert s.live_accuracy() == pytest.approx(100 * 5 / 6)
