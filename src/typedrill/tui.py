"""Full-screen drill drawn with curses.

Everything that can be decided without a terminal (word wrapping, which rows
to show, header and result text) is a plain function; :func:`run_tui` is the
thin loop around them and takes the curses module as a parameter so tests can
hand it a stand-in. On Windows curses comes from the ``windows-curses``
package, which pyproject installs automatically.
"""

from __future__ import annotations

from typing import Any

from typedrill.report import format_summary
from typedrill.scoring import Result
from typedrill.session import CORRECT, PENDING, WRONG, DrillSession

FINISHED, ABORTED = "finished", "aborted"
ESC = 27
BACKSPACE_CODES = (8, 127)
FOOTER = "Esc: quit   Backspace: correct a typo"
MIN_WIDTH = 20


def layout(text: str, width: int) -> list[tuple[int, int]]:
    """Word-wrap ``text`` into ``(start, end)`` spans, each at most ``width``
    characters. A word's trailing space stays on its line."""
    width = max(1, width)
    spans: list[tuple[int, int]] = []
    start = 0
    line_start = 0
    pos = 0
    n = len(text)
    while pos < n:
        end = text.find(" ", pos)
        end = n if end == -1 else end + 1  # token includes its trailing space
        if end - line_start > width and pos > line_start:
            spans.append((line_start, pos))
            line_start = pos
        while end - line_start > width:  # a single token wider than the screen
            spans.append((line_start, line_start + width))
            line_start += width
        pos = end
    if line_start < n:
        spans.append((line_start, n))
    return spans or [(0, 0)]


def locate(spans: list[tuple[int, int]], index: int) -> tuple[int, int]:
    """(line, column) of a character index; the end of text sits on the last line."""
    for line, (s, e) in enumerate(spans):
        if s <= index < e:
            return line, index - s
    s, e = spans[-1]
    return len(spans) - 1, max(0, index - s)


def visible_lines(spans: list[tuple[int, int]], cursor: int, rows: int) -> range:
    """Which wrapped lines to show: keep the cursor line second from the top."""
    line, _ = locate(spans, cursor)
    first = max(0, min(line - 1, len(spans) - rows))
    return range(first, min(len(spans), first + rows))


def header_text(session: DrillSession) -> str:
    left = session.remaining()
    clock = f"{left:4.1f}s left" if left is not None else f"{session.elapsed():4.1f}s"
    return f"typedrill   {clock}   {session.live_wpm():5.1f} wpm   {session.live_accuracy():5.1f}% acc"


def results_lines(result: Result, mode: str) -> list[str]:
    lines = ["Done!", "", format_summary(result, mode)]
    worst = sorted(result.key_errors.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    if worst:
        lines += ["", "Most missed: " + ", ".join(
            f"{'space' if k == ' ' else k} x{n}" for k, n in worst)]
    lines += ["", "Press any key to finish."]
    return lines


def style_attrs(curses: Any) -> dict[str, int]:
    """Map style names to curses attributes, with or without colour support."""
    bold = getattr(curses, "A_BOLD", 0)
    reverse = getattr(curses, "A_REVERSE", 0)
    dim = getattr(curses, "A_DIM", 0)
    attrs = {"correct": bold, "wrong": reverse, "pending": dim, "cursor": reverse | bold, "header": bold}
    try:
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                bg = -1
            except curses.error:
                bg = curses.COLOR_BLACK
            curses.init_pair(1, curses.COLOR_GREEN, bg)
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
            attrs["correct"] = curses.color_pair(1)
            attrs["wrong"] = curses.color_pair(2) | bold
    except (AttributeError, curses.error):
        pass
    return attrs


def _put(screen: Any, curses: Any, y: int, x: int, text: str, attr: int) -> None:
    try:
        screen.addstr(y, x, text, attr)
    except curses.error:  # writing the bottom-right cell raises in real curses
        pass


def draw(screen: Any, session: DrillSession, curses: Any, attrs: dict[str, int]) -> None:
    height, width = screen.getmaxyx()
    screen.erase()
    if width < MIN_WIDTH or height < 5:
        _put(screen, curses, 0, 0, "Terminal too small"[: max(1, width - 1)], 0)
        screen.refresh()
        return
    _put(screen, curses, 0, 0, header_text(session)[: width - 1], attrs["header"])
    margin = 2
    text_w = width - 2 * margin
    spans = layout(session.target, text_w)
    rows = min(height - 4, 6)
    states = session.char_states()
    for row, line in enumerate(visible_lines(spans, session.cursor, rows)):
        s, e = spans[line]
        for i in range(s, e):
            ch = session.target[i]
            state = states[i]
            if state == WRONG and ch == " ":
                ch = "_"  # make a mistyped space visible
            style = "cursor" if i == session.cursor else state
            _put(screen, curses, 2 + row, margin + (i - s), ch, attrs[style])
    _put(screen, curses, height - 1, 0, FOOTER[: width - 1], attrs["pending"])
    screen.refresh()


def draw_results(screen: Any, result: Result, mode: str, curses: Any, attrs: dict[str, int]) -> None:
    height, width = screen.getmaxyx()
    screen.erase()
    for y, line in enumerate(results_lines(result, mode)[: max(1, height - 1)]):
        _put(screen, curses, y + 1, 2, line[: max(1, width - 3)], attrs["header"] if y == 0 else 0)
    screen.refresh()


def run_tui(session: DrillSession, mode: str = "drill", curses_mod: Any = None) -> str:
    """Run the drill full-screen. Returns FINISHED or ABORTED."""
    if curses_mod is None:
        import curses as curses_mod  # noqa: PLC0415 (absent on bare Windows)
    curses = curses_mod

    def loop(screen: Any) -> str:
        screen.keypad(True)
        screen.timeout(100)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        attrs = style_attrs(curses)
        backspaces = BACKSPACE_CODES + (getattr(curses, "KEY_BACKSPACE", 263),)
        while not session.finished:
            draw(screen, session, curses, attrs)
            code = screen.getch()
            if code == -1:
                continue
            if code == ESC:
                return ABORTED
            if code in backspaces:
                session.backspace()
            elif 32 <= code <= 126:
                session.type_char(chr(code))
        draw_results(screen, session.result(), mode, curses, attrs)
        screen.timeout(-1)
        screen.getch()
        return FINISHED

    return curses.wrapper(loop)
