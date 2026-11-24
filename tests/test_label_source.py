"""Regression cases for verified-summarization's label_source.py: fragment IDs, splitting, and the
one-line errors (exit code 2) an agent acts on.

Usage: python3 tests/test_label_source.py [path/to/label_source.py]
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "skills/verified-summarization/scripts/label_source.py"


def run(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def ids(out):
    return re.findall(r"^\[([^\]]+)\]", out, flags=re.M)


failed = 0
total = 0


def check(name, ok, detail=""):
    global failed, total
    total += 1
    failed += not ok
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))


with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)

    one = t / "one.txt"
    one.write_text("First paragraph,\nwrapped   over lines.\n\n\n\nSecond paragraph.\n\nТретий абзац.\n", encoding="utf-8")
    r = run(one)
    check("paragraphs get p1..p3", r.returncode == 0 and ids(r.stdout) == ["p1", "p2", "p3"], r.stdout + r.stderr)
    check("whitespace collapsed, words kept", "[p1] First paragraph, wrapped over lines." in r.stdout, r.stdout)
    check("cyrillic kept as is", "[p3] Третий абзац." in r.stdout, r.stdout)

    long = t / "long.txt"
    sentences = [f"Sentence number {i} says something about the contract." for i in range(1, 21)]
    long.write_text(" ".join(sentences), encoding="utf-8")
    r = run(long, "--max-chars", "200")
    frags = [line.split("] ", 1)[1].strip() for line in r.stdout.split("\n\n") if line.strip()]
    check("long paragraph split into several fragments", r.returncode == 0 and len(frags) > 1, r.stdout + r.stderr)
    check("split only on sentence boundaries", all(f.endswith(".") for f in frags), str(frags))
    check("no fragment over the limit", all(len(f) <= 200 for f in frags), str([len(f) for f in frags]))
    check("splitting loses no text", " ".join(frags) == " ".join(sentences))

    two = t / "two.txt"
    two.write_text("Other document.\n\nIts second paragraph.", encoding="utf-8")
    r = run(one, two)
    check("multi-doc prefixes", ids(r.stdout) == ["d1:p1", "d1:p2", "d1:p3", "d2:p1", "d2:p2"], r.stdout)

    empty = t / "empty.txt"
    empty.write_text("  \n\n", encoding="utf-8")
    r = run(empty)
    check("empty file exits 2", r.returncode == 2 and "no text" in r.stderr, r.stderr)
    r = run(empty, two)
    check("empty file among others warns, still labels", r.returncode == 0 and "warning" in r.stderr
          and ids(r.stdout) == ["d2:p1", "d2:p2"], r.stdout + r.stderr)

    r = run(t / "missing.txt")
    check("missing file exits 2", r.returncode == 2 and "not found" in r.stderr, r.stderr)

    cp = t / "cp1251.txt"
    cp.write_bytes("Договор поставки".encode("cp1251"))
    r = run(cp)
    check("non-UTF-8 exits 2 with a hint", r.returncode == 2 and "iconv" in r.stderr, r.stderr)

    r = run(one, "--max-chars", "0")
    check("bad --max-chars rejected", r.returncode != 0, r.stderr)

print(f"{total - failed}/{total} passed")
sys.exit(1 if failed else 0)
