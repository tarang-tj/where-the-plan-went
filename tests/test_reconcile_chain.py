"""The chain check pairs each printed prior range with the latest earlier vintage, and the bridge
steps sum to the actual. Built on a throwaway DuckDB, independent of the curated files."""
import duckdb

from wtpw.pipeline import transforms
from wtpw.reconcile import CHAIN_SQL

ROWS = [  # scenario, low, high, prior_low, prior_high
    ("Plan", 8100, 8200, None, None),
    ("Fcst_Q1", 8100, 8200, None, None),
    ("Fcst_Q2", 6600, 6700, 8100, 8200),
    ("Fcst_Q3", 6675, 6725, 6600, 6700),
]


def _db(rows):
    con = duckdb.connect()
    con.execute("""CREATE TABLE silver_guidance (ticker VARCHAR, fiscal_year INT, scenario VARCHAR,
        entity VARCHAR, account VARCHAR, basis VARCHAR, low DOUBLE, high DOUBLE,
        prior_low DOUBLE, prior_high DOUBLE)""")
    for sc, lo, hi, plo, phi in rows:
        con.execute("INSERT INTO silver_guidance VALUES ('LMT', 2025, ?, 'LMT', 'SegmentOP', 'non-GAAP', ?, ?, ?, ?)",
                    [sc, lo, hi, plo, phi])
    return con


def _mismatches(con):
    df = con.execute(CHAIN_SQL).df()
    return [(r.scenario, r.prev_scenario) for r in df.itertuples()
            if (r.prior_low, r.prior_high) != (r.prev_low, r.prev_high)]


def test_consistent_chain_passes():
    df = _db(ROWS).execute(CHAIN_SQL).df()
    assert sorted(zip(df.scenario, df.prev_scenario)) == [("Fcst_Q2", "Fcst_Q1"), ("Fcst_Q3", "Fcst_Q2")]
    assert _mismatches(_db(ROWS)) == []


def test_mis_assigned_vintage_fails():
    bad = [r if r[0] != "Fcst_Q2" else ("Fcst_Q2", 6600, 6700, 8000, 8200) for r in ROWS]
    assert _mismatches(_db(bad)) == [("Fcst_Q2", "Fcst_Q1")]


def test_bridge_steps_sum_to_actual():
    con = duckdb.connect()
    con.execute("""CREATE TABLE silver_guidance AS SELECT * FROM (VALUES
        ('LMT', 2025, 'Plan', 'Sales', 74250.0), ('LMT', 2025, 'Plan', 'SegmentOP', 8150.0),
        ('LMT', 2025, 'Actual', 'Sales', 75048.0), ('LMT', 2025, 'Actual', 'SegmentOP', 6743.0))
        t(ticker, fiscal_year, scenario, account, mid)""")
    con.execute("CREATE TABLE silver_charges AS SELECT 'LMT' AS ticker, 2025 AS fiscal_year, 1615.0 AS amount_usd_m")
    body = dict(transforms())["gold_bridge"]
    r = con.execute(body).df().iloc[0]
    assert abs(r.plan_op + r.volume + r.named_charges + r.other - r.actual_op) < 1e-9
    assert round(r.volume, 2) == 87.59 and r.named_charges == -1615.0
