"""Readability scoring: a consensus grade, not one gameable number.

A single formula is noisy and easy to game, so the document grade is the mean of
ARI, Flesch-Kincaid, and Gunning fog (spec §2.5, §6). Per-sentence grades use
ARI + FK (spec §5 table). All scoring runs on normalized text.

The formulas live here, with Papa's own syllable counter, so scoring never
downloads anything and a grade never moves because a dependency released a new
version. Word, sentence and character counts follow textstat 0.7 conventions so
grades stay close to what earlier Papa releases reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import normalize
from .syllables import count_syllables

# Familiar words that Gunning fog does not count as complex despite three or
# more syllables: the long words in the Dale-Chall list of 3,000 familiar words,
# which textstat also excluded.
_FAMILIAR = frozenset("""
    accident admire adventure afternoon afterward afterwards alligator
    already america american animal another anybody anyhow anyone anything
    anyway anywhere apartment arithmetic attention automobile avenue awaken
    awfully bakery banana barefoot battleship beautiful beautify becoming
    beginning bicycle blackberry blueberry bookkeeper bracelet buffalo
    bumblebee buttercup butterfly buttermilk butterscotch buttonhole cabinet
    calendar campfire canary candlestick canyon capital carelessness
    carpenter carriage cashier caterpillar certainly champion chocolate
    cigarette citizen coconut coffeepot company conductor cowardly cranberry
    cushion customer dangerous december deposit desire diamond difference
    different direction discover dressmaker dying electric electricity
    elephant eleven elsewhere enemy engineer envelope eraser every everybody
    everyday everyone everything everywhere excited exciting eyebrow factory
    family faraway fashion favorite february finally firecracker fisherman
    flowery following forehead forgotten friendship furniture gasoline
    general gentleman gentlemen geography gingerbread godmother good-bye
    good-looking goodbye gooseberry government grandchildren granddaughter
    grandfather grandmother grapefruit grasshopper graveyard grocery
    gunpowder handkerchief handwriting happily happiness hickory history
    holiday honeybee honeymoon horseback horseshoe hospital housetop
    housewife housework however idea important impossible indian interested
    interesting ivory january jellyfish lawyer lemonade liberty library
    locomotive lonesome lying machinery magazine manager marriage medicine
    multiply neighborhood nevermore newspaper nineteen ninety nobody
    november october officer old-fashioned otherwise overalls overcoat
    overeat overhead overhear overnight overturn passenger peppermint piano
    pigeon pineapple pocketbook policeman possible potato potatoes powerful
    pussycat radio rapidly remember rosebud satisfactory saturday
    schoolmaster separate september settlement seventeen seventy several
    shoemaker slippery soldier somebody strawberry sunflower tablecloth
    tablespoon telephone terrible thanksgiving theater tobacco together
    tomato tomorrow tricycle umbrella understand underwear unfinished
    unfriendly unhappy uniform united unpleasant unwilling valentine
    valuable vegetable victory violet visitor watermelon waterproof whenever
    wonderful woodpecker yesterday
""".split())

_SENTENCE = re.compile(r"\b[^.!?]+[.!?]*")
_PUNCTUATION = re.compile(r"[^\w\s'-]")
_STRAY_APOSTROPHE = re.compile(r"'(?![tsd]|ve|ll|re)")
_WHITESPACE = re.compile(r"\s")
_LETTER = re.compile(r"[^\W_]")


@dataclass(frozen=True)
class _Counts:
    words: int
    sentences: int
    characters: int
    tokens: int
    syllables: int
    complex_words: int


def _words(text: str) -> list[str]:
    """Words with punctuation removed; contractions and hyphenated words stay whole."""
    text = _PUNCTUATION.sub("", _STRAY_APOSTROPHE.sub("", text))
    return [w for w in text.split() if _LETTER.search(w)]


def _sentence_count(text: str) -> int:
    """Count sentences, ignoring fragments of two words or fewer."""
    if not text:
        return 0
    sentences = _SENTENCE.findall(text)
    return max(1, sum(1 for s in sentences if len(_words(s)) > 2))


def _counts(text: str) -> _Counts:
    words = _words(text)
    syllables = [count_syllables(w) for w in words]
    return _Counts(
        words=len(words),
        sentences=_sentence_count(text),
        characters=len(_WHITESPACE.sub("", text)),
        tokens=len(text.split()),
        syllables=sum(syllables),
        complex_words=sum(
            1 for w, s in zip(words, syllables) if s >= 3 and w.lower() not in _FAMILIAR
        ),
    )


def automated_readability_index(text: str) -> float:
    """4.71 * characters per word + 0.5 * words per sentence - 21.43."""
    return _ari(_counts(text))


def flesch_kincaid_grade(text: str) -> float:
    """0.39 * words per sentence + 11.8 * syllables per word - 15.59."""
    return _fk(_counts(text))


def gunning_fog(text: str) -> float:
    """0.4 * (words per sentence + 100 * complex words / words)."""
    return _fog(_counts(text))


def _ari(c: _Counts) -> float:
    if not c.words:
        return 0.0
    return 4.71 * c.characters / c.tokens + 0.5 * c.words / c.sentences - 21.43


def _fk(c: _Counts) -> float:
    if not c.words:
        return 0.0
    return 0.39 * c.words / c.sentences + 11.8 * c.syllables / c.words - 15.59


def _fog(c: _Counts) -> float:
    if not c.words:
        return 0.0
    return 0.4 * (c.words / c.sentences + 100 * c.complex_words / c.words)


def _formula_grades(text: str) -> tuple[float, float, float]:
    c = _counts(text)
    return _ari(c), _fk(c), _fog(c)


def document_grades(clean_text: str) -> tuple[float, float, float, float]:
    """Return (ari, flesch_kincaid, gunning_fog, consensus) on normalized text."""
    ari, fk, fog = _formula_grades(normalize(clean_text))
    return ari, fk, fog, (ari + fk + fog) / 3


def sentence_grade(sentence: str) -> float:
    """Per-sentence consensus grade (ARI + FK), on normalized text."""
    ari, fk, _ = _formula_grades(normalize(sentence))
    return (ari + fk) / 2


def reading_grade(consensus: float) -> tuple[str, int]:
    """Return the display label and the integer grade used for gating."""
    grade = max(0, round(consensus))
    if grade < 10:
        label = "easy to read"
    elif grade < 14:
        label = "hard to read"
    else:
        label = "very hard to read"
    return f"Grade {grade}, {label}", grade
