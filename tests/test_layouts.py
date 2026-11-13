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


def test_finger_summary_groups_and_sorts():
    from typedrill.report import format_finger_summary
    stats = [KeyStat("p", 10, 3), KeyStat("[", 10, 1), KeyStat("a", 20, 2),
             KeyStat("é", 5, 1)]
    out = format_finger_summary(stats, "qwerty")
    assert out[0].startswith("Errors by finger")
    rows = [line.split() for line in out[2:]]
    assert rows[0][:2] == ["right", "pinky"] and rows[0][2:5] == ["4", "20", "20.0%"]
    assert rows[1][:2] == ["left", "pinky"] and rows[1][2] == "2"
    assert rows[2][0] == "unmapped" and rows[2][1] == "1"


def test_summary_only_with_layout():
    stats = [KeyStat("p", 10, 3)]
    assert "Errors by finger" in format_weak_keys(stats, "qwerty")
    assert "Errors by finger" not in format_weak_keys(stats)


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


def test_hand_summary_totals_and_balance():
    from typedrill.report import format_hand_summary

    stats = [KeyStat("a", 10, 3), KeyStat("j", 10, 1), KeyStat(" ", 5, 1), KeyStat("~", 4, 2)]
    out = "\n".join(format_hand_summary(stats, "qwerty"))
    rows = [line.split() for line in out.splitlines()]
    assert ["left", "3", "10", "30.0%"] in rows
    assert ["right", "1", "10", "10.0%"] in rows
    assert "thumb" in out and "unmapped" in out
    assert "Balance: 75.0% of errors on the left hand, 25.0% on the right" in out


def test_hand_summary_no_hand_errors():
    from typedrill.report import format_hand_summary

    out = format_hand_summary([KeyStat("~", 5, 2)], "qwerty")
    assert out[-1] == "Balance: no errors on either hand"


def test_weak_keys_layout_shows_hand_table_only_with_layout():
    stats = [KeyStat("a", 10, 3)]
    assert "Errors by hand" in format_weak_keys(stats, "dvorak")
    assert "Errors by hand" not in format_weak_keys(stats)


def test_cli_bad_layout(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["weak-keys", "--layout", "azerty"], env={"TYPEDRILL_HOME": str(tmp_path)})
    assert "invalid choice" in capsys.readouterr().err
