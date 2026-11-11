import json
from datetime import datetime, timezone

import pytest

from typedrill import storage
from typedrill.cli import DEFAULT_WORDS, build_parser, main
from typedrill.tui import ABORTED, FINISHED

NOW = datetime(2026, 5, 6, 7, 8, 9, tzinfo=timezone.utc)


class Clock:
    t = 0.0

    def __call__(self):
        return self.t


def typist(mistakes=0, seconds=30.0, clock=None):
    """A stand-in runner that types the target, botching the first few characters."""
    seen = {}

    def run(session, mode):
        seen["session"], seen["mode"] = session, mode
        text = session.target
        for i, ch in enumerate(text):
            session.type_char("#" if i < mistakes else ch)
            if i == 0 and clock:
                clock.t += seconds
            if session.finished:
                break
        return FINISHED

    run.seen = seen
    return run


def run_cli(argv, tmp_path, runner=None, clock=None):
    env = {"TYPEDRILL_HOME": str(tmp_path)}
    return main(argv, env=env, runner=runner, now=NOW, clock=clock)


def history(tmp_path):
    return storage.load_history(tmp_path / "history.json")


def test_default_drill_is_25_words(tmp_path, capsys):
    run = typist()
    assert run_cli(["--seed", "1"], tmp_path, run) == 0
    assert len(run.seen["session"].target.split()) == DEFAULT_WORDS
    assert run.seen["mode"] == "words"
    assert "words:" in capsys.readouterr().out


def test_words_option(tmp_path):
    run = typist()
    run_cli(["--words", "7"], tmp_path, run)
    assert len(run.seen["session"].target.split()) == 7


def test_time_option_sets_limit(tmp_path):
    run = typist()
    run_cli(["--time", "45"], tmp_path, run)
    assert run.seen["session"].limit == 45.0
    assert run.seen["mode"] == "time"


def test_time_and_words_conflict(tmp_path):
    with pytest.raises(SystemExit):
        run_cli(["--time", "5", "--words", "5"], tmp_path)


@pytest.mark.parametrize("bad", ["0", "-3", "abc"])
def test_bad_numbers_rejected(bad, tmp_path):
    with pytest.raises(SystemExit):
        run_cli(["--words", bad], tmp_path)


def test_seed_makes_drill_repeatable(tmp_path):
    a, b = typist(), typist()
    run_cli(["--seed", "9", "--no-save"], tmp_path, a)
    run_cli(["--seed", "9", "--no-save"], tmp_path, b)
    assert a.seen["session"].target == b.seen["session"].target


def test_result_saved_to_history(tmp_path):
    run_cli(["--seed", "1", "--words", "3"], tmp_path, typist())
    (rec,) = history(tmp_path)
    assert rec["mode"] == "words" and rec["ts"] == "2026-05-06T07:08:09Z"
    assert rec["accuracy"] == 100.0


def test_no_save_flag(tmp_path):
    run_cli(["--no-save", "--words", "3"], tmp_path, typist())
    assert not (tmp_path / "history.json").exists()


def test_mistakes_recorded_per_key(tmp_path):
    run_cli(["--words", "3", "--seed", "1"], tmp_path, typist(mistakes=2))
    (rec,) = history(tmp_path)
    assert rec["errors"] == 2
    assert sum(e for _, e in rec["keys"].values()) == 2


def test_aborted_drill_not_saved(tmp_path, capsys):
    assert run_cli([], tmp_path, lambda s, m: ABORTED) == 0
    assert "not saved" in capsys.readouterr().out
    assert not (tmp_path / "history.json").exists()


def test_ctrl_c_counts_as_abort(tmp_path):
    def boom(session, mode):
        raise KeyboardInterrupt

    assert run_cli([], tmp_path, boom) == 0
    assert history(tmp_path) == []


