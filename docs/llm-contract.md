# Papa LLM contract

Papa's JSON is built to be handed to an LLM so the draft, measure, revise loop
closes. This document is the stable contract: the JSON shape Papa emits and the
prompt an agent uses to rewrite flagged spans.

## 1. Get the findings

```bash
papa post.md --report json > findings.json
```

## 2. The JSON shape

```jsonc
{
  "version": "1",
  "score": {
    "ari": 11.2,
    "flesch_kincaid": 10.8,
    "gunning_fog": 12.1,
    "consensus_grade": 11.4,
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

- `start` and `end` are byte offsets into the **original** source file, so a span
  maps back to the exact text the writer sees.
- `consensus_grade` is the raw (unrounded) grade the `--max-grade` gate compares
  against. `reading_grade` is the human facing label only.
- `verdict` is `pass` or `fail`. `threshold` records the gate that produced it.

## 3. The rewrite prompt

Hand the model the source file plus `findings.json` with a prompt like this:

```
You are editing a document for readability. I will give you the full text and a
list of findings with byte offsets. For each finding, rewrite only the flagged
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

Re run Papa on the revision and compare `consensus_grade`. Repeat until
`verdict` is `pass` or the grade stops improving. The built in `--suggest` flag
runs this loop for you against a configured provider.
