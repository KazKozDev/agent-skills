"""Structure checks for the whole collection: every skill folder has a valid SKILL.md, evals in the
skill-creator format and a plugin entry in .claude-plugin/marketplace.json, and every plugin entry
points at a real skill.

Usage: python3 tests/check_repo.py
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
problems = []


def problem(msg):
    problems.append(msg)
    print("FAIL " + msg)


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problem(f"{path.relative_to(REPO)} is missing")
    except json.JSONDecodeError as e:
        problem(f"{path.relative_to(REPO)} is not valid JSON: {e}")
    return None


skill_dirs = sorted(p for p in (REPO / "skills").iterdir() if p.is_dir())

for d in skill_dirs:
    name = d.name
    rel = d.relative_to(REPO)
    fm = frontmatter(d / "SKILL.md") if (d / "SKILL.md").exists() else None
    if fm is None:
        problem(f"{rel}/SKILL.md is missing or has no frontmatter")
        continue
    if fm.get("name") != name:
        problem(f"{rel}/SKILL.md: name '{fm.get('name')}' does not match the folder '{name}'")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        problem(f"{rel}: skill name must be kebab-case, at most 64 characters")
    desc = fm.get("description", "")
    if not desc:
        problem(f"{rel}/SKILL.md: description is empty")
    elif len(desc) > 1024:
        problem(f"{rel}/SKILL.md: description is {len(desc)} characters, the limit is 1024")
    elif "<" in desc or ">" in desc:
        problem(f"{rel}/SKILL.md: description must not contain angle brackets")

    evals = load_json(d / "evals" / "evals.json")
    if evals is not None:
        if evals.get("skill_name") != name:
            problem(f"{rel}/evals/evals.json: skill_name '{evals.get('skill_name')}' does not match '{name}'")
        for e in evals.get("evals", []):
            for f in e.get("files", []):
                if not (d / f).exists():
                    problem(f"{rel}/evals/evals.json: eval {e.get('id')} refers to missing file {f}")
            if not e.get("expectations"):
                problem(f"{rel}/evals/evals.json: eval {e.get('id')} has no expectations")
    triggers = load_json(d / "evals" / "trigger-queries.json")
    if triggers is not None:
        kinds = {q.get("should_trigger") for q in triggers}
        if kinds != {True, False}:
            problem(f"{rel}/evals/trigger-queries.json needs both should_trigger true and false queries")
    if not (d / "evals" / "README.md").exists():
        problem(f"{rel}/evals/README.md is missing (what was run and the results)")

market = load_json(REPO / ".claude-plugin" / "marketplace.json")
if market is not None:
    plugins = market.get("plugins", [])
    names = [p.get("name") for p in plugins]
    if len(names) != len(set(names)):
        problem("marketplace.json has duplicate plugin names")
    covered = set()
    for p in plugins:
        for k in ("name", "description", "version", "source", "skills"):
            if not p.get(k):
                problem(f"marketplace.json: plugin '{p.get('name')}' has no {k}")
        if p.get("version") and not re.fullmatch(r"\d+\.\d+\.\d+", p["version"]):
            problem(f"marketplace.json: plugin '{p.get('name')}' version '{p['version']}' is not semver")
        for s in p.get("skills", []):
            path = (REPO / p.get("source", "./") / s).resolve()
            if not (path / "SKILL.md").exists():
                problem(f"marketplace.json: plugin '{p.get('name')}' points at {s}, which has no SKILL.md")
            covered.add(path.name)
    for d in skill_dirs:
        if d.name not in covered:
            problem(f"skills/{d.name} has no plugin entry in marketplace.json")

readme = (REPO / "README.md").read_text(encoding="utf-8")
for d in skill_dirs:
    if f"skills/{d.name}/SKILL.md" not in readme:
        problem(f"README.md has no table row linking skills/{d.name}/SKILL.md")

if problems:
    print(f"{len(problems)} problem(s)")
    sys.exit(1)
print(f"OK: {len(skill_dirs)} skills, marketplace and README consistent")
