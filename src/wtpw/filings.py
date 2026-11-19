"""Filing index: which 10-K, 10-Q and earnings 8-K (Item 2.02) filings exist per company.

Source: EDGAR submissions JSON (https://data.sec.gov/submissions/CIK##########.json), which holds
the most recent filings plus older pages listed under filings.files.
"""
from __future__ import annotations

import pandas as pd

from wtpw.sec_client import get_json

COMPANIES = {
    "LMT": 936468,
    "NOC": 1133421,
    "RTX": 101829,
    "LHX": 202058,
    "BA": 12927,  # 10-K only, for program reach-forward losses
}
FORMS = {"10-K", "10-Q", "8-K"}
FIRST_DATE = "2018-01-01"


def _frame(block: dict) -> pd.DataFrame:
    cols = ["accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument"]
    return pd.DataFrame({c: block.get(c, []) for c in cols})


def filing_index(ticker: str) -> pd.DataFrame:
    cik = COMPANIES[ticker]
    sub = get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    frames = [_frame(sub["filings"]["recent"])]
    for page in sub["filings"].get("files", []):
        frames.append(_frame(get_json(f"https://data.sec.gov/submissions/{page['name']}")))
    df = pd.concat(frames, ignore_index=True)
    df = df[df["form"].isin(FORMS) & (df["filingDate"] >= FIRST_DATE)].copy()
    is_earnings = df["items"].fillna("").str.contains("2.02")
    df = df[(df["form"] != "8-K") | is_earnings]
    if ticker == "BA":
        df = df[df["form"] == "10-K"]
    df.insert(0, "ticker", ticker)
    df.insert(1, "cik", cik)
    df["folder"] = df["accessionNumber"].str.replace("-", "", regex=False)
    return df.drop_duplicates("accessionNumber").sort_values("filingDate").reset_index(drop=True)


def filing_url(cik: int, folder: str, name: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{name}"


def folder_items(cik: int, folder: str) -> list[str]:
    idx = get_json(filing_url(cik, folder, "index.json"))
    return [item["name"] for item in idx["directory"]["item"]]


def instance_name(names: list[str]) -> str | None:
    """The XBRL instance: SEC's extracted *_htm.xml for inline filings, else the plain .xml instance."""
    extracted = [n for n in names if n.endswith("_htm.xml")]
    if extracted:
        return extracted[0]
    skip = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml", "FilingSummary.xml")
    plain = [n for n in names if n.endswith(".xml") and not n.endswith(skip) and "-" in n]
    return plain[0] if len(plain) == 1 else None
