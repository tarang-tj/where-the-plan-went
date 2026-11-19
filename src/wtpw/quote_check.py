"""Provenance gate for curated rows: the quote must be in the filing, and the number in the quote.

Curated CSVs (guidance, EAC series, program charges) carry accession + document + a verbatim
quote. This check loads the cached filing (never the network), reduces HTML to text, and fails
unless (1) the normalized quote is a substring of the normalized filing text and (2) every value
in the row appears inside the quote as printed (e.g. 8,100 or 8.1 or 950).
Run: python -m wtpw.quote_check   (exit 1 on any failure)
"""
from __future__ import annotations

import html
import re
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

from wtpw.sec_client import cache_path

CURATED = Path("curated")
VALUE_COLS = ("low", "high", "prior_low", "prior_high", "value", "amount")
_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")
_SPACES = dict.fromkeys(map(ord, "\u00a0\u2009\u202f\u200b"), " ")


def normalize(text: str) -> str:
    text = html.unescape(text).translate(_DASHES).translate(_SPACES)
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


@lru_cache(maxsize=64)
def filing_text(cik: int, accession: str, document: str) -> str:
    folder = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{document}"
    path = cache_path(url)
    if not path.exists():
        raise FileNotFoundError(f"not cached (run fetch first): {url}")
    raw = path.read_text(errors="replace")
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    # Table cells and blocks become spaces so "Net sales</td><td>$75,048" reads as one line.
    return normalize(re.sub(r"<[^>]+>", " ", raw))


def number_forms(value: float) -> set[str]:
    """Printed forms a value may take in a filing: 8100 -> {'8,100', '8100', '8,100.0', ...};
    26.0 -> {'26', '26.0', '26.00'}; 8.1 -> {'8.1', '8.10'}."""
    v = abs(value)
    forms = {f"{v:,.2f}", f"{v:.2f}", f"{v:,.1f}", f"{v:.1f}", f"{v:g}"}
    if v == int(v):
        forms |= {f"{v:,.0f}", f"{v:.0f}"}
    return forms


def printed(form: str, text: str) -> bool:
    """True when the number appears as a whole number: '6,300' does not match inside '16,300'."""
    return re.search(rf"(?<![\d,.]){re.escape(form)}(?![\d]|[.,]\d)", text) is not None


def check_row(row: pd.Series) -> list[str]:
    errors = []
    quote = normalize(str(row["quote"]))
    if len(quote) < 12:
        errors.append("quote too short to be evidence")
    try:
        text = filing_text(int(row["cik"]), row["accession"], row["document"])
    except FileNotFoundError as err:
        return [str(err)]
    if quote not in text:
        errors.append("quote not found in filing text")
    for col in VALUE_COLS:
        has_value = col in row and pd.notna(row[col])
        if has_value and not any(printed(form, quote) for form in number_forms(float(row[col]))):
            errors.append(f"{col}={row[col]} not printed in quote")
    return errors


def run(paths: list[Path]) -> int:
    failures = 0
    for path in paths:
        df = pd.read_csv(path)
        for i, row in df.iterrows():
            for err in check_row(row):
                failures += 1
                print(f"FAIL {path.name}:{i + 2} {row['accession']} {err}")
        print(f"{path.name}: {len(df)} rows checked")
    print("quote_check:", "FAIL" if failures else "PASS", f"({failures} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(sorted(CURATED.glob("*.csv"))))
