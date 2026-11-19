"""Parse every cached 10-K / 10-Q XBRL instance into data/work/facts.parquet (bronze input).

Usage: python -m wtpw.extract_facts   (reads data/work/filings.csv; no network)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from wtpw.filings import filing_url
from wtpw.sec_client import cache_path
from wtpw.xbrl_facts import parse_instance

WORK = Path("data/work")


def main() -> None:
    filings = pd.read_csv(WORK / "filings.csv")
    filings = filings[filings["instance"].notna()]
    frames = []
    for f in filings.itertuples(index=False):
        url = filing_url(f.cik, f.accession.replace("-", ""), f.instance)
        rows = parse_instance(cache_path(url).read_bytes(), f.accession)
        df = pd.DataFrame(rows)
        if df.empty:
            raise RuntimeError(f"{f.ticker} {f.accession}: instance parsed to zero numeric facts")
        df.insert(0, "ticker", f.ticker)
        df.insert(2, "form", f.form)
        df.insert(3, "filing_date", f.filing_date)
        frames.append(df)
        print(f"{f.ticker} {f.form:5} {f.filing_date} {len(df):6} facts")
    facts = pd.concat(frames, ignore_index=True)
    facts.to_parquet(WORK / "facts.parquet", index=False)
    print(f"wrote {WORK / 'facts.parquet'}: {len(facts):,} facts from {len(frames)} filings")


if __name__ == "__main__":
    main()
