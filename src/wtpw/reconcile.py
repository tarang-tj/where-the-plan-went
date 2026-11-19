"""Reconcile gate over the local DuckDB build (run `python -m wtpw.pipeline local` first).

1. Ties: inside every ranking partition, candidate facts that share the full ORDER BY key must
   share the value; otherwise the "first reported" pick is arbitrary (the RTX intersegment trap).
2. Segments vs consolidated: reported segment sales sum to consolidated sales within TOLERANCE
   (corporate / other lines explain small gaps; every gap is printed, large ones fail).
3. Guidance chain: when an update prints the prior outlook beside the current one, that printed
   prior equals the latest earlier vintage we recorded (catches a mis-assigned vintage or year).
4. Actual cross-check: the year-end release's GAAP sales equal the 10-K XBRL consolidated sales,
   and a "SegmentOP" actual equals the sum of XBRL segment operating income, within 0.5%.
Exit 1 on any failure.
"""
from __future__ import annotations

import sys

import duckdb

from wtpw import reconcile_guidance
from wtpw.pipeline import WORK
from wtpw.quote_check import filing_text, normalize

# Breaks in the guidance chain that the filing itself explains. Each needs a phrase that must
# appear in the cited release, and the exact printed prior it explains (silver units), so an
# exception is evidence, not a waiver, and a later edit to the row still fails.
CHAIN_EXCEPTIONS = {
    ("LMT", 2021, "EPS", "Fcst_Q3"): (
        936468, "0000936468-21-000098", "ex991q32021.htm", "current update 1 august 2021", (21.95, 22.25),
        ("Prior column is an off-cycle August 2021 outlook (after the pension settlement charge), "
        "not the Q2 release; that update is not an Item 2.02 earnings release.")),
    ("RTX", 2023, "Sales", "Fcst_Q3"): (
        101829, "0000101829-23-000034", "a2023-10x248xkerexhibit99.htm",
        "reported sales of approximately $68.5 billion, up from $67.5 - $68.5 billion", (67500.0, 68500.0),
        ("Prior is a reported-sales outlook issued between the Q2 and Q3 releases (the powder metal "
        "quarter), outside the Item 2.02 releases indexed here; Q2 printed only $73.0 - $74.0 billion.")),
}
TOLERANCE = 0.01  # 1% of consolidated sales (unallocated corporate and other lines)

TIE_SQL = """
WITH c AS (
  SELECT ticker, fiscal_year, COALESCE(segment_name, '(consolidated)') AS entity,
         CASE WHEN concept = 'us-gaap:OperatingIncomeLoss' THEN 'OP' ELSE 'Sales' END AS account,
         filing_date,
         CASE WHEN consolidation_item = 'us-gaap:OperatingSegmentsMember' THEN 0 ELSE 1 END AS cons_pref,
         CASE WHEN concept = 'us-gaap:Revenues' THEN 0 ELSE 1 END AS concept_pref,
         accession, value
  FROM bronze_facts
  WHERE form = '10-K' AND duration_days BETWEEN 350 AND 380 AND is_current_period
    AND concept IN ('us-gaap:Revenues', 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
                    'us-gaap:OperatingIncomeLoss')
    AND other_dims = 0
    AND ((segment IS NOT NULL AND (consolidation_item IS NULL
                                   OR consolidation_item = 'us-gaap:OperatingSegmentsMember'))
         OR n_dims = 0)
)
SELECT ticker, fiscal_year, entity, account, filing_date, accession,
       COUNT(DISTINCT value) AS n_values, MIN(value) / 1e6 AS lo, MAX(value) / 1e6 AS hi
FROM c
GROUP BY ticker, fiscal_year, entity, account, filing_date, cons_pref, concept_pref, accession
HAVING COUNT(DISTINCT value) > 1
"""

# Intersegment eliminations as tagged in each year's own 10-K. Filers disagree on sign (NOC +2,317,
# RTX -2,325 for the same economic item), so the magnitude is used: segments - |elim| = consolidated.
SEGMENT_SQL = """
WITH by_concept AS (
  -- One elimination figure per concept; LHX puts per-segment eliminations on contexts with one
  -- extra axis, hence other_dims <= 1 here only.
  SELECT ticker, fiscal_year, concept,
         SUM(CASE WHEN segment IS NULL THEN value END) / 1e6 AS elim_total,
         SUM(CASE WHEN segment IS NOT NULL THEN value END) / 1e6 AS elim_by_segment
  FROM bronze_facts
  WHERE form = '10-K' AND is_current_period AND duration_days BETWEEN 350 AND 380 AND other_dims <= 1
    AND concept IN ('us-gaap:Revenues', 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax')
    AND (consolidation_item = 'us-gaap:IntersegmentEliminationMember' OR segment_name = 'EliminationsAndOther')
  GROUP BY ticker, fiscal_year, concept
), elim AS (
  SELECT ticker, fiscal_year, ABS(elim_total) AS elim_total, ABS(elim_by_segment) AS elim_by_segment
  FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY ticker, fiscal_year
                                     ORDER BY CASE WHEN concept = 'us-gaap:Revenues' THEN 0 ELSE 1 END) AS rn
        FROM by_concept) x
  WHERE rn = 1
)
SELECT s.ticker, s.fiscal_year, SUM(s.value_usd_m) AS segment_sales,
       COALESCE(MAX(e.elim_total), MAX(e.elim_by_segment), 0) AS eliminations,
       c.value_usd_m AS consolidated_sales
FROM silver_segment_actuals s
JOIN silver_consolidated_actuals c
  ON c.ticker = s.ticker AND c.fiscal_year = s.fiscal_year AND c.account = 'Sales'
LEFT JOIN elim e ON e.ticker = s.ticker AND e.fiscal_year = s.fiscal_year
WHERE s.account = 'Sales'
GROUP BY s.ticker, s.fiscal_year, c.value_usd_m
ORDER BY s.ticker, s.fiscal_year
"""

