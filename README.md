# typedrill

A terminal typing trainer. It shows live WPM and accuracy while you type,
highlights every mistyped character, remembers your history, and turns the
keys you miss most into targeted drills. Python 3.10+, standard library only.

On Windows the `windows-curses` package is installed automatically (it is an
environment-marked dependency in `pyproject.toml`); Linux and macOS use the
curses that ships with Python.

## Install

```
pip install -e .
```

## Usage

```
typedrill                     # 25 random words
typedrill --words 50          # 50 random words
typedrill --time 60           # as many words as you can in 60 seconds
typedrill --text notes.txt    # type your own text (whole file, or --words N of it)
typedrill --wordlist my.txt   # random words drawn from your own list
typedrill --weak              # a drill built from your weak keys
typedrill stats               # history summary
typedrill stats --chart       # WPM and accuracy trend as text sparklines
typedrill weak-keys           # keys ranked by error rate
typedrill weak-keys --layout dvorak   # plus row and finger (qwerty, dvorak, colemak)
typedrill export --csv        # history as CSV on stdout (or -o FILE)
typedrill export --json       # history as JSON, with per-key counts
typedrill reset               # delete all history, after confirmation (-y skips it)
```

In the drill: type the text shown. Correct characters turn green, mistakes
turn red (a mistyped space shows as `_`), `Backspace` fixes a typo, `Esc`
quits. The clock starts on your first keystroke. A correction fixes the text
but the miss still counts against accuracy and against the key you got wrong.
Only finished drills are saved; use `--no-save` to skip saving.

Scoring: WPM = correct characters / 5 / minutes. Accuracy = correct keystrokes
/ all keystrokes. Errors are charged to the key you *should* have hit, which is
what `weak-keys` aggregates (keys tried fewer than 5 times are ignored).

`--layout` maps each recorded character to a row and finger using standard
touch-typing columns on an ANSI-style keyboard; it is a lookup table, not
something detected from your hardware, and shifted symbols are not mapped.

History is a JSON file, `history.json`, in `~/.typedrill`, or in the directory
named by the `TYPEDRILL_HOME` environment variable. If the file is ever
unreadable it is moved to `history.json.bad` rather than overwritten.

## Real output

The non-interactive commands below were captured from the installed
`typedrill` command. The history shown was seeded through the library API by a
script that simulates a typist, because a full-screen drill cannot be driven
from a script; so the numbers are demo data, not a human's typing.

```
$ typedrill stats   (empty history)
No drills recorded yet. Run `typedrill` to start one.

$ typedrill --weak   (empty history)
typedrill: no weak keys in your history yet; do a few drills first

$ typedrill < /dev/null   (not a terminal)
typedrill: the drill needs an interactive terminal (try `typedrill stats` or `typedrill weak-keys`)

$ typedrill stats
Sessions:        6
Time practised:  3.9 min
Best WPM:        52.4
Average WPM:     47.0 (last 10: 47.0)
Average accuracy: 97.1%

Last 5 sessions:
  when                  mode    wpm   acc
  2026-11-02 18:00:00   words   48.4  95.4%
  2026-11-03 18:00:00   words   47.7  98.7%
  2026-11-04 18:00:00   words   43.3  97.5%
  2026-11-05 18:00:00   words   46.9  95.1%
  2026-11-06 18:00:00   words   52.4  98.7%

$ typedrill stats --chart   (14 simulated sessions; ASCII only, "_" lowest to "@" highest)
WPM over the last 14 session(s), oldest to newest:
  __.__.==++*##@
  low 29.0  high 48.4  first 29.4  latest 48.4  change +19.0

Accuracy:
  +*_@-++.@#_*_+
  low 93.2%  high 98.2%

$ typedrill weak-keys
Weak keys (worst first):
  key     errors  attempts  error rate
  p            2         7       28.6%
  h            5        43       11.6%
  k            1        10       10.0%
  y            1        20        5.0%
  g            1        21        4.8%
  t            3        77        3.9%
  w            1        27        3.7%
  o            2        65        3.1%

Drill them with: typedrill --weak

$ typedrill weak-keys --layout dvorak --limit 3   (a separate one-session demo history)
Weak keys (worst first):  [dvorak layout]
  key     errors  attempts  error rate  row     finger
  p            2         7       28.6%  top     left index
  h            5        43       11.6%  home    right index
  k            1        10       10.0%  bottom  left index

Drill them with: typedrill --weak

$ typedrill export --csv   (three demo records, seeded like the above)
ts,mode,seconds,wpm,accuracy,errors,chars
2026-11-02T18:00:00Z,words,30.5,45.2,96.5,3,114
2026-11-03T18:00:00Z,words,30.5,48.2,96.5,2,114
2026-11-04T18:00:00Z,words,30.5,51.2,96.5,1,114

$ typedrill export -o no_such_dir/x.csv
typedrill: cannot write no_such_dir/x.csv: No such file or directory

$ typedrill export --json   (two tiny demo records typed by a simulated typist)
[
  {"accuracy": 100.0, "chars": 3, "errors": 0, "keys": {"a": [1, 0], "c": [1, 0], "t": [1, 0]}, "mode": "words", "seconds": 1.0, "ts": "2026-11-02T18:00:00Z", "wpm": 36.0},
  {"accuracy": 66.67, "chars": 2, "errors": 1, "keys": {"a": [1, 1], "c": [1, 0], "t": [1, 0]}, "mode": "words", "seconds": 1.0, "ts": "2026-11-03T18:00:00Z", "wpm": 24.0}
]

$ typedrill export --csv --json
usage: typedrill export [-h] [--csv | --json] [-o FILE]
typedrill export: error: argument --json: not allowed with argument --csv
```

