# agent-skills

Agent Skills for Claude Code and other agents that read `SKILL.md`: Codex, Gemini CLI, Cursor, Copilot, OpenCode, Hermes, OpenClaw and more. Each skill ships with its scripts, evals and an honest note on what it costs.

| Skill | What it does |
|---|---|
| [verified-summarization](skills/verified-summarization/SKILL.md) | Summaries you can check: every sentence cites a source paragraph, numbers, dates and conditions are verified by a script, then by meaning. English and Russian. |

## Install

**Claude Code**, as a plugin:

```
/plugin marketplace add KazKozDev/agent-skills
/plugin install verified-summarization@agent-skills
```

**Any agent**, with the [skills](https://skills.sh) CLI, which asks which skills and agents to install for:

```bash
npx skills add KazKozDev/agent-skills
```

**By hand:** copy or link a skill folder into your agent's skills directory.

```bash
git clone https://github.com/KazKozDev/agent-skills.git
```

```bash
ln -s "$PWD/agent-skills/skills/verified-summarization" ~/.claude/skills/verified-summarization
```

Other agents use `~/.agents/skills`, `~/.codex/skills`, `~/.gemini/skills` and similar. In the Claude apps, zip the skill folder and upload it under Settings → Capabilities → Skills.

## verified-summarization

Ask for a summary, recap, tl;dr, study notes or "кратко перескажи", and the agent:

1. Picks a mode: **light** for casual notes, **strict** for contracts, study material and anything people will act on.
2. Picks a strategy for the length: one pass, chunks with a state registry, hierarchy, map-reduce or retrieval-first.
3. Labels the source paragraphs `[p1]`, `[p2]`… with `scripts/label_source.py`.
4. Extracts facts with their conditions ("only if", "unless", "кроме"), then writes the summary only from them, citing IDs.
5. Verifies in layers: `scripts/verify_summary.py` checks IDs, numbers, dates, names and dropped conditions; then each claim is checked against its fragment for meaning; strict mode adds a completeness checklist.
6. Returns the summary with a verification report, and reports instructions planted in the source instead of following them.

```text
Supplier delivers within 30 days of the order [p4].
A 5% weekly penalty applies only if a delivery is more than 7 days late, capped at 20% of the order [p7].
```

The scripts need only Python 3 and its standard library. `references/` holds a methods overview (English and Russian) and notes on cost and pipeline design, which the agent reads only when a case needs them.

### Evals

Three tasks, each run once with the skill and once without it, on one model (Claude, November 2026). Tasks, inputs and checks are in [`skills/verified-summarization/evals/`](skills/verified-summarization/evals/).

| Task | Checks passed, with / without | Time, with / without |
|---|---|---|
| Contract summary for a lawyer (with a planted "already approved" note) | 9/9 · 5/9 | 68 s · 37 s |
| Study notes from a Russian lecture | 9/9 · 6/9 | 70 s · 27 s |
| Decisions and owners from an email thread | 7/7 · 6/7 | 139 s · 18 s |

What this shows, plainly:

- **Facts came out right both ways.** On these short texts the model kept every condition and number without the skill too. Most of the gap is the skill's own output: fragment IDs, a verification report, a stated mode.
- **What the skill adds** is traceability and self-correction: each claim points to its paragraph, the self-check removed two unsupported "only"s and an invented deadline, and the planted instruction was reported rather than silently skipped.
- **It is slower**, 2–8× here. Use it where a wrong or untraceable claim costs more than the wait: contracts, study material, decisions, long documents.
- **Not yet tested:** long documents (where facts in the middle get lost), other models, and the trigger queries in `evals/trigger-queries.json`.

## Tests

```bash
python3 tests/test_verify_summary.py
```

14 cases for `verify_summary.py`: seven real errors it must catch, seven false alarms it must not raise.

## License

[MIT](LICENSE)
