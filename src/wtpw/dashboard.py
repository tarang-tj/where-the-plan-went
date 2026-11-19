"""Write dashboards/where-the-plan-went.lvdash.json: a Databricks AI/BI dashboard over the gold
tables, deployed by the bundle (resources/dashboard.yml). Usage: python -m wtpw.dashboard"""
from __future__ import annotations

import json
from pathlib import Path

T = "workspace.wtpw"
DATASETS = [
    {"name": "bridge_long", "displayName": "Plan variance vs named charges",
     "queryLines": [
         f"SELECT concat(ticker, ' ', fiscal_year) AS company_year, 'Plan variance' AS measure, "
         f"actual_op - plan_op AS usd_m FROM {T}.gold_bridge ",
         f"UNION ALL SELECT concat(ticker, ' ', fiscal_year), 'Named program charges', named_charges "
         f"FROM {T}.gold_bridge"]},
    {"name": "guidance_error", "displayName": "Guidance error by vintage",
     "queryLines": [
         "SELECT CASE scenario WHEN 'Plan' THEN '1 Plan' WHEN 'Fcst_Q1' THEN '2 Q1 update' "
         "WHEN 'Fcst_Q2' THEN '3 Q2 update' ELSE '4 Q3 update' END AS vintage, account, "
         f"abs(error_vs_mid) AS abs_error FROM {T}.gold_guidance_error WHERE account IN ('Sales', 'SegmentOP')"]},
]


def bar() -> dict:
    return {"widget": {"name": "variance_vs_charges", "queries": [{"name": "main_query", "query": {
        "datasetName": "bridge_long", "disaggregated": False, "fields": [
            {"name": "company_year", "expression": "`company_year`"},
            {"name": "measure", "expression": "`measure`"},
            {"name": "sum(usd_m)", "expression": "SUM(`usd_m`)"}]}}],
        "spec": {"version": 3, "widgetType": "bar", "mark": {"layout": "group"}, "frame": {"showTitle": True,
                 "title": "Segment profit vs plan, and the program charges disclosed that year ($M)"},
                 "encodings": {
                     "x": {"fieldName": "company_year", "scale": {"type": "categorical"}, "displayName": "Company-year"},
                     "y": {"fieldName": "sum(usd_m)", "scale": {"type": "quantitative"}, "displayName": "$M"},
                     "color": {"fieldName": "measure", "scale": {"type": "categorical"}, "displayName": "Measure"}}}},
        "position": {"x": 0, "y": 2, "width": 6, "height": 7}}


def line() -> dict:
    return {"widget": {"name": "error_by_vintage", "queries": [{"name": "main_query", "query": {
        "datasetName": "guidance_error", "disaggregated": False, "fields": [
            {"name": "vintage", "expression": "`vintage`"},
            {"name": "account", "expression": "`account`"},
            {"name": "avg(abs_error)", "expression": "AVG(`abs_error`)"}]}}],
        "spec": {"version": 3, "widgetType": "line", "frame": {"showTitle": True,
                 "title": "Average miss vs the guidance midpoint, by release (Sales and segment profit)"},
                 "encodings": {
                     "x": {"fieldName": "vintage", "scale": {"type": "categorical"}, "displayName": "Release"},
                     "y": {"fieldName": "avg(abs_error)", "scale": {"type": "quantitative"}, "displayName": "Avg |error|",
                           "format": {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}},
                     "color": {"fieldName": "account", "scale": {"type": "categorical"}, "displayName": "Account"}}}},
        "position": {"x": 0, "y": 9, "width": 6, "height": 6}}


def text() -> dict:
    return {"widget": {"name": "title", "multilineTextboxSpec": {"lines": [
        "## Where the plan went\n",
        "Lockheed, Northrop, RTX and L3Harris guidance (plan, three updates, actual) from SEC filings, "
        "bridged to the program charges each company disclosed. Built by the wtpw-medallion pipeline."]}},
        "position": {"x": 0, "y": 0, "width": 6, "height": 2}}


def main() -> None:
    doc = {"datasets": DATASETS, "pages": [{"name": "plan_vs_actual", "displayName": "Plan vs actual",
                                            "layout": [text(), bar(), line()]}]}
    out = Path("dashboards/where-the-plan-went.lvdash.json")
    out.write_text(json.dumps(doc, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
