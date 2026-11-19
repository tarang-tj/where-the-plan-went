"""Schema contract for curated CSVs (curated/{guidance,charges,eac}_<TICKER>.csv).

Every file of a kind has the same header in the same order (both engines read them by glob),
enumerations are closed, and every row is evidence: accession + document + verbatim quote.
Run: python -m wtpw.curation_contract   (exit 1 on any violation)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

CURATED = Path("curated")
HEADERS = {
    "guidance": ["ticker", "cik", "fiscal_year", "vintage", "release_date", "accession", "document",
                 "entity", "metric", "basis", "measure", "low", "high", "unit", "prior_low", "prior_high",
                 "quote"],
    "charges": ["ticker", "cik", "fiscal_year", "quarter", "segment", "program", "amount", "unit", "basis",
                "accession", "document", "quote"],
    "eac": ["ticker", "cik", "fiscal_year", "entity", "metric", "value", "unit", "accession", "document",
            "quote"],
}
ENUMS = {
    ("guidance", "vintage"): {"Plan", "Fcst_Q1", "Fcst_Q2", "Fcst_Q3", "Actual"},
    ("guidance", "metric"): {"Sales", "SegmentOP", "EPS", "FCF"},
    ("guidance", "basis"): {"GAAP", "non-GAAP"},
    ("guidance", "unit"): {"USD_M", "USD_B", "USD_per_share"},
    ("charges", "quarter"): {"Q1", "Q2", "Q3", "Q4", "FY"},
    ("charges", "basis"): {"reach-forward loss", "charge"},
    ("charges", "unit"): {"USD_M"},
    ("eac", "metric"): {"NetEAC", "FavEAC", "UnfavEAC"},
    ("eac", "unit"): {"USD_M", "USD_B"},
}
ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")


def validate(path: Path) -> list[str]:
    kind, _, ticker = path.stem.partition("_")
    if kind not in HEADERS or not ticker.isupper():
        return [f"{path.name}: name must be <guidance|charges|eac>_<TICKER>.csv"]
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    errors = []
    if list(df.columns) != HEADERS[kind]:
        errors.append(f"{path.name}: header {list(df.columns)} != contract {HEADERS[kind]}")
        return errors
    for i, row in df.iterrows():
        where = f"{path.name}:{i + 2}"
        if row["ticker"] != ticker:
            errors.append(f"{where}: ticker {row['ticker']} in {ticker} file")
        if not ACCESSION.match(row["accession"]):
            errors.append(f"{where}: bad accession {row['accession']!r}")
        for (k, col), allowed in ENUMS.items():
            if k == kind and row[col] not in allowed:
                errors.append(f"{where}: {col}={row[col]!r} not in {sorted(allowed)}")
        if kind == "guidance" and row["low"] and row["high"] and float(row["low"]) > float(row["high"]):
            errors.append(f"{where}: low > high")
        if kind == "guidance" and row["vintage"] == "Actual" and row["low"] != row["high"]:
            errors.append(f"{where}: Actual rows carry one value (low == high)")
    key = {"guidance": ["fiscal_year", "vintage", "entity", "metric", "basis"],
           "charges": ["fiscal_year", "quarter", "program"],
           "eac": ["fiscal_year", "entity", "metric"]}[kind]
    dups = df[df.duplicated(key, keep=False)]
    if not dups.empty:
        errors.append(f"{path.name}: duplicate keys {dups[key].drop_duplicates().values.tolist()}")
    return errors


def main() -> int:
    paths = sorted(CURATED.glob("*.csv"))
    errors = [e for p in paths for e in validate(p)]
    for e in errors:
        print("FAIL", e)
    print(f"curation_contract: {'FAIL' if errors else 'PASS'} ({len(paths)} files, {len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
