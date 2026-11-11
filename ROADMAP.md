# Roadmap

Ideas for after v0.1, roughly in order of usefulness.

1. **Real-terminal verification** - drive the curses screen in a pty on
   Linux/macOS (and a Windows console) in CI, beyond the fake-screen tests.
2. **Bigram/trigram weakness** - track the previous key so slow or error-prone
   key pairs ("th", "ei") are found, not just single keys.
3. **Per-key speed** - record inter-key latency and report slow keys as well as
   inaccurate ones.
4. **Punctuation and numbers modes** - optional capitals, punctuation and
   digits in generated text.
5. **More word lists** - bundled lists by difficulty. (`--wordlist FILE` is
   done.)
6. ~~**Progress charts** - `typedrill stats --chart` with a text sparkline of WPM
   over time.~~ Done.
7. **Quote and code modes** - type short quotes or source snippets, with
   indentation handled sensibly.
8. **Stop-on-error mode** - optional strict mode where a wrong key blocks until
   corrected.
9. ~~**Export** - `typedrill export --csv` for history.~~ Done.
11. ~~**JSON export** - `typedrill export --json` including per-key counts.~~ Done.
12. ~~**Delete history** - `typedrill reset` with confirmation.~~ Done.
10. **Keyboard layouts** - show which finger/row a weak key belongs to for
    QWERTY, Dvorak and Colemak.