CHAIN_SQL = """
WITH ordered AS (
  SELECT *, CASE scenario WHEN 'Plan' THEN 0 WHEN 'Fcst_Q1' THEN 1 WHEN 'Fcst_Q2' THEN 2
                          WHEN 'Fcst_Q3' THEN 3 END AS k
  FROM silver_guidance WHERE scenario <> 'Actual'
)
SELECT cur.ticker, cur.fiscal_year, cur.account, cur.basis, cur.scenario,
       cur.prior_low, cur.prior_high, prev.scenario AS prev_scenario, prev.low AS prev_low, prev.high AS prev_high
FROM ordered cur
JOIN ordered prev ON prev.ticker = cur.ticker AND prev.fiscal_year = cur.fiscal_year
 AND prev.account = cur.account AND prev.basis = cur.basis AND prev.entity = cur.entity
 AND prev.k = (SELECT MAX(k) FROM ordered p2 WHERE p2.ticker = cur.ticker AND p2.fiscal_year = cur.fiscal_year
               AND p2.account = cur.account AND p2.basis = cur.basis AND p2.entity = cur.entity AND p2.k < cur.k)
WHERE cur.prior_low IS NOT NULL
"""

ACTUAL_SQL = """
SELECT g.ticker, g.fiscal_year, g.account, g.measure, g.mid AS release_actual, x.value_usd_m AS xbrl
FROM silver_guidance g
JOIN gold_cube x ON x.ticker = g.ticker AND x.fiscal_year = g.fiscal_year AND x.entity = g.ticker
 AND x.scenario = 'Actual_XBRL' AND x.account = g.account
WHERE g.scenario = 'Actual' AND g.unit = 'USD_M'
  AND ((g.account = 'Sales' AND g.basis = 'GAAP') OR g.account = 'SegmentOP')
"""


def main() -> int:
    con = duckdb.connect(str(WORK / "local.duckdb"), read_only=True)
    failures = 0
    ties = con.execute(TIE_SQL).df()
    print(f"[ties] {len(ties)} ambiguous selections")
    for r in ties.itertuples(index=False):
        failures += 1
        print(f"  FAIL {r.ticker} {r.fiscal_year} {r.entity} {r.account} {r.accession}: {r.lo} vs {r.hi}")
    seg = con.execute(SEGMENT_SQL).df()
    # Segments that report gross of intersegment sales net down by the elimination; segments that
    # already report external sales carry no elimination in the sum. Take whichever ties closer.
    gross = seg.segment_sales - seg.eliminations
    seg["net_segments"] = gross.where((seg.consolidated_sales - gross).abs()
                                      < (seg.consolidated_sales - seg.segment_sales).abs(), seg.segment_sales)
    seg["gap_pct"] = (seg.consolidated_sales - seg.net_segments) / seg.consolidated_sales
    print(f"[segments] {len(seg)} company-years")
    for r in seg.itertuples(index=False):
        bad = abs(r.gap_pct) > TOLERANCE
        failures += bad
        if bad or abs(r.gap_pct) > 1e-9:
            print(f"  {'FAIL' if bad else 'gap '} {r.ticker} {r.fiscal_year}: segments {r.segment_sales:,.0f}"
                  f" less eliminations -> {r.net_segments:,.0f} vs consolidated {r.consolidated_sales:,.0f}"
                  f" ({r.gap_pct:+.2%})")
    chain = con.execute(CHAIN_SQL).df()
    print(f"[chain] {len(chain)} printed prior ranges checked")
    for r in chain.itertuples(index=False):
        if (r.prior_low, r.prior_high) != (r.prev_low, r.prev_high):
            exc = CHAIN_EXCEPTIONS.get((r.ticker, r.fiscal_year, r.account, r.scenario))
            pinned = exc and (r.prior_low, r.prior_high) == exc[4]
            if pinned and normalize(exc[3]) in filing_text(exc[0], exc[1], exc[2]):
                print(f"  explained {r.ticker} {r.fiscal_year} {r.account} {r.scenario}: {exc[5]}")
                continue
            failures += 1
            print(f"  FAIL {r.ticker} {r.fiscal_year} {r.account} {r.scenario}: printed prior "
                  f"{r.prior_low}-{r.prior_high} != {r.prev_scenario} {r.prev_low}-{r.prev_high}")
    actual = con.execute(ACTUAL_SQL).df()
    print(f"[actuals] {len(actual)} release actuals cross-checked against XBRL")
    for r in actual.itertuples(index=False):
        gap = r.release_actual / r.xbrl - 1
        if abs(gap) > 0.005:
            failures += 1
            print(f"  FAIL {r.ticker} {r.fiscal_year} {r.account} ({r.measure}): release {r.release_actual:,.0f}"
                  f" vs XBRL {r.xbrl:,.0f} ({gap:+.2%})")
    failures += reconcile_guidance.run(con)
    print("reconcile:", "FAIL" if failures else "PASS", f"({failures} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
