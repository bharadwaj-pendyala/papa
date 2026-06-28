from papa.aggregate import build_score, merge_findings
from papa.models import (
    ADVERB,
    COLOR,
    HARD,
    PASSIVE,
    Finding,
)
from papa.scoring import document_grades, reading_grade


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