In the JSON, each key maps to `[attempts, errors]`. `export --csv` leaves out
the per-key counts. Both use LF line endings.

The error message text after the colon comes from the operating system.

### Deleting history

`typedrill reset` deletes the history file after a `[y/N]` question (only `y`
or `yes` confirms; anything else, or a closed stdin, cancels with exit code 1).
`-y` skips the question. Real output, with piped answers (so the typed answer
is not echoed and the reply follows the prompt on the same line):

```
$ echo n | typedrill reset
Delete 3 saved drill(s)? This cannot be undone. [y/N] Nothing deleted.
exit=1
$ echo y | typedrill reset
Delete 3 saved drill(s)? This cannot be undone. [y/N] Deleted 3 saved drill(s).
exit=0
$ typedrill reset
No history to delete.
exit=0
```

Only `history.json` is removed (a `history.json.bad` set aside after
corruption is left alone). The prompt was exercised with piped input and in
tests, not typed at an interactive console.

### Custom word lists

`--wordlist FILE` replaces the built-in words with the whitespace-separated
words in FILE (cleaned to ASCII, duplicates dropped). It cannot be combined
with `--text` or `--weak`. Real error output (a piped run, no terminal):

```
$ typedrill --wordlist empty.txt
typedrill: empty.txt has no typeable words
$ typedrill --wordlist missing.txt
typedrill: cannot read missing.txt: No such file or directory
$ typedrill --wordlist w.txt --weak
typedrill: --wordlist cannot be combined with --text or --weak
```

The word choice from a list is covered by tests with a stand-in runner; an
actual drill from a custom list was not run in a real terminal.

## What was and was not tested

The full-screen UI has only been tested with a fake screen and a stand-in
curses module (see `tests/test_tui.py`); it has not been run in a real
terminal. This is the fake-screen render after typing
`the quick brwwn fox jum` (text only, colours are not captured by the fake):

```
typedrill    9.0s    29.3 wpm    95.7% acc

  the quick brown fox jumps over the lazy dog
  and keeps running far away





Esc: quit   Backspace: correct a typo
```

Scoring, the session state machine, storage, weak-key analysis and the CLI
are plain Python with an injected clock and are covered by the test suite
(`pytest`).

## Layout

- `scoring.py` - WPM, accuracy, per-key counts (pure)
- `session.py` - drill state machine, injected clock, UI-independent
- `words.py` - built-in word list, text cleaning, drill generation
- `storage.py` - history JSON in the data dir
- `weak.py` - weak-key ranking and weak-key drills
- `report.py` - text for `stats` / `weak-keys`
- `tui.py` - the curses layer (wrapping, drawing, key loop)
- `cli.py` - argument parsing and wiring

## License

MIT
