# Papa LLM contract

Papa's JSON is built to be handed to an LLM so the draft, measure, revise loop
can be automated outside Papa. This document describes the JSON shape Papa emits
and a prompt an agent can use to rewrite flagged spans.

## 1. Get the findings

```bash
papa post.md --report json > findings.json
```

## 2. The JSON shape

```jsonc
{
  "version": "0.2",
  "file": "post.md",
  "score": {
    "ari": 11.2,
    "flesch_kincaid": 10.8,
    "gunning_fog": 12.1,
    "reading_grade": "Grade 11, hard to read",
    "grade": 11.4,
    "sentences": 142,
    "hard_sentences": 18,
    "very_hard_sentences": 4,
    "adverbs": 9,
    "passive": 6,
    "complex_phrases": 12,
    "verdict": "fail",
    "threshold": { "max_grade": 10 }
  },
  "findings": [
    {
      "start": 1423,
      "end": 1490,
      "category": "passive",
      "color": "green",
      "severity": "warn",
      "message": "Passive voice: 'is measured'",
      "analyzer": "passive"
    }
  ]
}
```

- `start` and `end` are offsets into the **original** source file, so a span maps
  back to the exact text the writer sees.
- `reading_grade` is the human-facing label. `grade` is the consensus grade to
  one decimal, the number the CLI compares against `--max-grade`. At the limit
  it is rounded in the direction that agrees with `verdict`.
- `verdict` is `pass`, `fail`, or `skip`. `skip` means the file has no prose to
  grade (empty, code only, or frontmatter only). It never fails `--max-grade`
  unless you pass `--fail-on-empty`. `threshold` records the gate that produced
  the verdict.
- Schema `0.2` added `grade` and the `skip` verdict to `0.1`. Nothing was
  renamed or removed.

## 3. The rewrite prompt

Hand the model the source file plus `findings.json` with a prompt like this:

```
You are editing a document for readability. I will give you the full text and a
list of findings with source offsets. For each finding, rewrite only the flagged
span so the issue is resolved, while preserving the author's meaning, voice, and
any code, links, or formatting.

Rules:
- Do not change text outside the flagged spans unless a fix requires a small
  local edit for grammar.
- Passive voice: prefer the active voice.
- Adverbs: cut the adverb or replace the weak verb plus adverb with one strong verb.
- Complex phrase: use the simpler suggested wording.
- Hard or very hard sentence: split it or shorten it. Do not drop information.

Return the full revised document, nothing else.

SOURCE:
<paste post.md>

FINDINGS:
<paste findings.json>
```

## 4. Close the loop

```bash
papa post.revised.md --report json > findings.next.json
```

Re run Papa on the revision and compare `reading_grade`, finding counts, and
`verdict`. Repeat until `verdict` is `pass` or `skip`, or the grade stops
improving.
