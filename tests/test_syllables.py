import pytest

from papa.syllables import count_syllables


def _check(cases):
    wrong = {w: (count_syllables(w), n) for w, n in cases.items() if count_syllables(w) != n}
    assert not wrong, f"word: (got, expected) {wrong}"


def test_common_words():
    _check({
        "the": 1, "cat": 1, "water": 2, "about": 2, "because": 2, "family": 3,
        "important": 3, "information": 4, "documentation": 5, "readability": 5,
        "everything": 3, "beautiful": 3, "different": 3, "people": 2,
    })


def test_silent_e():
    _check({
        "make": 1, "time": 1, "use": 1, "code": 1, "require": 3, "complete": 2,
        "statement": 2, "completely": 3, "careful": 2, "useless": 2,
        "baseline": 2, "something": 2, "pipeline": 2,
    })


def test_le_endings():
    _check({
        "table": 2, "little": 2, "simple": 2, "syllable": 3, "tables": 2,
        "settled": 2, "while": 1, "whole": 1, "style": 1,
    })


def test_ed_endings():
    _check({
        "walked": 1, "played": 1, "used": 1, "called": 1, "wanted": 2,
        "needed": 2, "tried": 1, "studied": 2, "hundred": 2, "deferred": 2,
    })


def test_es_endings():
    _check({"makes": 1, "lines": 1, "boxes": 2, "pages": 2, "matches": 2, "uses": 2})


def test_y_as_vowel_and_consonant():
    _check({
        "happy": 2, "fly": 1, "rhythm": 1, "type": 1, "yes": 1, "you": 1,
        "player": 2, "beyond": 2, "they": 1, "trying": 2, "studying": 3,
        "playing": 2, "every": 3,
    })


def test_vowel_pairs_that_split():
    _check({
        "idea": 3, "area": 3, "radio": 3, "being": 2, "going": 2, "seeing": 2,
        "create": 2, "video": 3, "science": 2, "actual": 3, "nation": 2,
        "special": 2, "quality": 3, "unique": 2, "basically": 3,
    })


def test_short_words_have_at_least_one_syllable():
    _check({"a": 1, "I": 1, "by": 1, "my": 1, "be": 1, "she": 1, "hmm": 1, "w": 1})


def test_contractions_possessives_and_hyphens():
    _check({
        "don't": 1, "isn't": 2, "didn't": 2, "it's": 1, "you're": 1,
        "Papa's": 2, "well-known": 2, "machine-readable": 5,
    })


def test_case_and_punctuation_are_ignored():
    assert count_syllables("Readability,") == count_syllables("readability") == 5


@pytest.mark.parametrize("token, expected", [("42", 1), ("2026", 1), ("", 0), ("--", 0), ("!", 0)])
def test_numbers_and_symbols(token, expected):
    # normalize() turns numbers and acronyms into "thing" before scoring; a stray
    # number still counts as one syllable, like that neutral token.
    assert count_syllables(token) == expected
