"""Render the README's findings block from docs/readme-findings-template.md and numbers.csv.

  python -m wtpw.readme_block          rewrite the block between the README markers
  python -m wtpw.readme_block --check  exit 1 if the README block differs from a fresh render
Uses the memo's renderer, so an unknown key or a hand-typed number fails here too.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from wtpw.memo import MemoError, hand_typed, load_numbers, render

README = Path("README.md")
TEMPLATE = Path("docs/readme-findings-template.md")
BLOCK = re.compile(r"(<!-- findings:start[^>]*-->\n)(.*?)(\n<!-- findings:end -->)", re.DOTALL)


def rendered() -> str:
    text, masked = render(TEMPLATE.read_text().strip(), load_numbers())
    bad = hand_typed(masked)
    if bad:
        raise MemoError("hand-typed numbers in README template: " + ", ".join(f"line {n}: {t}" for n, t, _ in bad))
    return text


def main(check: bool) -> int:
    readme = README.read_text()
    match = BLOCK.search(readme)
    if not match:
        print("readme_block: FAIL (findings markers not found)")
        return 1
    fresh = rendered()
    if check:
        ok = match.group(2) == fresh
        print("readme_block:", "PASS" if ok else "FAIL (README findings differ from numbers.csv; run make memo)")
        return 0 if ok else 1
    README.write_text(readme[:match.start(2)] + fresh + readme[match.end(2):])
    print("readme_block: rendered")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
