"""Measure families: every label maps to at most one family in any fiscal year, and every
mapping carries a reason. Overlapping ranges would put one row in two families."""
import itertools

import pandas as pd


def test_ranges_do_not_overlap_and_have_reasons():
    fam = pd.read_csv("reference/measure_families.csv")
    assert fam["reason"].fillna("").str.len().gt(10).all()
    for (_, _), grp in fam.groupby(["ticker", "measure"]):
        spans = sorted((r.fy_from if pd.notna(r.fy_from) else 0, r.fy_to if pd.notna(r.fy_to) else 9999)
                       for r in grp.itertuples())
        for (_, end), (start, _) in itertools.pairwise(spans):
            assert end < start, f"overlapping fiscal-year ranges in {grp.iloc[0].ticker} {grp.iloc[0].measure}"
