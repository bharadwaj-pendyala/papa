from papa.analyzers import ANALYZERS, AnalyzerContext
from papa.models import ADVERB, COMPLEX, PASSIVE
from papa.sentences import split_sentences


def _run(name, text):
    ctx = AnalyzerContext(clean=text, sentences=split_sentences(text))
    return ANALYZERS[name](ctx)


def test_passive_flags_be_plus_participle():
    findings = _run("passive", "The cake was eaten by the dog.")
    assert len(findings) == 1
    f = findings[0]
    assert f.category == PASSIVE
    assert text_of(f, "The cake was eaten by the dog.") == "was eaten"


def test_passive_allows_an_adverb_between():
    findings = _run("passive", "The bug was quickly fixed.")
    assert len(findings) == 1
    assert text_of(findings[0], "The bug was quickly fixed.") == "was quickly fixed"


def test_passive_ignores_active_voice():
    assert _run("passive", "The dog ate the cake.") == []


def test_adverbs_flag_ly_words():
    findings = _run("adverbs", "She quickly and quietly left.")
    words = {text_of(f, "She quickly and quietly left.") for f in findings}
    assert words == {"quickly", "quietly"}
    assert all(f.category == ADVERB for f in findings)


def test_adverbs_respect_exception_list():
    assert _run("adverbs", "Only the family reply early.") == []


def test_complex_phrase_flags_curated_phrases():
    text = "In order to win, utilize the tool."
    findings = _run("complex-phrase", text)
    spans = {text_of(f, text).lower() for f in findings}
    assert "in order to" in spans
    assert "utilize" in spans
    assert all(f.category == COMPLEX for f in findings)


def test_complex_phrase_message_has_suggestion():
    findings = _run("complex-phrase", "We met prior to the launch.")
    assert "consider 'before'" in findings[0].message


def test_readability_marks_hard_sentence():
    hard = (
        "The multifaceted implementation demonstrates considerable architectural "
        "sophistication notwithstanding numerous interdependent complications that "
        "consistently undermine maintainability throughout the organization."
    )
    findings = _run("readability", hard)
    assert len(findings) == 1
    assert findings[0].category in ("hard-sentence", "very-hard-sentence")


def test_readability_leaves_easy_sentence_alone():
    assert _run("readability", "The cat sat on the mat.") == []


def text_of(finding, source):
    return source[finding.start:finding.end]
