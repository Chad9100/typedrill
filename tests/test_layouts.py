import pytest

from typedrill import storage
from typedrill.cli import main
from typedrill.layouts import FINGERS, LAYOUTS, NUMBER_ROW, locate
from typedrill.report import format_weak_keys
from typedrill.weak import KeyStat


def test_locate_qwerty():
    assert locate("qwerty", "a") == ("home", "left pinky")
    assert locate("qwerty", "F") == ("home", "left index")
    assert locate("qwerty", "p") == ("top", "right pinky")
    assert locate("qwerty", "m") == ("bottom", "right index")
    assert locate("qwerty", "5") == ("number", "left index")
    assert locate("qwerty", " ") == ("space", "thumb")


def test_locate_differs_by_layout():
    assert locate("dvorak", "e") == ("home", "left middle")
    assert locate("qwerty", "e") == ("top", "left middle")
    assert locate("colemak", "r") == ("home", "left ring")
    assert locate("colemak", "i") == ("home", "right ring")


def test_locate_unknown():
    assert locate("qwerty", "é") is None
    assert locate("qwerty", "ab") is None
    assert locate("azerty", "a") is None


@pytest.mark.parametrize("name", sorted(LAYOUTS))
def test_layout_tables_consistent(name):
    top, home, bottom = LAYOUTS[name]
    letters = top + home + bottom
    assert len(set(letters)) == len(letters)
    assert len(top) <= len(FINGERS) and len(home) <= len(FINGERS)
    assert len(bottom) <= len(FINGERS) and len(NUMBER_ROW) <= len(FINGERS)
    for ch in "abcdefghijklmnopqrstuvwxyz":
        assert locate(name, ch) is not None, ch


def test_format_with_layout():
    stats = [KeyStat("p", 10, 3), KeyStat("é", 8, 2)]
    out = format_weak_keys(stats, "qwerty").splitlines()
    assert out[0] == "Weak keys (worst first):  [qwerty layout]"
    assert out[1].endswith("row     finger")
    assert out[2].endswith("30.0%  top     right pinky")
    assert out[3].endswith("25.0%  -       -")


def test_format_without_layout_unchanged():
    out = format_weak_keys([KeyStat("p", 10, 3)])
    assert "finger" not in out and "layout" not in out


def test_cli_layout(tmp_path, capsys):
    rec = {"wpm": 40.0, "accuracy": 90.0, "keys": {"a": [10, 4], "p": [10, 2]}}
    storage.save_history([rec], tmp_path / "history.json")
    code = main(["weak-keys", "--layout", "dvorak"], env={"TYPEDRILL_HOME": str(tmp_path)})
    assert code == 0
    out = capsys.readouterr().out
    assert "[dvorak layout]" in out
    assert "home    left pinky" in out  # a
    assert "top     left index" in out  # p


def test_cli_bad_layout(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["weak-keys", "--layout", "azerty"], env={"TYPEDRILL_HOME": str(tmp_path)})
    assert "invalid choice" in capsys.readouterr().err
