import json
from datetime import datetime, timezone
from pathlib import Path

from typedrill import storage
from typedrill.scoring import score


def result():
    return score(30, 25, [("a", "a"), ("b", "x"), ("a", "a")])


def test_data_dir_env(tmp_path):
    assert storage.data_dir({"TYPEDRILL_HOME": str(tmp_path)}) == tmp_path


def test_data_dir_default_is_home_dot_typedrill():
    assert storage.data_dir({}) == Path.home() / ".typedrill"


def test_history_path_name(tmp_path):
    assert storage.history_path({"TYPEDRILL_HOME": str(tmp_path)}) == tmp_path / "history.json"


def test_make_record_fields():
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    rec = storage.make_record(result(), "words", now)
    assert rec["ts"] == "2026-01-02T03:04:05Z"
    assert rec["mode"] == "words"
    assert rec["keys"] == {"a": [2, 0], "b": [1, 1]}
    assert rec["errors"] == 1


def test_missing_file_is_empty(tmp_path):
    assert storage.load_history(tmp_path / "nope.json") == []


def test_roundtrip_creates_directory(tmp_path):
    path = tmp_path / "deep" / "history.json"
    storage.add_record(storage.make_record(result(), "time"), path)
    storage.add_record(storage.make_record(result(), "words"), path)
    got = storage.load_history(path)
    assert [r["mode"] for r in got] == ["time", "words"]


def test_corrupt_file_moved_aside(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{not json", encoding="utf-8")
    assert storage.load_history(path) == []
    assert not path.exists()
    assert (tmp_path / "history.json.bad").read_text(encoding="utf-8") == "{not json"


def test_wrong_shape_moved_aside(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"a": 1}', encoding="utf-8")
    assert storage.load_history(path) == []
    assert (tmp_path / "history.json.bad").exists()


def test_invalid_records_skipped(tmp_path):
    path = tmp_path / "history.json"
    good = storage.make_record(result(), "words")
    path.write_text(json.dumps([good, {"wpm": "fast"}, 5]), encoding="utf-8")
    assert storage.load_history(path) == [good]


def test_bom_tolerated(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("﻿[]", encoding="utf-8")
    assert storage.load_history(path) == []
    assert path.exists()


def test_no_tmp_file_left(tmp_path):
    path = tmp_path / "history.json"
    storage.add_record(storage.make_record(result(), "words"), path)
    assert [p.name for p in tmp_path.iterdir()] == ["history.json"]


def test_load_history_when_parent_is_a_file(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert storage.load_history(blocker / "sub" / "history.json") == []
