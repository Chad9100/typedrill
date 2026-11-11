"""The full-screen layer, driven by a fake screen and a stand-in curses module."""

import types

import pytest

from typedrill import tui
from typedrill.scoring import score
from typedrill.session import DrillSession
from typedrill.tui import ABORTED, FINISHED, layout, locate, run_tui, visible_lines


class FakeCursesError(Exception):
    pass


class FakeScreen:
    """Keeps a grid of (char, attr) cells and plays back scripted key codes."""

    def __init__(self, keys, size=(24, 80), clock=None):
        self.keys = list(keys)
        self.size = size
        self.cells = {}
        self.frames = []
        self.timeouts = []
        self.clock = clock

    def getmaxyx(self):
        return self.size

    def erase(self):
        self.cells = {}

    def addstr(self, y, x, text, attr=0):
        for i, ch in enumerate(text):
            self.cells[(y, x + i)] = (ch, attr)

    def refresh(self):
        self.frames.append(dict(self.cells))

    def keypad(self, flag):
        pass

    def timeout(self, ms):
        self.timeouts.append(ms)

    def getch(self):
        if not self.keys:
            raise AssertionError("ran out of scripted keys")
        key = self.keys.pop(0)
        if callable(key):  # a hook that advances the clock, then reports "no key"
            key()
            return -1
        return key

    def row(self, frame, y):
        xs = [x for (yy, x) in frame if yy == y]
        if not xs:
            return ""
        return "".join(frame.get((y, x), (" ", 0))[0] for x in range(max(xs) + 1))


def fake_curses(screen):
    return types.SimpleNamespace(
        KEY_BACKSPACE=263,
        error=FakeCursesError,
        curs_set=lambda n: None,
        wrapper=lambda fn: fn(screen),
        A_BOLD=1, A_REVERSE=2, A_DIM=4,
    )


def codes(text):
    return [ord(c) for c in text]


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


# -- layout ------------------------------------------------------------------

def test_layout_wraps_on_words():
    assert layout("ab cd ef", 4) == [(0, 3), (3, 6), (6, 8)]
    assert layout("ab cd ef", 5) == [(0, 3), (3, 8)]


def test_layout_fits_in_one_line():
    assert layout("ab cd", 80) == [(0, 5)]


def test_layout_splits_overlong_word():
    assert layout("abcdefgh", 3) == [(0, 3), (3, 6), (6, 8)]


def test_layout_spans_cover_text_without_overlap():
    text = "the quick brown fox jumps over the lazy dog " * 3
    spans = layout(text.strip(), 17)
    assert spans[0][0] == 0 and spans[-1][1] == len(text.strip())
    assert all(a[1] == b[0] for a, b in zip(spans, spans[1:]))
    assert all(e - s <= 17 for s, e in spans)


def test_locate_and_end_of_text():
    spans = layout("ab cd ef", 4)
    assert locate(spans, 4) == (1, 1)
    assert locate(spans, 8) == (2, 2)


def test_visible_lines_follows_cursor():
    spans = [(i * 5, i * 5 + 5) for i in range(10)]
    assert list(visible_lines(spans, 0, 3)) == [0, 1, 2]
    assert list(visible_lines(spans, 30, 3)) == [5, 6, 7]
    assert list(visible_lines(spans, 49, 3)) == [7, 8, 9]


# -- text helpers ------------------------------------------------------------

def test_header_shows_time_left_and_stats():
    clock = Clock()
    s = DrillSession("abc" * 20, limit_seconds=30, clock=clock)
    assert "30.0s left" in tui.header_text(s)
    s.type_char("a")
    assert "100.0% acc" in tui.header_text(s)


def test_header_without_limit_shows_elapsed():
    s = DrillSession("abc", clock=Clock())
    assert "0.0s" in tui.header_text(s) and "left" not in tui.header_text(s)


def test_results_lines_list_most_missed():
    r = score(10, 5, [("a", "x"), ("a", "x"), (" ", "x"), ("b", "b")])
    text = "\n".join(tui.results_lines(r, "words"))
    assert "Most missed: a x2, space x1" in text


def test_style_attrs_without_colour_support():
    attrs = tui.style_attrs(fake_curses(None))
    assert attrs["wrong"] == 2 and attrs["correct"] == 1


