"""Guidance-level reconcile checks (split from reconcile.py to keep files small).

magnitude:  every Sales / SegmentOP guidance midpoint (any vintage) is within a band of the same
            company-year's 10-K XBRL figure (BANDS). Catches a billions/millions mix-up or a value
            copied from the wrong table, which quote_check alone cannot see.
bridge:     each company-year in the bridge has exactly one Plan and one Actual measure family for
            Sales and SegmentOP, so the bridge never silently takes the larger of two measures.
unmatched:  a release Actual with no XBRL counterpart is reported, never skipped; only listed
            exceptions (with a reason) pass.
"""
from __future__ import annotations

# Sales barely moves against its plan; segment profit legitimately can (NOC 2023 planned 4,350 and
# reported 2,760 after the B-21 charge). A unit error is 1,000x, so both bands still catch it.
BANDS = {"Sales": (0.5, 1.5), "SegmentOP": (0.2, 5.0)}

MAGNITUDE_SQL = """
SELECT g.ticker, g.fiscal_year, g.scenario, g.account, g.measure, g.mid, x.value_usd_m AS xbrl
FROM silver_guidance g
JOIN gold_cube x ON x.ticker = g.ticker AND x.fiscal_year = g.fiscal_year AND x.entity = g.ticker
 AND x.scenario = 'Actual_XBRL' AND x.account = g.account
WHERE g.account IN ('Sales', 'SegmentOP') AND g.unit = 'USD_M'
"""

BRIDGE_SQL = """
SELECT b.ticker, b.fiscal_year, g.scenario, g.account, COUNT(DISTINCT g.measure_family) AS families
FROM gold_bridge b
JOIN silver_guidance g ON g.ticker = b.ticker AND g.fiscal_year = b.fiscal_year
WHERE g.scenario IN ('Plan', 'Actual') AND g.account IN ('Sales', 'SegmentOP')
GROUP BY b.ticker, b.fiscal_year, g.scenario, g.account
HAVING COUNT(DISTINCT g.measure_family) <> 1
"""

UNMATCHED_SQL = """
SELECT g.ticker, g.fiscal_year, g.account, g.measure
FROM silver_guidance g
LEFT JOIN gold_cube x ON x.ticker = g.ticker AND x.fiscal_year = g.fiscal_year AND x.entity = g.ticker
 AND x.scenario = 'Actual_XBRL' AND x.account = g.account
WHERE g.scenario = 'Actual' AND g.unit = 'USD_M'
  AND ((g.account = 'Sales' AND g.basis = 'GAAP') OR g.account = 'SegmentOP')
  AND x.value_usd_m IS NULL
"""
UNMATCHED_ALLOWED = {
    ("LHX", 2025, "Sales"): "FY2025 10-K tags revenue only on a product or service axis, no total fact",
}


def run(con) -> int:
    failures = 0
    mag = con.execute(MAGNITUDE_SQL).df()
    ratio = mag.mid / mag.xbrl
    lo = mag.account.map(lambda a: BANDS[a][0])
    hi = mag.account.map(lambda a: BANDS[a][1])
    bad = mag[(ratio < lo) | (ratio > hi)]
    print(f"[magnitude] {len(mag)} guidance midpoints checked against the 10-K figure {BANDS}")
    for r in bad.itertuples(index=False):
        failures += 1
        print(f"  FAIL {r.ticker} {r.fiscal_year} {r.scenario} {r.account}: mid {r.mid:,.1f} vs XBRL {r.xbrl:,.1f}")
    multi = con.execute(BRIDGE_SQL).df()
    print(f"[bridge] {len(multi)} company-year inputs with other than one measure family")
    for r in multi.itertuples(index=False):
        failures += 1
        print(f"  FAIL {r.ticker} {r.fiscal_year} {r.scenario} {r.account}: {r.families} measure families")
    unmatched = con.execute(UNMATCHED_SQL).df()
    for r in unmatched.itertuples(index=False):
        reason = UNMATCHED_ALLOWED.get((r.ticker, int(r.fiscal_year), r.account))
        if reason:
            print(f"  unmatched (allowed) {r.ticker} {r.fiscal_year} {r.account}: {reason}")
        else:
            failures += 1
            print(f"  FAIL {r.ticker} {r.fiscal_year} {r.account} ({r.measure}): release actual has no XBRL figure")
    return failures
