"""Built-in word list, text cleaning for --text files, and drill generation."""

from __future__ import annotations

import random
import unicodedata

WORDS = tuple(
    """
about above add after again air all almost along also always and animal answer any
are around ask away back because been before began begin being below between big
book both boy but call came can car carry change children city close come could
country cut day did different does dog door down draw each earth eat end enough
even every example eye face family far farm father feet few find fire first fish
follow food for form found four from get girl give go good great group grow had
hand hard has have head hear help here high home house how idea important in into
is it just keep kind know land large last late learn leave left let letter life
light like line list little live long look made make man many may mean men might
mile mind miss more most mother mountain move much must name near need never new
next night not now number object of off often oil old once one only open or other
our out over own page paper part people picture place plant play point put quick
quite rain read really red right river road rock run said same saw say school sea
second see seem sentence set she should show side small so some song soon sound
spell stand start state still stop story study such take talk tell than that the
their them then there these they thing think this those thought three through time
to together too took tree try turn two under until up us use very walk want was
watch water way we well went were what when where which while white who why will
with without word work world would write year you young
""".split()
)

_REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", " ": " ",
}


def clean_text(raw: str) -> str:
    """Reduce text to typeable printable ASCII with single spaces."""
    for old, new in _REPLACEMENTS.items():
        raw = raw.replace(old, new)
    folded = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    return " ".join(folded.split())


def generate(count: int, rng: random.Random | None = None, pool: list[str] | None = None) -> str:
    """``count`` random words joined by spaces, never repeating one twice in a row."""
    rng = rng or random.Random()
    pool = list(pool or WORDS)
    out: list[str] = []
    for _ in range(max(0, count)):
        word = rng.choice(pool)
        if len(pool) > 1:
            while out and word == out[-1]:
                word = rng.choice(pool)
        out.append(word)
    return " ".join(out)


def text_words(text: str, count: int | None = None) -> str:
    """The first ``count`` words of cleaned text (all of it when count is None)."""
    words = clean_text(text).split()
    if count is not None:
        words = words[:count]
    return " ".join(words)


def cycle_text(text: str, count: int) -> str:
    """Repeat the words of ``text`` until there are ``count`` of them."""
    words = clean_text(text).split()
    if not words:
        return ""
    return " ".join(words[i % len(words)] for i in range(count))
