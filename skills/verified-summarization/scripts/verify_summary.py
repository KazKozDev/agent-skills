#!/usr/bin/env python3
"""Deterministic (Layer 1) checks of a summary against an ID-labeled source.

Source format: fragments starting with an ID, e.g. "[p14] text..." or "[d2:p7] text...".
Summary: sentences ending with one or more IDs, e.g. "Delivery within 30 days [p14]."

Checks (English and Russian):
  errors   - cited ID missing from source
           - number/percentage in a sentence not found in its cited fragments
           - date in a sentence not found in its cited fragments
  warnings - sentence without any ID
           - number found only in other fragments (wrong citation?)
           - spelled-out number ("two", "три") not in the source (often a count; check it)
           - capitalized name not found in source
           - a condition marker (if/only/unless/если/только/кроме...) in a cited fragment that no
             sentence citing that fragment carries -> possible dropped condition
           - "from A% to B%" in source vs "by B%" in summary -> possible change misread

Markdown is accepted: headings, label lines and table header rows are skipped, list markers
are ignored, and each table row is checked as one sentence. Ordinals match digits
("Второе правило" supports "Правило 2"); dots after abbreviations such as "Ltd." do not end a sentence.

Exit code 0 if no errors, 1 if the summary has errors, 2 if the input files cannot be used
(missing, unreadable, not UTF-8, or a source without fragment IDs). Output: JSON to stdout.
This does NOT verify meaning; Layer 2 (semantic check) is still required.

Usage: python3 verify_summary.py labeled_source.txt summary.txt
"""
import json
import re
import sys

ID_RE = re.compile(r"\[((?:d\d+:)?p\d+)\]")
FRAG_RE = re.compile(r"^\s*\[((?:d\d+:)?p\d+)\]\s*", re.M)

WORD_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "ninety": 90, "hundred": 100,
    "ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3,
    "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
    "десять": 10, "пятнадцать": 15, "двадцать": 20, "тридцать": 30,
    "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "девяносто": 90, "сто": 100,
}
SCALE = {
    "тыс": 1e3, "тысяч": 1e3, "тысячи": 1e3, "thousand": 1e3, "k": 1e3,
    "млн": 1e6, "миллион": 1e6, "миллиона": 1e6, "миллионов": 1e6, "million": 1e6, "m": 1e6,
    "млрд": 1e9, "миллиард": 1e9, "миллиарда": 1e9, "миллиардов": 1e9, "billion": 1e9, "bn": 1e9,
}
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5, "июн": 6, "июл": 7,
    "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
}
# Ordinals count as numbers too: "Второе правило" in the source supports "Правило 2" in the summary.
ORDINAL_RE = re.compile(
    r"\b(?:(first)|(second)|(third)|(fourth)|(fifth)|(sixth)|(seventh)|(eighth)|(ninth)|(tenth))\b|"
    r"\b(?:(перв)|(втор)|(трет)|(четв[её]рт)|(пят)|(шест)|(седьм)|(восьм)|(девят)|(десят))"
    r"(?:ое|ой|ая|ый|ий|ье|ья|ьего|ьей|ьему|ьим|ьих|ью|ого|ому|ую|ым|ом|ых|ыми)\b",
    re.I,
)
# Bare "при" and "пока" are left out: "при этом", "при генерации" are ordinary phrases, not conditions.
COND = re.compile(
    r"\b(if|only|unless|except|provided|as long as|when|"
    r"если|только|лишь|кроме|за исключением|при условии|не более|не менее)\b",
    re.I,
)
# A dot after these does not end a sentence ("Northwind Components Ltd. (Supplier)", "т.е. ученик").
ABBREV_RE = re.compile(
    r"\b(?:No|Nr|Ltd|Inc|Co|Corp|LLC|Mr|Mrs|Ms|Dr|Prof|St|vs|etc|approx|cl|art|para|sec|fig|"
    r"e\.g|i\.e|cf|т\.е|т\.д|т\.п|т\.к|напр|см|ср|рис|стр|табл|гл|ст|ч|п|пп|г|гг|руб|долл|тыс|млн|млрд|"
    r"[A-ZА-ЯЁ])\.(?=\s)"
)
DOT = "․"  # stands in for a protected dot while sentences are split
NUM_RE = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:[   ]\d{3})+|\d+)(?:[.,](\d+))?\s*(%|процент\w*|percent)?"
    r"(?:\s*(тыс\w*|млн|млрд|миллион\w*|миллиард\w*|thousand|million|billion|bn|k|m)\b)?",
    re.I,
)
DATE_NUM_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_TXT_RE = re.compile(
    r"\b(\d{1,2})\s+([A-Za-zА-Яа-яё]{3,})\.?,?\s+(\d{4})\b|\b([A-Za-z]{3,})\.?\s+(\d{1,2}),?\s+(\d{4})\b"
)
FROM_TO = re.compile(r"(?:from|с)\s+(\d+(?:[.,]\d+)?)\s*%?\s+(?:to|до)\s+(\d+(?:[.,]\d+)?)\s*%", re.I)
BY_PCT = re.compile(r"(?:by|на)\s+(\d+(?:[.,]\d+)?)\s*%", re.I)


