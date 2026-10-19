"""Offline English syllable counting for the readability formulas.

A rule-based counter plus a small exceptions table. It needs no corpus, no
download and no network, and it gives the same answer on every machine, so a
grade never moves because a dependency changed.

The rules count vowel groups, then correct for the common ways spelling and
sound disagree in English: silent final e, -le endings, -ed and -es endings,
y as a vowel, vowel pairs that span two syllables (idea, radio, being), and
compounds whose first part ends in a silent e (baseline, something). Counts
follow the CMU Pronouncing Dictionary, which most readability tools use.
"""

from __future__ import annotations

import re

# Words the rules get wrong that show up often in prose and docs.
_EXCEPTIONS = {
    "anyone": 3,
    "area": 3,
    "argue": 2,
    "business": 2,
    "busy": 2,
    "cafe": 2,
    "cement": 2,
    "chocolate": 2,
    "colonel": 2,
    "different": 3,
    "dr": 2,
    "element": 3,
    "evening": 2,
    "flour": 2,
    "giant": 2,
    "hour": 2,
    "idea": 3,
    "interest": 2,
    "interested": 3,
    "interesting": 3,
    "lineage": 3,
    "linear": 3,
    "maybe": 2,
    "mr": 2,
    "mrs": 2,
    "naive": 2,
    "our": 2,
    "people": 2,
    "poem": 2,
    "poet": 2,
    "priest": 1,
    "reality": 4,
    "recipe": 3,
    "museum": 3,
    "reuse": 2,
    "reused": 2,
    "reuses": 3,
    "sour": 2,
    "whereas": 2,
    "wednesday": 2,
    "yes": 1,
}

# First halves of compounds, with their syllables: the e in "baseline" is silent.
_COMPOUND_HEADS = {
    "bare": 1, "base": 1, "brace": 1, "care": 1, "code": 1, "else": 1,
    "every": 2, "eye": 1, "file": 1, "frame": 1, "game": 1, "grave": 1,
    "home": 1, "horse": 1, "house": 1, "ice": 1, "life": 1, "like": 1,
    "line": 1, "lone": 1, "make": 1, "name": 1, "nine": 1, "note": 1,
    "pipe": 1, "rose": 1, "safe": 1, "side": 1, "some": 1, "space": 1,
    "store": 1, "there": 1, "time": 1, "type": 1, "where": 1, "white": 1,
}

# Second halves that start with a vowel but still join a compound: time-out, home-owner.
_VOWEL_TAILS = frozenset((
    "in", "ins", "off", "offs", "on", "one", "ones", "out", "outs",
    "over", "overs", "owner", "owners", "up", "ups",
))

# Spellings that add a syllable the vowel-group count misses.
_SPLITS = [re.compile(p) for p in (
    r"[^ctgsx]i[au]",            # media, medium, trivial (not special, asian)
    r"[^ctgsxhnlv]io|(?<!l)lio|vio(?!r)",  # radio, lion (not nation, million, behavior)
    r"[ct]iat(?!iv)",            # appreciate, negotiation
    r"[^qg]ua",                  # actual, usual (not quality, language)
    r"[^qg]uo",                  # continuous, fluorine
    r"[^qg]ue[nlt]",             # fluent, cruel, duet (not guess, queen)
    r"[^ct]ie[nt]",              # client, quiet (not ancient, patient)
    r"[^aeiou]ier",              # earlier, easier, happier
    r"[^aeiou]iest",             # happiest
    r"(?<!g)eo|^geo",            # video, geography (not pigeon)
    r"eity",                     # spontaneity
    r"creat|react|reag|theat|scien",  # create, reaction, science
    r"[aeiou]ing",               # being, going, doing, seeing
    r"[^aeiou]yi",               # trying, studying
    r"ism$",                     # tourism (the m is syllabic)
)]

# Spellings that read as one syllable fewer than their vowel groups.
_MERGES = [re.compile(p) for p in (
    r"ically$",                  # basically: "-ic-ly"
    r"rriage",                   # marriage, carriage
    r"friend",                   # friend, friendship
    r"..[qg]ues?$",              # unique, league, techniques
)]

