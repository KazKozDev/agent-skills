# Evals for complete-list-collection

Not part of the skill: an agent running it never reads this folder.

## What was run

`evals.json` holds six tasks in the skill-creator format. Each gives the listing's pages as text and asks for the
plan, items.jsonl and report.md in one reply, with no tools: the agent's decisions are checked, not its fetching.

| # | Case | What a correct run does |
|---|---|---|
| 1 | Duplicate in the middle of page 2 | Skips it, counts 1 duplicate, reports no problem |
| 2 | Sort changes on page 4 | Saves nothing from page 4, says what changed, resumes at page 4 |
| 3 | Page 5 fails twice | No third attempt, no padding, resumes at page 5 |
| 4 | N reached in the middle of page 2 | Resume point is page 2, so the rest of page 2 is not lost |
| 5 | Page 2 holds only repeats | Not taken for the end of the listing; goes on to page 3 |
| 6 | A shift on page 2, then page 3 fails | Reports both problems, not just one |

`trigger-queries.json` holds five requests: three that should load the skill and two near misses that should not.

## Results

Run with [Prompta](https://github.com/KazKozDev/prompta) on deepseek-v4.1-flash (Ollama Cloud), November 2026. Each
task ran twice with the skill and twice without it; a grader model checked every expectation.

| | With the skill | Without |
|---|---|---|
| Run 1 | 36/36 | 24/36 |
| Run 2 | 36/36 | 26/36 |

Without the skill the model missed the resume point in five of the six tasks: mostly it gave none, or a page without
the last ID; in case 4 it pointed to page 3, which loses the rest of page 2. It also left fields out of items.jsonl
(cases 1, 3, 4) and left report fields out in cases 1 and 4.

Routing: 3 of 3 requests loaded the skill and 2 of 2 near misses did not, each tried 3 times among 15 other skills.

## Not yet tested

- Real pages: these tasks describe the pages instead of serving them.
- A live harness, planned and not built: a mock listing on localhost (10 items per page, 50 items) that serves each
  case above, and a run that compares the files each agent writes.
- Other models.
