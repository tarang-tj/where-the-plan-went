"""Gold -> outputs/numbers.csv (every number the memo, workbook and page may print) and
web/data.json (everything the page draws). No number is typed by hand downstream.
Usage: python -m wtpw.findings   (after `python -m wtpw.pipeline local`)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from wtpw.pipeline import WORK

GOLD = WORK / "gold_local"
OUT = Path("outputs")
WEB = Path("web")
EDGAR = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"
ORDER = ["Plan", "Fcst_Q1", "Fcst_Q2", "Fcst_Q3", "Actual"]
LARGE_MISS = 300.0  # USD M below plan


def _url(cik, accession, document) -> str:
    return EDGAR.format(cik=int(cik), folder=str(accession).replace("-", ""), doc=document)


def _curated(kind: str) -> pd.DataFrame:
    return pd.concat([pd.read_csv(p) for p in sorted(Path("curated").glob(f"{kind}_*.csv"))], ignore_index=True)


def numbers(bridge: pd.DataFrame, err: pd.DataFrame) -> list[dict]:
    rows = []

    def add(key, value, fmt, note):
        rows.append({"key": key, "value": value, "display": fmt.format(value), "note": note})

    b = bridge.assign(miss=bridge.actual_op - bridge.plan_op)
    large = b[b.miss <= -LARGE_MISS]
    add("bridge_company_years", len(b), "{:d}", "company-years with a dollar segment-profit plan and actual")
    add("large_misses", len(large), "{:d}", f"misses of more than ${LARGE_MISS:.0f}M below plan")
    if large.empty:
        raise ValueError("no large misses: the headline finding no longer applies")
    cover = (-large.named_charges / -large.miss)
    add("large_miss_min_charge_cover", float(cover.min()), "{:.0%}", "smallest share of a large miss covered by named charges")
    rest = b[b.miss > -LARGE_MISS]
    add("other_years_worst_miss", float(rest.miss.min()), "{:+,.0f}", "worst plan variance among the other years, $M")
    worst = float(rest.miss.min()) + 0.0
    if worst >= 0:
        raise ValueError("every other year beat plan; the 'below plan' prose no longer applies")
    add("other_years_worst_miss_abs", abs(worst), "{:,.0f}", "same, unsigned for prose (always below plan)")
    for r in b.itertuples():
        k = f"{r.ticker}_{r.fiscal_year}"
        for col in ("plan_op", "volume", "named_charges", "other", "actual_op", "miss"):
            v = float(getattr(r, col)) + 0.0  # + 0.0 turns -0.0 into 0.0, so nothing prints "-0"
            add(f"bridge_{k}_{col}", v, "{:,.0f}" if col in ("plan_op", "actual_op") else "{:+,.0f}",
                f"{r.ticker} {r.fiscal_year} {col}, $M")
            add(f"bridge_{k}_{col}_abs", abs(v), "{:,.0f}", f"{r.ticker} {r.fiscal_year} {col}, $M, unsigned for prose")
            # Direction words come from the sign, so prose using an _abs key cannot state the wrong way.
            rows.append({"key": f"bridge_{k}_{col}_verb", "value": v, "display": "added" if v >= 0 else "took away",
                         "note": "direction word for the matching _abs key"})
    for acct in ("Sales", "SegmentOP", "EPS", "FCF"):
        for sc in ("Plan", "Fcst_Q1", "Fcst_Q2", "Fcst_Q3"):
            x = err[(err.account == acct) & (err.scenario == sc)]
            if x.empty:
                continue
            tag = f"{acct}_{sc}"
            add(f"err_{tag}_n", len(x), "{:d}", f"{acct} {sc} vintages scored")
            add(f"err_{tag}_median_abs", float(x.error_vs_mid.abs().median()), "{:.1%}", "median |actual / midpoint - 1|")
            add(f"err_{tag}_beat_share", float((x.error_vs_mid > 0).mean()), "{:.0%}", "share where actual beat the midpoint")
            add(f"err_{tag}_inside_share", float(x.inside_range.mean()), "{:.0%}", "share where actual fell inside the range")
    return rows


def walks(g: pd.DataFrame, charges: pd.DataFrame) -> list[dict]:
    fam = pd.read_csv("reference/measure_families.csv")
    g = g.merge(fam[["ticker", "measure", "fy_from", "fy_to", "family"]], on=["ticker", "measure"], how="left")
    in_range = (g.fy_from.isna() | (g.fiscal_year >= g.fy_from)) & (g.fy_to.isna() | (g.fiscal_year <= g.fy_to))
    g = g[in_range | g.family.isna()].drop(columns=["fy_from", "fy_to"])
    g["family"] = g["family"].fillna(g["measure"])
    out = []
    for (t, fy, acct, basis, measure), grp in g.groupby(["ticker", "fiscal_year", "metric", "basis", "measure"]):
        grp = grp.assign(k=grp.vintage.map(ORDER.index)).sort_values("k")
        if len(grp) < 2:
            continue
        ch = charges[(charges.ticker == t) & (charges.fiscal_year == fy)] if acct == "SegmentOP" else charges.iloc[0:0]
        out.append({
            "ticker": t, "fiscal_year": int(fy), "account": acct, "basis": basis, "measure": measure,
            "family": grp.family.iloc[0],
            "unit": "USD_per_share" if grp.unit.iloc[0] == "USD_per_share" else "USD_M",
            "vintages": [{"scenario": r.vintage, "date": r.release_date,
                          "low": float(r.low) * (1000 if r.unit == "USD_B" else 1),
                          "high": float(r.high) * (1000 if r.unit == "USD_B" else 1),
                          "quote": r.quote, "url": _url(r.cik, r.accession, r.document)} for r in grp.itertuples()],
            "charges": [{"quarter": c.quarter, "segment": c.segment, "program": c.program, "amount": float(c.amount),
                         "basis": c.basis, "quote": c.quote, "url": _url(c.cik, c.accession, c.document)}
                        for c in ch.itertuples()],
        })
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    WEB.mkdir(exist_ok=True)
    bridge = pd.read_csv(GOLD / "gold_bridge.csv").sort_values(["ticker", "fiscal_year"], ignore_index=True)
    err = pd.read_csv(GOLD / "gold_guidance_error.csv").sort_values(
        ["ticker", "fiscal_year", "account", "basis", "measure", "scenario"], ignore_index=True)
    nums = numbers(bridge, err)
    g, charges, eac = _curated("guidance"), _curated("charges"), _curated("eac")
    n_filings = int(pd.read_csv(WORK / "filings.csv").shape[0])
    n_facts = int(pd.read_parquet(WORK / "facts.parquet").shape[0])
    # Segment-profit guidance midpoints per vintage, for the company-years that have a bridge.
    seg = g[(g.metric == "SegmentOP")].assign(mid=lambda d: (d.low + d.high) / 2)
    for r in seg.merge(bridge[["ticker", "fiscal_year"]], on=["ticker", "fiscal_year"]).itertuples():
        nums.append({"key": f"walk_{r.ticker}_{r.fiscal_year}_SegmentOP_{r.vintage}", "value": float(r.mid),
                     "display": f"{r.mid:,.0f}", "note": f"{r.ticker} {r.fiscal_year} segment profit {r.vintage} midpoint, $M"})
    nums += [
        {"key": "filings", "value": n_filings, "display": f"{n_filings:,}", "note": "SEC filings cached and read"},
        {"key": "facts", "value": n_facts, "display": f"{n_facts:,}", "note": "XBRL facts parsed"},
        {"key": "curated_rows", "value": len(g) + len(charges) + len(eac),
         "display": f"{len(g) + len(charges) + len(eac):,}", "note": "hand-curated rows, each quote-checked"},
        {"key": "large_miss_threshold", "value": LARGE_MISS, "display": f"${LARGE_MISS:,.0f} million",
         "note": "a large miss is this far below plan"},
        {"key": "charge_threshold", "value": 100.0, "display": "$100 million",
         "note": "curation contract: a program qualifies at this annual loss"},
    ]
    keys = [n["key"] for n in nums]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        raise ValueError(f"duplicate numbers.csv keys: {sorted(dup)}")
    pd.DataFrame(nums).to_csv(OUT / "numbers.csv", index=False)
    # Undefined values (TCPI at completion) become null: browsers reject a bare NaN in JSON.
    program = {name: pd.read_csv(f"data/program/program_{name}.csv").astype(object)
               .where(lambda d: d.notna(), None).to_dict("records") for name in ("evm", "revrec")}
    # A hash of the inputs, not the git commit: committing data.json would change the commit it names.
    inputs = sorted(Path("curated").glob("*.csv")) + [Path("reference/measure_families.csv"),
                                                       GOLD / "gold_cube.csv"]
    lines = sorted(line for p in inputs for line in p.read_bytes().splitlines())  # gold row order varies
    digest = hashlib.sha256(b"\n".join(lines)).hexdigest()[:12]
    data = {
        "meta": {"inputs_sha256": digest, "filings": n_filings, "facts": n_facts,
                 "curated_rows": int(len(g) + len(charges) + len(eac))},
        "numbers": {n["key"]: {"value": n["value"], "display": n["display"]} for n in nums},
        "walks": walks(g, charges),
        "bridges": bridge.to_dict("records"),
        "errors": err.to_dict("records"),
        "eac": eac.assign(url=[_url(*r) for r in eac[["cik", "accession", "document"]].itertuples(index=False)])
                  .drop(columns=["cik"]).to_dict("records"),
        "charges": charges.assign(url=[_url(*r) for r in charges[["cik", "accession", "document"]]
                                       .itertuples(index=False)]).drop(columns=["cik"]).to_dict("records"),
        "program": program,
    }
    (WEB / "data.json").write_text(json.dumps(data, separators=(",", ":"), default=str, allow_nan=False))
    print(f"numbers.csv: {len(nums)} keys; data.json: {len(data['walks'])} walks, "
          f"{len(data['bridges'])} bridges, {len(data['charges'])} charges")


if __name__ == "__main__":
    main()