def test_style_attrs_with_colour():
    calls = []
    c = fake_curses(None)
    c.has_colors = lambda: True
    c.start_color = lambda: None
    c.use_default_colors = lambda: None
    c.COLOR_GREEN, c.COLOR_WHITE, c.COLOR_RED = 2, 7, 1
    c.init_pair = lambda *a: calls.append(a)
    c.color_pair = lambda n: n << 8
    attrs = tui.style_attrs(c)
    assert len(calls) == 2
    assert attrs["correct"] == 1 << 8 and attrs["wrong"] & (2 << 8)


# -- run_tui -------------------------------------------------------------------

def test_finishing_a_words_drill_shows_results():
    clock = Clock()
    s = DrillSession("hi", clock=clock)
    screen = FakeScreen(codes("hi") + [ord("k")], clock=clock)
    assert run_tui(s, "words", fake_curses(screen)) == FINISHED
    last = "\n".join(screen.row(screen.frames[-1], y) for y in range(8))
    assert "Done!" in last and "words:" in last
    assert screen.timeouts == [100, -1]


def test_escape_aborts():
    s = DrillSession("hello", clock=Clock())
    screen = FakeScreen(codes("he") + [27])
    assert run_tui(s, "words", fake_curses(screen)) == ABORTED
    assert len(s.typed) == 2


def test_idle_polls_do_not_type():
    s = DrillSession("hello", clock=Clock())
    screen = FakeScreen([-1, -1, 27])
    run_tui(s, "words", fake_curses(screen))
    assert s.typed == [] and not s.started


@pytest.mark.parametrize("code", [8, 127, 263])
def test_backspace_codes(code):
    s = DrillSession("abc", clock=Clock())
    screen = FakeScreen(codes("ax") + [code] + codes("b") + [27])
    run_tui(s, "words", fake_curses(screen))
    assert "".join(s.typed) == "ab"


def test_non_printable_keys_ignored():
    s = DrillSession("abc", clock=Clock())
    screen = FakeScreen([9, 10, 258, 400, ord("a"), 27])
    run_tui(s, "words", fake_curses(screen))
    assert "".join(s.typed) == "a"


def test_per_key_error_highlighting_is_drawn():
    s = DrillSession("abc", clock=Clock())
    screen = FakeScreen(codes("ax") + [27])
    run_tui(s, "words", fake_curses(screen))
    frame = screen.frames[-1]
    # text starts at row 2, column 2: a correct, b wrong, c is the cursor
    attrs = tui.style_attrs(fake_curses(screen))
    assert frame[(2, 2)] == ("a", attrs["correct"])
    assert frame[(2, 3)] == ("b", attrs["wrong"])
    assert frame[(2, 4)] == ("c", attrs["cursor"])


def test_wrong_space_is_shown_as_underscore():
    s = DrillSession("a b", clock=Clock())
    screen = FakeScreen(codes("ax") + [27])
    run_tui(s, "words", fake_curses(screen))
    assert screen.frames[-1][(2, 3)][0] == "_"


def test_live_header_updates_on_screen():
    clock = Clock()
    s = DrillSession("abcde" * 10, clock=clock)
    screen = FakeScreen(codes("abcde") + [lambda: setattr(clock, "t", 60.0)] + [27])
    run_tui(s, "words", fake_curses(screen))
    assert "1.0 wpm" in screen.row(screen.frames[-1], 0)


def test_time_mode_ends_when_clock_passes_limit():
    clock = Clock()
    s = DrillSession("abc " * 30, limit_seconds=10, clock=clock)
    keys = codes("a") + [lambda: setattr(clock, "t", 11.0)] + [ord("z")]
    screen = FakeScreen(keys)
    assert run_tui(s, "time", fake_curses(screen)) == FINISHED
    assert s.finished and len(s.typed) == 1


def test_text_scrolls_with_long_target():
    s = DrillSession("word " * 100, clock=Clock())
    screen = FakeScreen(codes("word " * 60) + [27], size=(10, 30))
    run_tui(s, "words", fake_curses(screen))
    frame = screen.frames[-1]
    first_row = screen.row(frame, 2)
    assert first_row.startswith("  word") and len(first_row) <= 30


def test_small_terminal_message():
    s = DrillSession("abc", clock=Clock())
    screen = FakeScreen([27], size=(3, 40))
    run_tui(s, "words", fake_curses(screen))
    assert "too small" in screen.row(screen.frames[-1], 0)


def test_addstr_errors_are_swallowed():
    class Picky(FakeScreen):
        def addstr(self, y, x, text, attr=0):
            raise FakeCursesError()

    s = DrillSession("abc", clock=Clock())
    screen = Picky([27])
    assert run_tui(s, "words", fake_curses(screen)) == ABORTED