def test_wordlist_file_is_the_word_pool(tmp_path):
    f = tmp_path / "w.txt"
    f.write_text("alpha beta\ngamma alpha\n", encoding="utf-8")
    run = typist()
    run_cli(["--wordlist", str(f), "--words", "40", "--seed", "2", "--no-save"], tmp_path, run)
    target = run.seen["session"].target.split()
    assert len(target) == 40
    assert set(target) == {"alpha", "beta", "gamma"}
    assert run.seen["mode"] == "words"


def test_wordlist_missing_file(tmp_path, capsys):
    assert run_cli(["--wordlist", str(tmp_path / "nope.txt")], tmp_path, typist()) == 1
    assert "cannot read" in capsys.readouterr().err


def test_wordlist_empty_file(tmp_path, capsys):
    f = tmp_path / "e.txt"
    f.write_text("  \n", encoding="utf-8")
    assert run_cli(["--wordlist", str(f)], tmp_path, typist()) == 1
    assert "no typeable words" in capsys.readouterr().err


def test_wordlist_rejects_weak(tmp_path, capsys):
    f = tmp_path / "w.txt"
    f.write_text("a b", encoding="utf-8")
    assert run_cli(["--wordlist", str(f), "--weak"], tmp_path, typist()) == 1
    assert "cannot be combined" in capsys.readouterr().err


def test_wordlist_directory_is_an_error(tmp_path, capsys):
    assert run_cli(["--wordlist", str(tmp_path)], tmp_path, typist()) == 1
    assert "cannot read" in capsys.readouterr().err


