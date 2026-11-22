"""Regression cases for verified-summarization's verify_summary.py: real problems it must catch,
false alarms it must not raise.

Usage: python3 tests/test_verify_summary.py [path/to/verify_summary.py]
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "skills/verified-summarization/scripts/verify_summary.py"

SOURCE = """[p1] Supply Agreement No. 2026-114 between Northwind Components Ltd. ("Supplier") and Halden Robotics GmbH ("Buyer").

[p2] Accuracy rose from 60% to 80% after fine-tuning.

[p3] Distillation works well only if the teacher is accurate on the target domain.

[p4] Второе правило: данных нужно не меньше 5 тысяч примеров на класс. Учитель при этом давал 86%.

[p5] Blockers: the payment crash on Android 14 and the missing Polish translations.

[p6] If a delivery is late by more than 7 days, Supplier pays 5% per full week. The cap is 20%.

[p7] The decision was made on 12 November 2026 by Dana Ortiz."""

CASES = [
    # (name, summary, expected error types (exact set), warning types that must appear, warning types that must NOT appear)
    ("change misread caught", "Accuracy rose by 80% [p2].", set(), {"possible_change_misread"}, set()),
    ("dropped condition caught", "Distillation works well [p3].", set(), {"possible_dropped_condition"}, set()),
    ("missing id caught", "Delivery within 30 days [p9].", {"missing_id", "number_not_in_source"}, set(), set()),
    ("invented number caught", "The penalty is 15% per week if late by more than 7 days [p6].", {"number_not_in_source"}, set(), set()),
    ("wrong date caught", "The decision was made on 14 November 2026 [p7].", {"date_not_in_cited"}, set(), set()),
    ("invented name caught", "The decision was made by Dana Ortiz and Kevin Brandt [p7].", set(), {"name_not_in_source"}, set()),
    ("no id caught", "Supplier must also deliver spare parts within a week.", set(), {"no_id"}, set()),
    ("abbreviations do not split", 'Agreement No. 2026-114 between Northwind Components Ltd. and Halden Robotics GmbH [p1].',
     set(), set(), {"no_id"}),
    ("ordinal supports digit", "Правило 2: нужно не меньше 5 тысяч примеров на класс [p4].", set(), set(), set()),
    ("word count is a warning", "Dana named three blockers: the payment crash, the translations and the release notes [p5].",
     set(), {"number_word_not_in_source"}, set()),
    ("'при этом' is not a condition", "Учитель давал 86% [p4].", set(), set(), {"possible_dropped_condition"}),
    ("condition kept in next sentence",
     "Supplier pays 5% per full week of delay [p6]. This applies only if a delivery is late by more than 7 days [p6]. The cap is 20% [p6].",
     set(), set(), {"possible_dropped_condition"}),
    ("negated misread is fine", "Accuracy rose from 60% to 80% [p2]. That is a rise from 60% to 80%, not by 80% [p2].",
     set(), set(), {"possible_change_misread"}),
    ("markdown table and labels",
     "## Decisions\n\n**Risk**\n\n| What | Owner | Src |\n|---|---|---|\n| Decision on 12 November 2026 | Dana Ortiz | [p7] |\n",
     set(), set(), {"name_not_in_source", "no_id"}),
]

failed = 0
with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp, "src.txt")
    src.write_text(SOURCE, encoding="utf-8")
    for name, summary, want_err, want_warn, no_warn in CASES:
        summ = Path(tmp, "sum.txt")
        summ.write_text(summary, encoding="utf-8")
        r = json.loads(subprocess.run([sys.executable, "-I", str(SCRIPT), str(src), str(summ)],
                                      capture_output=True, text=True).stdout)
        errs = {e["type"] for e in r["errors"]}
        warns = {w["type"] for w in r["warnings"]}
        ok = errs == want_err and want_warn <= warns and not (no_warn & warns)
        failed += not ok
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  errors={sorted(errs)} warnings={sorted(warns)}"))
print(f"{len(CASES) - failed}/{len(CASES)} passed")
sys.exit(1 if failed else 0)
