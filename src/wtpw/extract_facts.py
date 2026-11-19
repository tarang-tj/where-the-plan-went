"""Parse every cached 10-K / 10-Q XBRL instance into data/work/facts.parquet (bronze input).

Usage: python -m wtpw.extract_facts   (reads data/work/filings.csv; no network)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from wtpw.filings import filing_url
from wtpw.sec_client import cache_path
from wtpw.xbrl_facts import parse_instance

WORK = Path("data/work")
SEGMENT_AXIS = "us-gaap:StatementBusinessSegmentsAxis"
CONSOLIDATION_AXIS = "srt:ConsolidationItemsAxis"


def add_portable_columns(facts: pd.DataFrame) -> pd.DataFrame:
    """Derive the columns whose SQL differs between Spark and DuckDB (JSON paths, date math),
    so the silver and gold SQL stays in the subset both engines run identically."""
    facts = facts.drop_duplicates(["accession", "concept", "context_id", "unit"]).copy()
    dims = facts["dims"].map(json.loads)
    facts["segment"] = dims.map(lambda d: d.get(SEGMENT_AXIS))
    facts["segment_name"] = facts["segment"].str.split(":").str[-1].str.removesuffix("Member")
    facts["consolidation_item"] = dims.map(lambda d: d.get(CONSOLIDATION_AXIS))
    facts["other_dims"] = dims.map(lambda d: len(set(d) - {SEGMENT_AXIS, CONSOLIDATION_AXIS}))
    start = pd.to_datetime(facts["period_start"])
    end = pd.to_datetime(facts["period_end"])
    facts["duration_days"] = (end - start).dt.days.astype("Int64")
    # 52/53-week years end near Dec 31 (LHX FY2020 ended 2021-01-01): label by end minus 15 days.
    facts["fiscal_year"] = (end - pd.Timedelta(days=15)).dt.year.astype("int64")
    # True when the fact is the filing's own current period (not a comparative or recast year).
    facts["is_current_period"] = facts["period_end"] == facts["report_date"]
    return facts


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
        df.insert(4, "report_date", f.report_date)
        frames.append(df)
        print(f"{f.ticker} {f.form:5} {f.filing_date} {len(df):6} facts")
    facts = add_portable_columns(pd.concat(frames, ignore_index=True))
    facts.to_parquet(WORK / "facts.parquet", index=False)
    print(f"wrote {WORK / 'facts.parquet'}: {len(facts):,} facts from {len(frames)} filings")


if __name__ == "__main__":
    main()
