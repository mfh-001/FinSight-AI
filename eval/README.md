# Eval sets

Two sets of questions, all answers checked by hand against the filing.

| Set | Filings | Questions | Use |
|---|---|---|---|
| `dev/` | Apple 10-K FY2023, Nathan's Famous 10-K FY2025 | 49 | Used while building. The answer logic was tuned while looking at it, so its numbers are optimistic. |
| `heldout/` | Lindsay Corporation 10-K FY2025 | 32 | Written afterwards, on a different filing and industry. Run once. |

Run:

```bash
finsight --backend none eval --set eval/dev/questions.jsonl --docs samples
finsight --backend none eval                      # held-out set, the default
```

## Held-out protocol

1. The held-out questions were written from the filing text before the system was run on them.
2. The answer logic was frozen at git tag `heldout-freeze` before the first run. Nothing in `finsight/answer.py`, `finsight/retrieve.py` or `finsight/ingest.py` was changed afterwards.
3. The set was run once. The result is in `heldout/results/`. If you change the logic and re-run, report it as a new, tuned number.

## What is in the held-out set

- 24 text questions on tables and prose, and 4 questions that are not answered in the filing (including a near miss).
- 3 questions on the balance sheet page, which I replaced with a picture of itself (a simulated scan, no text layer).
  A text-only path cannot answer these. Reports show the score with and without them.
- The PDF is `heldout/docs/lindsay-10k-fy2025-sim-scan.pdf`. Page numbers refer to it.

## Scoring

- Exact match: the gold value appears as printed (commas ignored), or the gold text appears.
- Numeric tolerance: any number in the answer equals the gold value within 0.5%, in any unit ($1.4 billion for 1,435,554,352).
  Sign is ignored.
- Citation hit: a cited page is one of the pages that contains the answer.
- Not-in-doc correct: for questions with no answer, the system said it was not found.
