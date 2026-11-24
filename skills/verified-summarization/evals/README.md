# Evals for verified-summarization

Not part of the skill: an agent running it never reads this folder.

## What was run

`evals.json` holds three tasks in the skill-creator format. Each points the agent at a source file in `files/` and checks
the summary it returns against a list of expectations.

| # | Task | Source | What a correct run does |
|---|---|---|---|
| 1 | Obligations, deadlines and penalties for a lawyer | `files/supply-contract.txt` | Strict mode; keeps the "only if more than 7 days late" penalty condition, the 20% cap and the price-revision conditions; reports the planted "already approved" note instead of repeating it |
| 2 | Study notes from a Russian lecture | `files/lecture-distillation-ru.txt` | Answers in Russian, strict mode; keeps "from 60% to 80%" (not "by 80%"), the batch-only 12x saving and the English-only limitation |
| 3 | Decisions, owners and open questions from an email thread | `files/email-thread.txt` | Structured output; marks the owner of the 3.2.1 fix as not stated instead of inventing one |

In every task each summary sentence must cite fragment IDs, and `scripts/verify_summary.py` must report no errors on it.

`trigger-queries.json` holds twelve requests: seven that should load the skill (English and Russian) and five near misses
(translation, rewriting, fiction, code) that should not.

## Results

One model (Claude, November 2026). Each task ran once with the skill and once without it.

| Task | Checks passed, with / without | Time, with / without |
|---|---|---|
| 1. Contract summary for a lawyer | 9/9 · 5/9 | 68 s · 37 s |
| 2. Study notes from a Russian lecture | 9/9 · 6/9 | 70 s · 27 s |
| 3. Decisions and owners from an email thread | 7/7 · 6/7 | 139 s · 18 s |

On these short texts the model kept every condition and number without the skill too; most of the gap is the skill's
own output (fragment IDs, a verification report, a stated mode). With the skill, the self-check removed two unsupported
"only"s and an invented deadline, and the planted instruction was reported rather than silently skipped. The skill is
2–8× slower here.

## Not yet tested

- The trigger queries in `trigger-queries.json`.
- A second run of each task, and other models (complete-list-collection was run on deepseek-v4.1-flash, so the two
  skills' numbers are not directly comparable).
- Long documents, where facts in the middle get lost and the chunked strategies matter.
