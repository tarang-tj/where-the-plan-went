"""Download (once) every filing this project reads, into the data/raw/ cache.

For each company: the filing index, every 10-K and 10-Q XBRL instance, and the Exhibit 99.1
earnings release of every Item 2.02 8-K (guidance vintages live there). BA: 10-K main documents.
Usage: python -m wtpw.fetch [--tickers LMT NOC] [--since 2018-01-01] [--until 2026-12-31]
Writes data/work/filings.csv: one row per filing with the documents found.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from wtpw.filings import COMPANIES, filing_index, filing_url, folder_items, instance_name
from wtpw.sec_client import get

WORK = Path("data/work")
EX99 = re.compile(r"(ex-?99[-_.]?0?1|ex991|exhibit99[-_]?1|earningsrelea)", re.IGNORECASE)


def earnings_exhibit(names: list[str]) -> str | None:
    hits = [n for n in names if n.lower().endswith((".htm", ".html")) and EX99.search(n)]
    return min(hits, key=len) if hits else None


def fetch_company(ticker: str, since: str, until: str) -> list[dict]:
    idx = filing_index(ticker)
    idx = idx[(idx["filingDate"] >= since) & (idx["filingDate"] <= until)]
    rows = []
    for f in idx.itertuples(index=False):
        names = folder_items(f.cik, f.folder)
        row = {"ticker": ticker, "cik": f.cik, "accession": f.accessionNumber, "form": f.form,
               "filing_date": f.filingDate, "report_date": f.reportDate,
               "primary_document": f.primaryDocument, "instance": None, "exhibit": None}
        if f.form in ("10-K", "10-Q"):
            row["instance"] = instance_name(names)
            if row["instance"] is None:
                raise RuntimeError(f"{ticker} {f.accessionNumber}: no unique XBRL instance in {names}")
            get(filing_url(f.cik, f.folder, row["instance"]))
            if ticker == "BA" or f.form == "10-K":
                get(filing_url(f.cik, f.folder, f.primaryDocument))  # text for charges and EAC quotes
        else:
            row["exhibit"] = earnings_exhibit(names)
            if row["exhibit"] is None:
                print(f"WARN {ticker} {f.accessionNumber} 8-K 2.02 without an EX-99.1 htm: {names}")
            else:
                get(filing_url(f.cik, f.folder, row["exhibit"]))
        rows.append(row)
        print(f"{ticker} {f.form:5} {f.filingDate} {f.accessionNumber} ok")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", default=list(COMPANIES))
    ap.add_argument("--since", default="2018-01-01")
    ap.add_argument("--until", default="2026-12-31")
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    rows = [r for t in args.tickers for r in fetch_company(t, args.since, args.until)]
    out = WORK / "filings.csv"
    new = pd.DataFrame(rows)
    if out.exists():
        new = pd.concat([pd.read_csv(out), new]).drop_duplicates("accession", keep="last")
    new.sort_values(["ticker", "filing_date"]).to_csv(out, index=False)
    print(f"wrote {out} ({len(new)} filings)")


if __name__ == "__main__":
    main()
