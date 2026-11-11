import random

from typedrill.words import WORDS, clean_text, cycle_text, generate, text_words


def test_builtin_words_are_lowercase_ascii_and_unique():
    assert len(WORDS) >= 150
    assert all(w.isascii() and w.islower() for w in WORDS)
    assert len(set(WORDS)) == len(WORDS)


def test_generate_count_and_seed_determinism():
    a = generate(20, random.Random(1))
    b = generate(20, random.Random(1))
    assert a == b
    assert len(a.split()) == 20


def test_generate_no_immediate_repeats():
    text = generate(200, random.Random(3), pool=["a", "b"])
    words = text.split()
    assert all(x != y for x, y in zip(words, words[1:]))


def test_generate_single_word_pool_terminates():
    assert generate(3, pool=["x"]) == "x x x"


def test_generate_zero():
    assert generate(0) == ""


def test_clean_text_collapses_whitespace():
    assert clean_text("a \n\t b   c\n") == "a b c"


def test_clean_text_folds_unicode():
    assert clean_text("“smart” — café") == '"smart" - cafe'


def test_clean_text_drops_unmappable():
    assert clean_text("hi 中文 there") == "hi there"


def test_text_words_limit():
    assert text_words("one two three four", 2) == "one two"
    assert text_words("one two three four") == "one two three four"


def test_cycle_text_repeats():
    assert cycle_text("a b", 5) == "a b a b a"
    assert cycle_text("   ", 5) == ""