_SUFFIXES = ("ments", "ment", "ness", "fully", "ful", "less", "ly")
_NON_LETTERS = re.compile(r"[^a-z]")
_DIGIT = re.compile(r"[0-9]")
_NOT_CONTRACTION = re.compile(r"[^aeiouy]n't$")  # isn't, didn't (not don't, can't)


def count_syllables(word: str) -> int:
    """Return the number of syllables in ``word``.

    Hyphenated words count each part ("well-known" is 2). A bare number counts
    as one syllable, like the neutral token in normalize, and a token with no
    letters or digits counts as none.
    """
    word = word.lower()
    if "-" in word:
        return sum(count_syllables(part) for part in word.split("-"))
    extra = 1 if _NOT_CONTRACTION.search(word) else 0
    letters = _NON_LETTERS.sub("", word)
    if not letters:
        return 1 if _DIGIT.search(word) else 0
    return extra + _count(letters)


def _count(word: str) -> int:
    if word in _EXCEPTIONS:
        return _EXCEPTIONS[word]
    if word.endswith("s") and word[:-1] in _EXCEPTIONS:
        return _EXCEPTIONS[word[:-1]]
    if word.endswith("es") and word[:-2] in _EXCEPTIONS and _sibilant(word[:-2]):
        return _EXCEPTIONS[word[:-2]] + 1  # businesses, buses
    for head, syllables in _COMPOUND_HEADS.items():
        rest = word[len(head):]
        if not word.startswith(head) or not _vowel_groups(rest):
            continue
        if rest in _VOWEL_TAILS or not _is_vowel(rest, 0):
            return syllables + _count(rest)
    for suffix in _SUFFIXES:
        stem = word[: -len(suffix)]
        if word.endswith(suffix) and _silent_e(stem) and _vowel_groups(stem) > 1:
            return _count(stem) + _vowel_groups(suffix)
    count = _vowel_groups(word) + _matches(_SPLITS, word) - _matches(_MERGES, word)
    if _vowel_groups(word) > 1 and _silent_ending(word):
        count -= 1
    return max(1, count)


def _sibilant(word: str) -> bool:
    return word[-1:] in ("s", "x", "z") or word[-2:] in ("ch", "sh")


def _is_vowel(word: str, i: int) -> bool:
    """y is a consonant at the start of a word and after a vowel (yes, player)."""
    if word[i] == "y":
        return i > 0 and word[i - 1] not in "aeiou"
    return word[i] in "aeiou"


def _vowel_groups(word: str) -> int:
    groups = 0
    previous = False
    for i in range(len(word)):
        vowel = _is_vowel(word, i)
        if vowel and not previous:
            groups += 1
        previous = vowel
    return groups


def _matches(patterns: list[re.Pattern[str]], word: str) -> int:
    return sum(len(pattern.findall(word)) for pattern in patterns)


def _silent_e(word: str) -> bool:
    """True when ``word`` ends in a silent e: make, time, use."""
    return len(word) >= 3 and word.endswith("e") and _silent_before(word, len(word) - 2)


def _silent_ending(word: str) -> bool:
    """Silent final e, or an -es / -ed ending that adds no syllable (makes, played)."""
    if _silent_e(word):
        return True
    if len(word) < 4:
        return False
    i = len(word) - 3
    if word.endswith("es"):
        sibilant = word[i] in "sxzcg" or word[i - 1:i + 1] in ("ch", "sh")
        return _silent_before(word, i) and not sibilant  # makes, but boxes, pages
    if word.endswith("ed"):
        return _silent_before(word, i) and word[i] not in "td"
    return False


def _silent_before(word: str, i: int) -> bool:
    """True when the e after ``word[i]`` is silent: a consonant, but not -ble, -cre or -ire."""
    if _is_vowel(word, i):
        return False
    if word[i] in "lr" and i > 0 and word[i - 1] in "bcdfgkptz":
        return False  # table, settled, acre, hundred
    if word[i] == "r" and i > 1 and word[i - 1] == "i" and word[i - 2] not in "aeo":
        return False  # fire, require, tired: CMU gives "-ire" two syllables
    return True
