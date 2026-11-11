"""Plain-text reports for ``stats`` and ``weak-keys``."""

from __future__ import annotations

import csv
import io
from typing import Any

from typedrill.scoring import Result
from typedrill.weak import KeyStat


def key_label(key: str) -> str:
    return "space" if key == " " else key


def format_summary(result: Result, mode: str) -> str:
    return (
        f"{mode}: {result.wpm:.1f} wpm, {result.accuracy:.1f}% accuracy, "
        f"{result.errors} errors in {result.seconds:.1f}s"
    )


def format_stats(history: list[dict[str, Any]], recent: int = 5) -> str:
    if not history:
        return "No drills recorded yet. Run `typedrill` to start one."
    wpms = [float(r["wpm"]) for r in history]
    accs = [float(r["accuracy"]) for r in history]
    total = sum(float(r.get("seconds", 0)) for r in history)
    last10 = wpms[-10:]
    lines = [
        f"Sessions:        {len(history)}",
        f"Time practised:  {total / 60:.1f} min",
        f"Best WPM:        {max(wpms):.1f}",
        f"Average WPM:     {sum(wpms) / len(wpms):.1f} (last 10: {sum(last10) / len(last10):.1f})",
        f"Average accuracy: {sum(accs) / len(accs):.1f}%",
        "",
        f"Last {min(recent, len(history))} sessions:",
        "  when                  mode    wpm   acc",
    ]
    for r in history[-recent:]:
        when = str(r.get("ts", "?")).replace("T", " ").rstrip("Z")
        lines.append(
            f"  {when:<20}  {str(r.get('mode', '?')):<6} {float(r['wpm']):>5.1f} {float(r['accuracy']):>5.1f}%"
        )
    return "\n".join(lines)


CSV_COLUMNS = ["ts", "mode", "seconds", "wpm", "accuracy", "errors", "chars"]


def format_csv(history: list[dict[str, Any]]) -> str:
    """History as CSV text (header plus one row per drill, LF line ends).
    The per-key counts are left out; fields a record lacks are empty."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for r in history:
        writer.writerow([r.get(c, "") for c in CSV_COLUMNS])
    return out.getvalue()


def format_weak_keys(stats: list[KeyStat]) -> str:
    if not stats:
        return "No weak keys yet: nothing with errors and enough attempts in your history."
    lines = ["Weak keys (worst first):", "  key     errors  attempts  error rate"]
    for s in stats:
        lines.append(
            f"  {key_label(s.key):<6}  {s.errors:>6}  {s.attempts:>8}  {s.error_rate:>9.1f}%"
        )
    lines.append("")
    lines.append("Drill them with: typedrill --weak")
    return "\n".join(lines)
