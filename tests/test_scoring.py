import pytest

from papa.aggregate import build_score, merge_findings
from papa.models import (
    ADVERB,
    COLOR,
    HARD,
    PASSIVE,
    Finding,
)
from papa.scoring import (
    automated_readability_index,
    document_grades,
    flesch_kincaid_grade,
    gunning_fog,
    reading_grade,
    sentence_grade,
)

# 6 one-syllable words, 18 non-space characters, 1 sentence.
SHORT = "The cat sat on the mat."
# 8 words, 2 sentences, 61 non-space characters, 19 syllables
# (4+5+2+2+2 + 2+1+1), 2 complex words (complicated, documentation).
TWO = "Complicated documentation frustrates many people. Simple words help."


def test_ari_by_hand():
    assert automated_readability_index(SHORT) == pytest.approx(4.71 * 18 / 6 + 0.5 * 6 - 21.43)
    assert automated_readability_index(TWO) == pytest.approx(4.71 * 61 / 8 + 0.5 * 4 - 21.43)


def test_flesch_kincaid_by_hand():
    assert flesch_kincaid_grade(SHORT) == pytest.approx(0.39 * 6 + 11.8 * 1 - 15.59)
    assert flesch_kincaid_grade(TWO) == pytest.approx(0.39 * 4 + 11.8 * 19 / 8 - 15.59)


def test_gunning_fog_by_hand():
    assert gunning_fog(SHORT) == pytest.approx(0.4 * 6)
    assert gunning_fog(TWO) == pytest.approx(0.4 * (4 + 100 * 2 / 8))


def test_fog_skips_familiar_long_words():
    # "everybody" and "important" have 3+ syllables but are familiar words.
    assert gunning_fog("Everybody knows this is important work.") == pytest.approx(0.4 * 6)
    assert gunning_fog("Everybody knows this is significant work.") == pytest.approx(
        0.4 * (6 + 100 / 6)
    )


def test_fragments_of_two_words_are_not_sentences():
    # "Simple words help." counts; "Read this." is folded into the word total only.
    assert flesch_kincaid_grade("Simple words help. Read this.") == pytest.approx(
        0.39 * 5 + 11.8 * 6 / 5 - 15.59
    )


def test_empty_text_scores_zero():
    assert document_grades("") == (0.0, 0.0, 0.0, 0.0)
    assert sentence_grade("   ") == 0.0


def test_grades_are_deterministic_and_dependency_free():
    first = document_grades(TWO)
    assert document_grades(TWO) == first
    assert first[:3] == (
        automated_readability_index(TWO), flesch_kincaid_grade(TWO), gunning_fog(TWO)
    )


def test_reading_grade_labels():
    assert reading_grade(8)[0].endswith("easy to read")
    assert reading_grade(11)[0] == "Grade 11, hard to read"
    assert reading_grade(16)[0].endswith("very hard to read")


def test_reading_grade_rounds_for_gating():
    label, grade = reading_grade(10.6)
    assert grade == 11
    assert "Grade 11" in label


def test_document_consensus_is_mean_of_three_formulas():
    ari, fk, fog, consensus = document_grades(
        "The committee deliberated extensively over the contentious proposal."
    )
    assert consensus == (ari + fk + fog) / 3


def test_no_gate_passes_with_null_threshold():
    score = build_score([], 3, (8.0, 8.0, 8.0, 8.0), None)
    assert score.verdict == "pass"
    assert score.threshold is None


def test_gate_fails_when_harder_than_max():
    score = build_score([], 5, (12.0, 12.0, 12.0, 12.0), 10)
    assert score.verdict == "fail"
    assert score.threshold == {"max_grade": 10}


def test_gate_passes_when_within_max():
    score = build_score([], 5, (9.0, 9.0, 9.0, 9.0), 10)
    assert score.verdict == "pass"


def test_gate_uses_raw_consensus_not_rounded_grade():
    # 10.4 displays as "Grade 10" but is harder than 10 -> must fail
    harder = build_score([], 5, (10.4, 10.4, 10.4, 10.4), 10)
    assert harder.verdict == "fail"
    assert "Grade 10" in harder.reading_grade  # display still rounds down

    # exactly at the bar is not "harder than" -> passes
    at_bar = build_score([], 5, (10.0, 10.0, 10.0, 10.0), 10)
    assert at_bar.verdict == "pass"


def test_counts_come_from_findings():
    findings = [
        _f(0, 5, PASSIVE),
        _f(6, 9, ADVERB),
        _f(10, 14, ADVERB),
        _f(0, 30, HARD),
    ]
    score = build_score(findings, 2, (8, 8, 8, 8), None)
    assert score.passive == 1
    assert score.adverbs == 2
    assert score.hard_sentences == 1


def test_merge_keeps_sentence_layer_and_resolves_word_overlap():
    findings = [
        _f(0, 40, HARD),
        _f(4, 16, PASSIVE),
        _f(8, 12, ADVERB),  # nested inside the passive span
    ]
    cats = [f.category for f in merge_findings(findings)]
    assert HARD in cats
    assert PASSIVE in cats
    assert ADVERB not in cats  # dropped: lower priority than the passive it overlaps


def _f(start, end, category):
    return Finding(start, end, category, COLOR[category], "warn", "", category)
