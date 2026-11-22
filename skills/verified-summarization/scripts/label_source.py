#!/usr/bin/env python3
"""Label a source text with fragment IDs without rewriting it.

Splits on blank lines (paragraphs). Very long paragraphs are split further
on sentence boundaries so each fragment stays checkable.

Usage:
  python3 label_source.py input.txt > labeled.txt
  python3 label_source.py a.txt b.txt c.txt > labeled.txt   # multi-doc: [d1:p1], [d2:p1], ...
  python3 label_source.py input.txt --max-chars 1200
"""
import argparse
import re
import sys

SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[A-ZА-ЯЁ0-9«\"(])")
# About 250 words: short enough that a cited fragment can be checked against one claim at a glance,
# long enough that ordinary paragraphs stay whole and keep their own ID.
DEFAULT_MAX_CHARS = 1500


def split_paragraph(p: str, max_chars: int):
    if len(p) <= max_chars:
        return [p]
    parts, cur = [], ""
    for s in SENT_SPLIT.split(p):
        if cur and len(cur) + len(s) + 1 > max_chars:
            parts.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        parts.append(cur)
    return parts


def label(text: str, prefix: str, max_chars: int):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, n = [], 0
    for p in paras:
        for frag in split_paragraph(" ".join(p.split()), max_chars):
            n += 1
            out.append(f"[{prefix}p{n}] {frag}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Label paragraphs of UTF-8 text files with fragment IDs ([p1] or [d1:p1]).")
    ap.add_argument("files", nargs="+", help="source text file(s); several files get [d1:p1], [d2:p1], ... IDs")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help=f"split paragraphs longer than this on sentence boundaries (default {DEFAULT_MAX_CHARS})")
    a = ap.parse_args()
    if a.max_chars < 1:
        ap.error("--max-chars must be a positive number")
    multi = len(a.files) > 1
    blocks = []
    for i, f in enumerate(a.files, 1):
        text = read_text(f)
        if not text.strip():
            print(f"warning: {f} is empty, no fragments from it", file=sys.stderr)
        blocks.extend(label(text, f"d{i}:" if multi else "", a.max_chars))
    if not blocks:
        print("error: no text to label in the given file(s)", file=sys.stderr)
        sys.exit(2)
    sys.stdout.write("\n\n".join(blocks) + "\n")


def read_text(path: str) -> str:
    """The file's text, or exit with a one-line message (code 2) the agent can act on."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
    except IsADirectoryError:
        print(f"error: {path} is a directory, not a text file", file=sys.stderr)
    except PermissionError:
        print(f"error: no permission to read {path}", file=sys.stderr)
    except UnicodeDecodeError:
        print(f"error: {path} is not UTF-8 text; convert it first (e.g. iconv -f cp1251 -t utf-8)", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
