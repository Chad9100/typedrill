"""Command line: the drill itself, plus ``stats`` and ``weak-keys``."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from typedrill import __version__, storage, weak, words
from typedrill.report import format_chart, format_csv, format_json, format_stats, format_summary, format_weak_keys
from typedrill.session import DrillSession
from typedrill.tui import ABORTED

DEFAULT_WORDS = 25
TIME_START_WORDS = 60
EXTEND_WORDS = 30

Runner = Callable[[DrillSession, str], str]


def _positive(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="typedrill",
        description="Terminal typing trainer. With no command, starts a drill.",
    )
    p.add_argument("--version", action="version", version=f"typedrill {__version__}")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--time", type=_positive, metavar="N", help="drill for N seconds")
    mode.add_argument("--words", type=_positive, metavar="N",
                      help=f"drill N words (default {DEFAULT_WORDS})")
    p.add_argument("--text", metavar="FILE", help="type the contents of FILE instead of random words")
    p.add_argument("--wordlist", metavar="FILE",
                   help="draw random words from FILE (whitespace separated) instead of the built-in list")
    p.add_argument("--weak", action="store_true", help="drill your weak keys from history")
    p.add_argument("--seed", type=int, help="seed the random word choice (repeatable drills)")
    p.add_argument("--no-save", action="store_true", help="do not record this drill in history")
    sub = p.add_subparsers(dest="command")
    st = sub.add_parser("stats", help="show history summary")
    st.add_argument("--chart", action="store_true", help="show WPM and accuracy trend sparklines")
    wk = sub.add_parser("weak-keys", help="show the keys you miss most")
    wk.add_argument("--limit", type=_positive, default=8, help="how many keys to list (default 8)")
    wk.add_argument("--last", type=_positive, help="only look at the last N sessions")
    ex = sub.add_parser("export", help="write history as CSV or JSON")
    fmt = ex.add_mutually_exclusive_group()
    fmt.add_argument("--csv", action="store_true", help="CSV format (the default)")
    fmt.add_argument("--json", action="store_true", help="JSON format, including per-key counts")
    ex.add_argument("-o", "--output", metavar="FILE", help="write to FILE instead of standard output")
    rs = sub.add_parser("reset", help="delete all saved history (asks first)")
    rs.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    return p


def _reset(path: Path, assume_yes: bool) -> int:
    count = len(storage.load_history(path))
    if count == 0:
        print("No history to delete.")
        return 0
    if not assume_yes:
        try:
            answer = input(f"Delete {count} saved drill(s)? This cannot be undone. [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            print("Nothing deleted.")
            return 1
    try:
        storage.clear_history(path)
    except OSError as exc:
        print(f"typedrill: cannot delete history: {exc.strerror or exc}", file=sys.stderr)
        return 1
    print(f"Deleted {count} saved drill(s).")
    return 0


def build_session(
    args: argparse.Namespace, history: list[dict[str, Any]], rng: random.Random,
    clock: Callable[[], float] | None = None,
) -> tuple[DrillSession, str]:
    """Pick the target text and mode label from the options. Raises ValueError."""
    kwargs: dict[str, Any] = {"clock": clock} if clock else {}
    limit = float(args.time) if args.time else None
    pool: list[str] | None = None
    label = "time" if limit else "words"
    source: str | None = None

    if args.wordlist and (args.text or args.weak):
        raise ValueError("--wordlist cannot be combined with --text or --weak")
    if args.wordlist:
        try:
            raw = Path(args.wordlist).read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:
            raise ValueError(f"cannot read {args.wordlist}: {exc.strerror or exc}") from None
        pool = words.parse_wordlist(raw)
        if not pool:
            raise ValueError(f"{args.wordlist} has no typeable words")

    if args.text:
        try:
            raw = Path(args.text).read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:
            raise ValueError(f"cannot read {args.text}: {exc.strerror or exc}") from None
        source = words.clean_text(raw)
        if not source:
            raise ValueError(f"{args.text} has no typeable text")
        label = "text"
    elif args.weak:
        keys = [s.key for s in weak.weak_keys(history)]
        if not keys:
            raise ValueError("no weak keys in your history yet; do a few drills first")
        pool = weak.drill_pool(keys) or None
        label = "weak"

    if source is not None:
        if limit:
            target = words.cycle_text(source, TIME_START_WORDS)
            return DrillSession(target, limit, extend=lambda: words.cycle_text(source, EXTEND_WORDS), **kwargs), label
        return DrillSession(words.text_words(source, args.words), **kwargs), label

    if limit:
        target = words.generate(TIME_START_WORDS, rng, pool)
        return DrillSession(target, limit, extend=lambda: words.generate(EXTEND_WORDS, rng, pool), **kwargs), label
    return DrillSession(words.generate(args.words or DEFAULT_WORDS, rng, pool), **kwargs), label


def _default_runner(session: DrillSession, mode: str) -> str:
    from typedrill.tui import run_tui

    return run_tui(session, mode)


def main(
    argv: list[str] | None = None,
    env: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    now: datetime | None = None,
    clock: Callable[[], float] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    hist_path = storage.history_path(env)

    if args.command == "stats":
        history = storage.load_history(hist_path)
        print(format_chart(history) if args.chart else format_stats(history))
        return 0
    if args.command == "reset":
        return _reset(hist_path, args.yes)
    if args.command == "export":
        fmt = format_json if args.json else format_csv
        text = fmt(storage.load_history(hist_path))
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text)
            except OSError as exc:
                print(f"typedrill: cannot write {args.output}: {exc.strerror or exc}", file=sys.stderr)
                return 1
        else:
            sys.stdout.write(text)
        return 0
    if args.command == "weak-keys":
        history = storage.load_history(hist_path)
        print(format_weak_keys(weak.weak_keys(history, args.limit, last=args.last)))
        return 0

    rng = random.Random(args.seed)
    try:
        session, mode = build_session(args, storage.load_history(hist_path), rng, clock)
    except ValueError as exc:
        print(f"typedrill: {exc}", file=sys.stderr)
        return 1

    if runner is None:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print("typedrill: the drill needs an interactive terminal "
                  "(try `typedrill stats` or `typedrill weak-keys`)", file=sys.stderr)
            return 1
        try:
            import curses  # noqa: F401
        except ImportError:
            print("typedrill: curses is not available; on Windows run "
                  "`pip install windows-curses`", file=sys.stderr)
            return 1
        runner = _default_runner

    try:
        outcome = runner(session, mode)
    except KeyboardInterrupt:
        outcome = ABORTED
    if outcome == ABORTED:
        print("Drill stopped; partial drills are not saved.")
        return 0

    result = session.result()
    print(format_summary(result, mode))
    if not args.no_save:
        try:
            storage.add_record(storage.make_record(result, mode, now), hist_path)
        except OSError as exc:
            print(f"typedrill: could not save history: {exc}", file=sys.stderr)
    return 0
