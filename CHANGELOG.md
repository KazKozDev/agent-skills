# Changelog

Versions are per plugin, as listed in `.claude-plugin/marketplace.json`.

## 2026-11-24

- **complete-list-collection 0.1.0**: first release. Collects the first N items of a paginated listing into
  `items.jsonl` page by page, with a `report.md` that names each problem and where to resume.
- Repository: CI on every push and pull request, structure checks for all skills, tests for `label_source.py`,
  an evals README for verified-summarization.

## 2026-11-22

- **verified-summarization 0.1.0**: first release. Summaries that cite source fragment IDs, checked by
  `verify_summary.py` and then by meaning; English and Russian.
