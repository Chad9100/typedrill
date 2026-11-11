"""Drill history kept in a JSON file inside the data directory."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from typedrill.scoring import Result

ENV_HOME = "TYPEDRILL_HOME"
HISTORY_FILE = "history.json"


def data_dir(env: Mapping[str, str] | None = None) -> Path:
    """TYPEDRILL_HOME if set, else ~/.typedrill."""
    env = os.environ if env is None else env
    custom = env.get(ENV_HOME)
    if custom:
        return Path(custom).expanduser()
    return Path.home() / ".typedrill"


def history_path(env: Mapping[str, str] | None = None) -> Path:
    return data_dir(env) / HISTORY_FILE


def make_record(result: Result, mode: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    return {
        "ts": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "seconds": round(result.seconds, 2),
        "wpm": round(result.wpm, 2),
        "accuracy": round(result.accuracy, 2),
        "errors": result.errors,
        "chars": result.correct_chars,
        "keys": {
            k: [n, result.key_errors.get(k, 0)] for k, n in sorted(result.key_attempts.items())
        },
    }


def _valid(rec: Any) -> bool:
    return (
        isinstance(rec, dict)
        and isinstance(rec.get("wpm"), (int, float))
        and isinstance(rec.get("accuracy"), (int, float))
        and isinstance(rec.get("keys", {}), dict)
    )


def load_history(path: Path | None = None) -> list[dict[str, Any]]:
    """All saved records. A missing file is empty history; an unreadable one
    is moved aside to ``history.json.bad`` so it is never silently lost."""
    path = path or history_path()
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("history is not a list")
    except ValueError:
        bad = path.with_name(path.name + ".bad")
        try:
            os.replace(path, bad)
        except OSError:
            pass
        return []
    return [r for r in data if _valid(r)]


def save_history(records: list[dict[str, Any]], path: Path | None = None) -> None:
    path = path or history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(records, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def add_record(record: dict[str, Any], path: Path | None = None) -> None:
    records = load_history(path)
    records.append(record)
    save_history(records, path)
