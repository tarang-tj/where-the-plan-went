"""Render the memo from its template so every number comes from outputs/numbers.csv.

Usage: python -m wtpw.memo   -> docs/memo.md and outputs/memo.pdf
{{key}} in docs/memo-template.md is replaced by the key's `display` in numbers.csv; an unknown key
fails. The rendered memo is then audited: any number-like token (digits with optional $, commas,
decimals, %) that did not come from a key fails with its line. Allowed by hand: plain years
2018-2027, program designators (B-21, KC-46A), ordered-list markers ("1. "), digits inside a word or identifier (Q3, FY2025, 10-K) and
URLs. The PDF is printed by Chrome via Playwright from a small markdown to HTML converter.
"""
import csv
import html
import re
import sys
from pathlib import Path

TEMPLATE, MEMO = Path("docs/memo-template.md"), Path("docs/memo.md")
NUMBERS, PDF = Path("outputs/numbers.csv"), Path("outputs/memo.pdf")
KEY = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
MASK = "\ue000"  # stands in for substituted text during the audit; not a word character
URL = re.compile(r"https?://[^\s)>\]]+")
NUM = re.compile(r"(?<![\w.$,])\$?\d(?:[\d,]*\d)?(?:\.\d+)?%?(?!\d)(?!-[A-Za-z])")
YEAR = re.compile(r"20(1[89]|2[0-7])")
# Program and aircraft designators are names, not figures: B-21, KC-46A, T-7A, F-35, VC-25B.
DESIGNATOR = re.compile(r"\b[A-Z]{1,4}-\d+[A-Z]?\b")
LIST_MARK = re.compile(r"\s*(\d+)\.\s")


class MemoError(ValueError):
    pass


def load_numbers(path: Path = NUMBERS) -> dict[str, str]:
    with path.open(newline="") as f:
        return {r["key"]: r["display"] for r in csv.DictReader(f)}


def render(template: str, numbers: dict[str, str]) -> tuple[str, str]:
    """Return (rendered memo, audit copy with every substitution masked). Unknown key raises."""
    unknown = [(template.count("\n", 0, m.start()) + 1, m.group(1))
               for m in KEY.finditer(template) if m.group(1) not in numbers]
    if unknown:
        raise MemoError("unknown numbers.csv key(s): " + ", ".join(f"line {n}: {k}" for n, k in unknown))
    rendered = KEY.sub(lambda m: numbers[m.group(1)], template)
    return rendered, KEY.sub(MASK, template)


def hand_typed(masked: str) -> list[tuple[int, str, str]]:
    """Number-like tokens not produced by a key: (line number, token, line)."""
    bad = []
    for n, line in enumerate(masked.splitlines(), 1):
        scan = DESIGNATOR.sub(MASK, URL.sub(MASK, line))
        mark = LIST_MARK.match(scan)
        for m in NUM.finditer(scan):
            if YEAR.fullmatch(m.group()) or (mark and m.start() == mark.start(1)):
                continue
            bad.append((n, m.group(), line.replace(MASK, "{{}}")))
    return bad


def build_markdown(template: Path = TEMPLATE, out: Path = MEMO, numbers: Path = NUMBERS) -> str:
    rendered, masked = render(template.read_text(), load_numbers(numbers))
    bad = hand_typed(masked)
    if bad:
        raise MemoError("hand-typed numbers (use a {{key}} from numbers.csv):\n" +
                        "\n".join(f"  {template}:{n}: {tok!r} in: {line.strip()}" for n, tok, line in bad))
    out.write_text(rendered)
    return rendered


def _inline(text: str) -> str:
    s = html.escape(text, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)


def _table(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    body = [r for r in cells[1:] if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    head = "".join(f"<th>{_inline(c)}</th>" for c in cells[0])
    trs = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{trs}</tbody></table>"


def to_html(md: str) -> str:
    """Minimal markdown: headings, paragraphs, - and 1. lists, pipe tables, bold, italic, code, links."""
    out, para, block, kind = [], [], [], None

    def flush():
        nonlocal block, kind
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()
        if kind == "table":
            out.append(_table(block))
        elif kind:
            out.append(f"<{kind}>" + "".join(f"<li>{_inline(i)}</li>" for i in block) + f"</{kind}>")
        block, kind = [], None

    for line in re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL).splitlines():
        s = line.strip()
        h = re.match(r"(#{1,6})\s+(.*)", s)
        item = re.match(r"(?:[-*]|(\d+)\.)\s+(.*)", s)
        if not s or h:
            flush()
            if h:
                out.append(f"<h{len(h.group(1))}>{_inline(h.group(2))}</h{len(h.group(1))}>")
        elif s.startswith("|"):
            if kind != "table":
                flush()
            kind = "table"
            block.append(s)
        elif item:
            want = "ol" if item.group(1) else "ul"
            if kind != want:
                flush()
            kind = want
            block.append(item.group(2))
        elif kind in ("ul", "ol") and line.startswith((" ", "\t")):
            block[-1] += " " + s
        else:
            if kind:
                flush()
            para.append(s)
    flush()
    return "\n".join(out)


CSS = """body{font-family:Arial,Helvetica,sans-serif;font-size:10.5pt;line-height:1.35;color:#111;margin:0}
h1{font-size:16pt;margin:0 0 6pt}h2{font-size:12.5pt;margin:12pt 0 4pt}h3{font-size:11pt;margin:10pt 0 3pt}
p{margin:0 0 6pt}ul,ol{margin:0 0 6pt 18pt;padding:0}table{border-collapse:collapse;margin:4pt 0 8pt}
th,td{border:1px solid #bbb;padding:2pt 6pt;text-align:left}th{background:#eef1f4}a{color:inherit}"""


def write_pdf(md: str, pdf: Path = PDF) -> Path:
    from playwright.sync_api import sync_playwright

    doc = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Where the plan went</title>"
           f"<style>{CSS}</style></head><body>{to_html(md)}</body></html>")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        try:
            page = browser.new_page()
            page.set_content(doc)
            page.pdf(path=str(pdf), format="Letter",
                     margin={"top": "0.6in", "bottom": "0.6in", "left": "0.7in", "right": "0.7in"})
        finally:
            browser.close()
    return pdf


def main() -> None:
    before = MEMO.read_text() if MEMO.exists() else None
    try:
        md = build_markdown()
    except MemoError as e:
        sys.exit(f"memo: FAIL\n{e}")
    if md == before and PDF.exists():  # Chrome stamps a creation date; only rebuild when the text changed
        print(f"memo: {MEMO} unchanged; kept {PDF}")
        return
    print(f"memo: wrote {MEMO} and {write_pdf(md)}")


if __name__ == "__main__":
    main()
