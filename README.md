# agent-skills

A small collection of agent skills (`SKILL.md` folders) for Claude Code and any other agent that reads them, each shipped with its scripts and with evals run with and without it.

- [verified-summarization](skills/verified-summarization/SKILL.md) - summaries where every sentence cites a source paragraph, and numbers, dates and conditions are checked by a script, then by meaning. English and Russian.
- [complete-list-collection](skills/complete-list-collection/SKILL.md) - the first N items of a paginated listing, saved page by page into `items.jsonl`, with a `report.md` that says what went wrong and where to resume.

## install

Claude Code. Each skill is its own plugin:

```
/plugin marketplace add KazKozDev/agent-skills
/plugin install verified-summarization@agent-skills
/plugin install complete-list-collection@agent-skills
```

Any agent, with the [skills](https://skills.sh) CLI (it asks which skills and which agents):

```bash
npx skills add KazKozDev/agent-skills
```

By hand: clone and link a skill folder into your agent's skills directory.

```bash
git clone https://github.com/KazKozDev/agent-skills.git
```

```bash
ln -s "$PWD/agent-skills/skills/verified-summarization" ~/.claude/skills/verified-summarization
```

Other agents look in `~/.agents/skills`, `~/.codex/skills`, `~/.gemini/skills` and similar. In the Claude apps, zip the skill folder and upload it under Settings → Capabilities → Skills.

## verified-summarization

Ask for a summary, recap, tl;dr, study notes or "кратко перескажи". The agent picks a mode (light, or strict for contracts and anything people will act on), labels the source paragraphs `[p1]`, `[p2]`... with `scripts/label_source.py`, extracts facts with their conditions, writes the summary only from those facts, then runs `scripts/verify_summary.py` over it and checks each claim against its fragment.

```text
Supplier delivers within 30 days of the order [p4].
A 5% weekly penalty applies only if a delivery is more than 7 days late, capped at 20% of the order [p7].
```

The scripts need only Python 3. `references/` holds a methods overview (English and Russian) and notes on cost; the agent reads them only when a case needs them.

Evals: three tasks, one run each with and without the skill, on Claude (November 2026). Checks passed with / without:

- contract summary for a lawyer, with a planted "already approved" note: 9/9 vs 5/9
- study notes from a Russian lecture: 9/9 vs 6/9
- decisions and owners from an email thread: 7/7 vs 6/7

The facts came out right without the skill too on these short texts; most of the gap is the skill's own output (fragment IDs, a verification report). With the skill the self-check removed two unsupported "only"s and an invented deadline, and the planted note was reported instead of skipped. It is 2-8x slower (68 s vs 37 s, 70 s vs 27 s, 139 s vs 18 s). Details in [skills/verified-summarization/evals/](skills/verified-summarization/evals/).

## complete-list-collection

Ask for the first N jobs, products or search results from a listing. The agent states the URL, N, the sort order and the stable ID it will use, then takes each page in a fixed order: fetch (one retry), read the items, check the sort, sort out repeats, append to `items.jsonl`, decide whether to go on. It stops at N or at the first problem (`page-failed`, `ended-early`, `sort-changed`; `items-shifted` is recorded and the crawl goes on) and always writes `report.md`:

```text
- Requested N: 40
- Confirmed count: 30
- Duplicates removed: 0
- Problems detected: sort-changed on page 4 (Newest → Relevance)
- Resume point: page 4, after ID item-30
```

It fetches with `curl` (or WebFetch, or Python requests) and uses a browser only when the listing needs JavaScript.

Evals: six tasks that describe the pages as text, two runs each with and without the skill, on deepseek-v4.1-flash (November 2026). With the skill 36/36 both runs, without 24/36 and 26/36. Without it the model missed the resume point in five of six tasks: mostly it gave none, or a page without the last ID, and once, stopping at N in the middle of page 2, it pointed to page 3 and lost the rest of page 2. Details in [skills/complete-list-collection/evals/](skills/complete-list-collection/evals/).

## tests

```bash
python3 tests/check_repo.py
python3 tests/test_verify_summary.py
python3 tests/test_label_source.py
```

The first checks that every skill has a valid `SKILL.md`, evals, a plugin entry in `.claude-plugin/marketplace.json` and a link here (`OK: 2 skills, marketplace and README consistent`). The other two test the summarization scripts (`14/14 passed`, `13/13 passed`). All three run in CI on every push and pull request and need only Python 3.

## adding a skill

1. `skills/<name>/SKILL.md`, with its scripts and references next to it.
2. `skills/<name>/evals/`: `evals.json` and `trigger-queries.json` in the skill-creator format, and a `README.md` with what was run and the results.
3. A plugin entry with a `version` in `.claude-plugin/marketplace.json`, a line in the list at the top, a section here and a line in [CHANGELOG.md](CHANGELOG.md).
4. `python3 tests/check_repo.py` passes.

## todos

- verified-summarization: run the trigger queries, a second run of each task, other models, long documents.
- complete-list-collection: real pages, through a mock listing on localhost (planned, not built), and other models.

## license

MIT, see [LICENSE](LICENSE).