def parse_source(text):
    marks = list(FRAG_RE.finditer(text))
    frags = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        frags[m.group(1)] = text[m.end():end].strip()
    return frags


def prepare(text):
    """Markdown to plain sentences: headings, bold labels and table header/separator rows are dropped,
    list markers removed, each table row becomes one sentence and each line ends a sentence."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        s = line.strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not s or s.startswith("#") or re.fullmatch(r"\|?[\s:|-]*-[\s:|-]*\|?", s):
            continue
        if s.startswith("|") and re.fullmatch(r"\|?[\s:|-]*-[\s:|-]*\|?", nxt):
            continue  # table header row
        if re.fullmatch(r"\*\*[^*]+\*\*:?|[^\[\]]{1,40}:", s):
            continue  # a label line such as "**Risk**" or "Supplier obligations:"
        if "[" not in s and s[-1] not in ".!?…;" and len(s.split()) <= 5 and not re.search(r"\d", s):
            continue  # a plain heading such as "Governing law and disputes"
        if s.startswith("|"):
            s = " ; ".join(c.strip() for c in s.strip("|").split("|") if c.strip())
        s = re.sub(r"^(?:[-*•]|\d{1,2}[.)])\s+", "", s).replace("**", "").replace("`", "")
        if s and s[-1] not in ".!?…":
            s += "."
        out.append(s)
    return "\n".join(out)


def split_sentences(text):
    text = ABBREV_RE.sub(lambda m: m.group(0)[:-1] + DOT, " ".join(prepare(text).split()))
    parts = re.split(r"(?<=[.!?…])\s+(?=[^\[\s])|(?<=\])\s*[.;]?\s+(?=[A-ZА-ЯЁ\-•*\d])", text)
    return [p.strip().replace(DOT, ".") for p in parts if p.strip()]


def strip_ids(s):
    return ID_RE.sub("", s)


def numbers(s):
    s = strip_ids(s)
    s = DATE_NUM_RE.sub(" ", s)
    out = set()
    for m in NUM_RE.finditer(s):
        whole = re.sub(r"[   ]", "", m.group(1))
        frac = m.group(2)
        val = float(f"{whole}.{frac}") if frac else float(whole)
        if m.group(4):
            key = m.group(4).lower()
            mult = next((v for k, v in SCALE.items() if key.startswith(k)), 1)
            out.add(("abs", round(val * mult, 6)))
            continue
        if m.group(3):
            out.add(("pct", val))
        else:
            out.add(("num", val))
    # Spelled-out numbers and ordinals are kind "word": they match digits, but a summary's own word
    # number that is missing from the source is only a warning (it is often a count, e.g. "two blockers").
    for w in re.findall(r"[A-Za-zА-Яа-яё]+", s.lower()):
        if w in WORD_NUM:
            out.add(("word", float(WORD_NUM[w])))
    for m in ORDINAL_RE.finditer(s):
        out.add(("word", float(next(i for i, g in enumerate(m.groups()) if g) % 10 + 1)))
    return out


def dates(s):
    out = set()
    for m in DATE_NUM_RE.finditer(s):
        if m.group(1):
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            y, mo, d = int(m.group(4)), int(m.group(5)), int(m.group(6))
        y = y + 2000 if y < 100 else y
        out.add((y, mo, d))
    for m in DATE_TXT_RE.finditer(s):
        if m.group(1):
            d, mon, y = m.group(1), m.group(2), m.group(3)
        else:
            mon, d, y = m.group(4), m.group(5), m.group(6)
        mo = MONTHS.get(mon.lower()[:3])
        if mo:
            out.add((int(y), mo, int(d)))
    return out


def names(s):
    """Capitalized words that are not just the first word of the sentence or of a table cell."""
    found = set()
    for part in strip_ids(s).split(" ; "):
        words = re.findall(r"[A-Za-zА-Яа-яЁё][\w\-]+", part)
        found |= {w for w in words[1:] if w[0].isupper() and len(w) > 2}
    return found


def in_source(name, src_lower):
    n = name.lower()
    return n in src_lower or (len(n) > 5 and n[:5] in src_lower)


def num_match(item, pool):
    kind, val = item
    for k, v in pool:
        if abs(v - val) < 1e-9 and (k == kind or {k, kind} <= {"num", "pct", "word"} or "abs" in (k, kind)):
            return True
    return False


def read_text(path):
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


def main(src_path, sum_path):
    src = read_text(src_path)
    summ = read_text(sum_path)
    frags = parse_source(src)
    if not frags:
        print(f"error: {src_path} has no fragment IDs like [p1] at line starts; "
              "label it first: python3 scripts/label_source.py <source> > labeled.txt", file=sys.stderr)
        sys.exit(2)
    if not summ.strip():
        print(f"error: {sum_path} is empty", file=sys.stderr)
        sys.exit(2)
    src_lower = src.lower()
    frag_nums = {k: numbers(v) for k, v in frags.items()}
    errors, warnings = [], []
    sentences = split_sentences(summ)
    checked = 0
    # Condition markers per cited fragment: which ones some citing sentence kept, and the sentences.
    cond_kept, cond_citing = {}, {}
    for s in sentences:
        ids = ID_RE.findall(s)
        body = strip_ids(s).strip(" .;")
        if not body:
            continue
        checked += 1
        if not ids:
            if numbers(s) or len(body.split()) > 3:
                warnings.append({"type": "no_id", "sentence": s})
            continue
        missing = [i for i in ids if i not in frags]
        if missing:
            errors.append({"type": "missing_id", "ids": missing, "sentence": s})
        cited = " ".join(frags.get(i, "") for i in ids)
        cited_nums = set().union(*(frag_nums.get(i, set()) for i in ids)) if ids else set()
        for n in numbers(s):
            if not num_match(n, cited_nums):
                elsewhere = [k for k, v in frag_nums.items() if k not in ids and num_match(n, v)]
                if elsewhere:
                    warnings.append({"type": "number_in_other_fragment", "value": n[1],
                                     "found_in": elsewhere[:5], "sentence": s})
                elif n[0] == "word":
                    warnings.append({"type": "number_word_not_in_source", "value": n[1], "sentence": s})
                else:
                    errors.append({"type": "number_not_in_source", "value": n[1], "sentence": s})
        for d in dates(s) - dates(cited):
            errors.append({"type": "date_not_in_cited", "date": "%04d-%02d-%02d" % d, "sentence": s})
        for nm in names(s):
            if not in_source(nm, src_lower):
                warnings.append({"type": "name_not_in_source", "name": nm, "sentence": s})
        kept = {m.group(0).lower() for m in COND.finditer(body)}
        for i in ids:
            if i in frags:
                cond_kept.setdefault(i, set()).update(kept)
                cond_citing.setdefault(i, []).append(s)
        ft = FROM_TO.search(cited)
        by = BY_PCT.search(body)
        negated = by and re.search(r"(?:\bnot|\bне)\s*$", body[:by.start()], re.I)
        if ft and by and not negated and by.group(1) in (ft.group(1), ft.group(2)):
            warnings.append({"type": "possible_change_misread",
                             "source": ft.group(0), "summary": by.group(0), "sentence": s})
    # A condition counts as kept when any sentence citing that fragment carries its marker, since a
    # summary often states a rule in one sentence and its condition in the next.
    for i, citing in cond_citing.items():
        dropped = sorted({m.group(0).lower() for m in COND.finditer(frags[i])} - cond_kept[i])
        if dropped:
            warnings.append({"type": "possible_dropped_condition", "fragment": i,
                             "markers": dropped, "sentences": citing})
    result = {
        "pass": not errors,
        "sentences_checked": checked,
        "fragments_in_source": len(frags),
        "errors": errors,
        "warnings": warnings,
        "note": "Layer 1 only. Meaning is not verified; run the semantic check (Layer 2).",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
