---
name: readability
description: Grade and improve the readability of Markdown, MDX, or text with papa. Use when the user asks to make docs, a README, a blog post, or any prose easier to read, to hit a reading grade, to fix hard sentences, passive voice, or adverbs, or to check prose before a PR.
---

# Improve readability with papa

papa grades prose like the Hemingway editor. The grade is a US school grade. Under 10 is easy to read.

## Grade

Use the `grade_files` or `grade_text` tool from the papa MCP server. If the tools are not available, run the CLI:

```bash
uvx --from papa-lint papa <files> --report json --max-grade <grade>
```

Use the max grade from the user, then from `papa.toml`. If neither sets one, use 10.

## Rewrite loop

1. Grade the files with the max grade.
2. Fix the findings in this order: `very-hard-sentence`, `hard-sentence`, `passive`, `complex-phrase`, `adverb`. Each finding has a `line`, a `column`, and a `hint`.
3. Grade again.
4. Stop when every file passes. Also stop after 3 rounds, or when a round does not lower the grade. Tell the user which findings are left.

## Rules for the rewrite

- Keep the meaning, every fact, every number, and the author's voice.
- Do not change code blocks, commands, links, headings that other pages link to, or front matter.
- Split long sentences. Name who does the action. Use the plainer phrase that the hint gives.
- Do not delete content to lower the grade.
- An adverb or a passive verb is advice, not an error. Keep it when it is the clearest choice.

End with the grade before and after for each file.
