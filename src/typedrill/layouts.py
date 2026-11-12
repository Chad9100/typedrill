"""Keyboard layouts: which row and finger a key belongs to (touch typing)."""

from __future__ import annotations

# Finger for each physical column, left to right. The last columns of a row
# (brackets, quotes, equals) are reached by the right pinky.
FINGERS = [
    "left pinky", "left ring", "left middle", "left index", "left index",
    "right index", "right index", "right middle", "right ring", "right pinky",
    "right pinky", "right pinky",
]

NUMBER_ROW = "1234567890-="

# (top, home, bottom) letter rows; each string is one key per physical column.
LAYOUTS: dict[str, tuple[str, str, str]] = {
    "qwerty": ("qwertyuiop[]", "asdfghjkl;'", "zxcvbnm,./"),
    "dvorak": ("',.pyfgcrl/=", "aoeuidhtns-", ";qjkxbmwvz"),
    "colemak": ("qwfpgjluy;[]", "arstdhneio'", "zxcvbkm,./"),
}

ROW_NAMES = ("top", "home", "bottom")


def locate(layout: str, key: str) -> tuple[str, str] | None:
    """(row, finger) for ``key`` on ``layout``, or None if it is not on the
    main block (unknown character, or a layout name that does not exist)."""
    rows = LAYOUTS.get(layout)
    if rows is None or len(key) != 1:
        return None
    if key == " ":
        return "space", "thumb"
    low = key.lower()
    for name, row in zip(ROW_NAMES, rows):
        col = row.find(low)
        if col >= 0:
            return name, FINGERS[col]
    col = NUMBER_ROW.find(low)
    if col >= 0:
        return "number", FINGERS[col]
    return None