def test_text_file_drill(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("The quick\nbrown fox\n", encoding="utf-8")
    run = typist()
    run_cli(["--text", str(f), "--no-save"], tmp_path, run)
    assert run.seen["session"].target == "The quick brown fox"
    assert run.seen["mode"] == "text"


def test_text_file_with_word_limit(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("one two three four", encoding="utf-8")
    run = typist()
    run_cli(["--text", str(f), "--words", "2", "--no-save"], tmp_path, run)
    assert run.seen["session"].target == "one two"


def test_text_file_with_time_cycles(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("ab cd", encoding="utf-8")
    run = typist()
    run_cli(["--text", str(f), "--time", "10", "--no-save"], tmp_path, run)
    assert run.seen["session"].limit == 10.0
    assert run.seen["session"].extend is not None
    assert run.seen["session"].target.startswith("ab cd ab cd")


def test_text_file_missing(tmp_path, capsys):
    assert run_cli(["--text", str(tmp_path / "nope.txt")], tmp_path, typist()) == 1
    assert "cannot read" in capsys.readouterr().err


def test_text_file_blank(tmp_path, capsys):
    f = tmp_path / "t.txt"
    f.write_text("  \n \n", encoding="utf-8")
    assert run_cli(["--text", str(f)], tmp_path, typist()) == 1
    assert "no typeable text" in capsys.readouterr().err


def test_text_file_with_bom(tmp_path):
    f = tmp_path / "t.txt"
    f.write_bytes(b"\xef\xbb\xbfhello world")
    run = typist()
    run_cli(["--text", str(f), "--no-save"], tmp_path, run)
    assert run.seen["session"].target == "hello world"


def test_stats_empty(tmp_path, capsys):
    assert run_cli(["stats"], tmp_path) == 0
    assert "No drills" in capsys.readouterr().out


def test_stats_after_drills(tmp_path, capsys):
    run_cli(["--words", "3", "--seed", "1"], tmp_path, typist())
    run_cli(["--words", "3", "--seed", "2"], tmp_path, typist())
    capsys.readouterr()
    run_cli(["stats"], tmp_path)
    assert "Sessions:        2" in capsys.readouterr().out


def test_weak_keys_report_from_history(tmp_path, capsys):
    rec = {"ts": "2026-01-01T00:00:00Z", "mode": "words", "seconds": 30, "wpm": 40,
           "accuracy": 90, "errors": 9, "chars": 100, "keys": {"q": [10, 9], "e": [50, 1]}}
    (tmp_path / "history.json").write_text(json.dumps([rec]), encoding="utf-8")
    run_cli(["weak-keys"], tmp_path)
    out = capsys.readouterr().out
    assert out.index("\n  q ") < out.index("\n  e ") and "90.0%" in out


def test_weak_keys_empty(tmp_path, capsys):
    run_cli(["weak-keys"], tmp_path)
    assert "No weak keys" in capsys.readouterr().out


def test_weak_keys_limit_and_last(tmp_path, capsys):
    old = {"wpm": 1, "accuracy": 1, "keys": {"z": [10, 10]}}
    new = {"wpm": 1, "accuracy": 1, "keys": {"a": [10, 5], "b": [10, 4]}}
    (tmp_path / "history.json").write_text(json.dumps([old, new]), encoding="utf-8")
    run_cli(["weak-keys", "--last", "1", "--limit", "1"], tmp_path)
    out = capsys.readouterr().out
    assert " a " in out and " b " not in out and " z " not in out


def test_weak_drill_uses_history(tmp_path):
    rec = {"wpm": 1, "accuracy": 1, "keys": {"z": [10, 5]}}
    (tmp_path / "history.json").write_text(json.dumps([rec]), encoding="utf-8")
    run = typist()
    run_cli(["--weak", "--seed", "1", "--no-save"], tmp_path, run)
    assert run.seen["mode"] == "weak"
    assert all("z" in w for w in run.seen["session"].target.split())


def test_weak_drill_without_history(tmp_path, capsys):
    assert run_cli(["--weak"], tmp_path, typist()) == 1
    assert "no weak keys" in capsys.readouterr().err


def test_weak_time_drill_extends_with_weak_words(tmp_path):
    rec = {"wpm": 1, "accuracy": 1, "keys": {"z": [10, 5]}}
    (tmp_path / "history.json").write_text(json.dumps([rec]), encoding="utf-8")
    run = typist()
    run_cli(["--weak", "--time", "5", "--no-save"], tmp_path, run)
    session = run.seen["session"]
    assert all("z" in w for w in session.extend().split())


def test_non_interactive_terminal_refused(tmp_path, capsys, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO())  # never a tty
    assert run_cli([], tmp_path) == 1
    assert "interactive terminal" in capsys.readouterr().err


def test_save_failure_is_reported_not_fatal(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    code = main(["--words", "2"], env={"TYPEDRILL_HOME": str(blocker / "sub")},
                runner=typist(), now=NOW)
    assert code == 0
    assert "could not save" in capsys.readouterr().err


def seed_history(tmp_path):
    run_cli(["--words", "3"], tmp_path, typist())
    run_cli(["--words", "3"], tmp_path, typist(mistakes=2))


def test_reset_confirmed_deletes_history(tmp_path, capsys, monkeypatch):
    seed_history(tmp_path)
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    assert run_cli(["reset"], tmp_path) == 0
    assert "Deleted 2 saved drill(s)." in capsys.readouterr().out
    assert not (tmp_path / "history.json").exists()


@pytest.mark.parametrize("answer", ["", "n", "no", "maybe"])
def test_reset_declined_keeps_history(answer, tmp_path, capsys, monkeypatch):
    seed_history(tmp_path)
    capsys.readouterr()
    monkeypatch.setattr("builtins.input", lambda prompt="": answer)
    assert run_cli(["reset"], tmp_path) == 1
    assert "Nothing deleted." in capsys.readouterr().out
    assert len(history(tmp_path)) == 2


def test_reset_eof_counts_as_no(tmp_path, monkeypatch):
    seed_history(tmp_path)

    def eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    assert run_cli(["reset"], tmp_path) == 1
    assert len(history(tmp_path)) == 2


def test_reset_yes_skips_prompt(tmp_path, monkeypatch):
    seed_history(tmp_path)

    def fail(prompt=""):
        raise AssertionError("should not prompt")

    monkeypatch.setattr("builtins.input", fail)
    assert run_cli(["reset", "--yes"], tmp_path) == 0
    assert history(tmp_path) == []


def test_reset_with_no_history(tmp_path, capsys):
    assert run_cli(["reset", "-y"], tmp_path) == 0
    assert "No history to delete." in capsys.readouterr().out


def test_reset_under_a_file_is_empty_history(tmp_path, capsys):
    blocker = tmp_path / "f"
    blocker.write_text("x")
    assert main(["reset"], env={"TYPEDRILL_HOME": str(blocker / "sub")}) == 0
    assert "No history to delete." in capsys.readouterr().out


def test_export_stdout_csv(tmp_path, capsys):
    seed_history(tmp_path)
    capsys.readouterr()
    assert run_cli(["export", "--csv"], tmp_path) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "ts,mode,seconds,wpm,accuracy,errors,chars"
    assert len(lines) == 3
    assert lines[1].startswith("2026-05-06T07:08:09Z,words,")
    assert lines[1].split(",")[5] == "0"
    assert lines[2].split(",")[5] == "2"


def test_export_empty_history_is_header_only(tmp_path, capsys):
    assert run_cli(["export"], tmp_path) == 0
    assert capsys.readouterr().out == "ts,mode,seconds,wpm,accuracy,errors,chars\n"


def test_export_to_file(tmp_path, capsys):
    seed_history(tmp_path)
    capsys.readouterr()
    out = tmp_path / "out.csv"
    assert run_cli(["export", "-o", str(out)], tmp_path) == 0
    assert capsys.readouterr().out == ""
    assert len(out.read_bytes().splitlines()) == 3
    assert b"\r" not in out.read_bytes()


def test_export_unwritable_output_reports_error(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    # a path under a regular file: NotADirectoryError on Linux, other OSError on Windows
    assert run_cli(["export", "-o", str(blocker / "out.csv")], tmp_path) == 1
    assert "cannot write" in capsys.readouterr().err


def test_export_json_includes_keys(tmp_path, capsys):
    seed_history(tmp_path)
    capsys.readouterr()
    assert run_cli(["export", "--json"], tmp_path) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2
    assert data[0]["ts"] == "2026-05-06T07:08:09Z"
    assert data[1]["errors"] == 2
    assert all(isinstance(v, list) and len(v) == 2 for v in data[0]["keys"].values())
    assert data == history(tmp_path)


def test_export_json_empty_and_file(tmp_path, capsys):
    assert run_cli(["export", "--json"], tmp_path) == 0
    assert capsys.readouterr().out == "[]\n"
    seed_history(tmp_path)
    capsys.readouterr()
    out = tmp_path / "out.json"
    assert run_cli(["export", "--json", "-o", str(out)], tmp_path) == 0
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 2
    assert b"\r" not in out.read_bytes()


def test_export_csv_and_json_conflict(tmp_path):
    with pytest.raises(SystemExit):
        run_cli(["export", "--csv", "--json"], tmp_path)


def test_stats_chart_empty(tmp_path, capsys):
    assert run_cli(["stats", "--chart"], tmp_path) == 0
    assert "No drills recorded yet" in capsys.readouterr().out


def test_stats_chart_rising(tmp_path, capsys):
    recs = [{"wpm": w, "accuracy": 95.0, "keys": {}} for w in (20, 30, 40, 50)]
    storage.save_history(recs, tmp_path / "history.json")
    assert run_cli(["stats", "--chart"], tmp_path) == 0
    out = capsys.readouterr().out
    assert "last 4 session(s)" in out
    assert "low 20.0  high 50.0  first 20.0  latest 50.0  change +30.0" in out
    line = out.splitlines()[1].strip()
    assert line[0] == "_" and line[-1] == "@" and len(line) == 4
    assert list(line) == sorted(line, key="_.-=+*#@".index)


def test_chart_flat_and_width():
    from typedrill.report import format_chart, sparkline

    assert sparkline([5, 5, 5]) == "+++"
    assert sparkline([]) == ""
    recs = [{"wpm": float(i), "accuracy": 90.0} for i in range(100)]
    lines = format_chart(recs, width=10).splitlines()
    assert len(lines[1].strip()) == 10
    assert "last 10 session(s)" in lines[0]
    assert "first 90.0  latest 99.0" in lines[2]


def test_version(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])
    assert "typedrill" in capsys.readouterr().out
