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
