from papa.ingest import ingest


def test_txt_is_identity():
    text = "Plain text, no markdown here."
    clean, omap = ingest(text, "txt")
    assert clean == text
    assert omap.to_original(5) == 5


def test_frontmatter_stripped():
    text = "---\ntitle: Hi\ndate: 2026-01-01\n---\nBody starts here."
    clean, _ = ingest(text, "md")
    assert "title" not in clean
    assert clean.strip() == "Body starts here."


def test_fenced_code_stripped():
    text = "Before code.\n\n```python\nsecret = 1\n```\n\nAfter code."
    clean, _ = ingest(text, "md")
    assert "secret" not in clean
    assert "Before code." in clean and "After code." in clean


def test_tilde_fence_stripped():
    text = "Intro.\n\n~~~\nhidden = True\n~~~\n\nOutro."
    clean, _ = ingest(text, "md")
    assert "hidden" not in clean
    assert "Intro." in clean and "Outro." in clean


def test_inline_code_stripped():
    text = "Run `rm -rf /` with care."
    clean, _ = ingest(text, "md")
    assert "rm -rf" not in clean
    assert "Run" in clean and "care" in clean


def test_svg_stripped():
    text = "Diagram: <svg><path d='M0 0'/></svg> done."
    clean, _ = ingest(text, "md")
    assert "<svg" not in clean and "path" not in clean
    assert "Diagram" in clean and "done" in clean


def test_offset_maps_to_original_not_stripped():
    text = "```\nx = 1\n```\nThe word anchor lives here."
    clean, omap = ingest(text, "md")
    idx = clean.index("anchor")
    orig = omap.to_original(idx)
    assert text[orig:orig + len("anchor")] == "anchor"
    # the strip really removed bytes, so clean and original offsets differ
    assert orig != idx


def test_offset_end_does_not_jump_a_strip():
    text = "Alpha `code` beta."
    clean, omap = ingest(text, "md")
    pos = clean.index("beta")
    start = omap.to_original(pos)
    end = omap.to_original_end(pos + len("beta"))
    assert text[start:end] == "beta"


def test_inline_backticks_inside_fence_are_not_double_counted():
    text = "Text.\n\n```\na = `not inline`\n```\n\nMore text."
    clean, _ = ingest(text, "md")
    assert "not inline" not in clean
    assert "More text." in clean


from pathlib import Path

from papa import analyze
from papa.ingest import block_breaks
from papa.sentences import split_sentences

CORPORA = Path(__file__).parent / "ux" / "corpora"
README = (CORPORA / "readme-style.md").read_text(encoding="utf-8")
MDX = (CORPORA / "mdx-site" / "page.mdx").read_text(encoding="utf-8")


def _sentences(source, fmt):
    clean, omap = ingest(source, fmt)
    return [" ".join(text.split()) for _, _, text in split_sentences(clean, breaks=block_breaks(source, fmt, omap))]


def test_markdown_markup_is_not_prose():
    clean = analyze(README, fmt="md").clean
    for markup in ("img.shields", "](", "**", "<div", "|", "https://", "#"):
        assert markup not in clean, markup


def test_markdown_keeps_link_and_cell_text():
    clean = analyze(README, fmt="md").clean
    for text in ("Quickstart", "labeled", "Skip the slow checks.", "Fast widgets for your build."):
        assert text in clean, text


def test_list_items_headings_and_cells_are_separate_sentences():
    sentences = _sentences(README, "md")
    assert "CLI command:" in sentences
    assert "Python package:" in sentences
    assert "Status" in sentences
    assert "Skip the slow checks." in sentences


def test_wrapped_paragraph_lines_stay_one_sentence():
    sentences = _sentences(README, "md")
    assert "Good first issues are labeled for new people." in sentences


def test_mdx_imports_exports_and_tags_are_not_prose():
    clean = analyze(MDX, fmt="mdx").clean
    for markup in ("import", "export", "<Tab", "items=", "<Image", "screenshot.png"):
        assert markup not in clean, markup
    assert "Call the function from your code." in clean


def test_findings_in_markdown_still_point_at_the_source():
    result = analyze(README, fmt="md")
    passive = [f for f in result.findings if f.category == "passive"]
    assert any(README[f.start:f.end].startswith("are") for f in passive)
    assert all(0 <= f.start < f.end <= len(README) for f in result.findings)


def test_passive_message_reads_as_prose_across_a_link():
    result = analyze(README, fmt="md")
    assert any(f.message == "Passive voice: 'are labeled'" for f in result.findings)


def test_split_sentences_honours_block_breaks():
    text = "one two three four five six seven"
    assert [s for _, _, s in split_sentences(text, breaks={8})] == ["one two", "three four five six seven"]


def test_jsx_tag_with_an_element_inside_an_attribute_is_not_prose():
    mdx = '<Button\n  href={HOSTS.WWW}\n  endIcon={<Compass aria-hidden />}\n>\n  Explore the docs.\n</Button>\n'
    clean, _ = ingest(mdx, "mdx")
    assert " ".join(clean.split()) == "Explore the docs."


def test_jsx_attribute_with_two_levels_of_braces_is_not_prose():
    mdx = '<Card\n  icon={\n    <img src="/x.svg" width={20} />\n  }\n  title="LangChain"\n/>\nTrace your chains.\n'
    clean, _ = ingest(mdx, "mdx")
    assert " ".join(clean.split()) == "Trace your chains."


def test_callout_markers_are_not_prose():
    md = ":::info\nThis guide shows how to run checks in CI.\n:::\n"
    clean, _ = ingest(md, "mdx")
    assert " ".join(clean.split()) == "This guide shows how to run checks in CI."


def test_findings_carry_a_prose_excerpt_even_inside_a_link():
    md = "Read [part one](/blog/one) of the multifaceted interdependent architectural sophistication series today.\n"
    hard = [f for f in analyze(md).findings if "sentence" in f.category]
    assert hard and hard[0].excerpt.startswith("Read part one of the")
