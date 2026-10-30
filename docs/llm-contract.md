# Papa LLM contract

Papa's JSON is built to be handed to an LLM so the draft, measure, revise loop
can be automated outside Papa. This document describes the JSON shape Papa emits
and a prompt an agent can use to rewrite flagged spans.

## 1. Get the findings

```bash
papa post.md --max-grade 10 --report json > findings.json
```

## 2. The JSON shape

Schema `0.2` has one shape for every run: one file, many files, or none.

```jsonc
{
  "version": "0.2",
  "files": [
    {
      "file": "post.md",
      "score": {
        "ari": 11.2,
        "flesch_kincaid": 10.8,
        "gunning_fog": 12.1,
        "consensus": 11.3667,
        "reading_grade": "Grade 11, hard to read",
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
          "end": 1434,
          "line": 42,
          "column": 7,
          "end_line": 42,
          "end_column": 18,
          "category": "passive",
          "color": "green",
          "severity": "warn",
          "message": "Passive voice: 'is measured'",
          "analyzer": "passive",
          "hint": "Name who does the action and make them the subject.",
          "excerpt": "is measured"
        }
      ]
    }
  ],
  "skipped": [{ "file": "snippets.md", "reason": "no prose found (only code or markup)" }],
  "errors": [{ "file": "missing.md", "message": "no such file or directory" }],
  "summary": {
    "files": 3, "analyzed": 1, "passed": 0, "failed": 1,
    "skipped": 1, "errors": 1, "max_grade": 10
  }
}
```

- `start` and `end` are code-point offsets into the **original** source file.
  `source[start:end]` is the exact flagged text.
- `line` and `column` are 1-based and count code points. They point at the
  same place as `start`, so an editor can jump there.
- `hint` tells the writer how to fix the finding.
- `excerpt` is the flagged text as prose: link text without URLs, no
  emphasis marks, whitespace collapsed. Use `start` and `end` to edit.
- `consensus` is the mean of ARI, Flesch-Kincaid and Gunning fog. The
  `--max-grade` gate compares this value. `reading_grade` is the rounded label.
- `verdict` is `fail` only when a gate is set and `consensus` is above it.
  `threshold` is `null` when no gate is set.
- Papa always writes this JSON with `--report json`, also when every input
  fails. Read `errors` and `skipped` before you trust `files`.

### Changes from 0.1

- The top level is an object with `files`, not a single file or a list.
- `score.consensus`, and `line`, `column`, `end_line`, `end_column`, `hint`
  and `excerpt` on findings, are new.
- `skipped`, `errors` and `summary` are new.

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
papa post.revised.md --max-grade 10 --report json > findings.next.json
```

Re run Papa on the revision and compare `consensus`, finding counts, and
`verdict`. Repeat until `verdict` is `pass` or the grade stops improving.
