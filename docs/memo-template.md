# Defense Finance Model on Databricks

**Question.** When a defense prime misses its own profit plan, what caused the miss?

**Data.** I collected every earnings release, 10-K and 10-Q that Lockheed Martin, Northrop Grumman, RTX and L3Harris filed from 2018 through 2026, plus Boeing's 10-Ks for its defense program losses: {{filings}} SEC filings and {{facts}} XBRL facts. Each January outlook is the plan, the three quarterly updates are forecasts, and the year-end release is the actual. Guidance ranges, program charges and EAC adjustments are not tagged in XBRL, so I copied them from the filings, {{curated_rows}} rows in all, each with the sentence it came from. The build fails if a quote is not in the cached filing word for word or if a number is not printed inside its quote. The same SQL runs as a Lakeflow pipeline on Databricks and on DuckDB, and a parity check compares the two outputs row by row.

## The large misses are program charges

Of the company-years scored, {{bridge_company_years}} have a dollar plan for segment operating profit (Lockheed 2019 to 2025, Northrop 2023 to 2025). {{large_misses}} of them came in more than {{large_miss_threshold}} below plan. In each of those, losses the company itself tied to named programs covered at least {{large_miss_min_charge_cover}} of the miss. In the other years, no company-year finished more than ${{other_years_worst_miss_abs}} million below plan.

Lockheed 2025 shows the shape. The plan was ${{bridge_LMT_2025_plan_op}} million. Sales volume {{bridge_LMT_2025_volume_verb}} ${{bridge_LMT_2025_volume_abs}} million at the planned margin. Second-quarter reach-forward losses on a classified Aeronautics program, the Canadian Maritime Helicopter Program and the Turkish Utility Helicopter Program took ${{bridge_LMT_2025_named_charges_abs}} million. Everything else {{bridge_LMT_2025_other_verb}} ${{bridge_LMT_2025_other_abs}} million, and the actual was ${{bridge_LMT_2025_actual_op}} million.

## Guidance is set to be beaten

Sales beat the midpoint of the January plan in {{err_Sales_Plan_beat_share}} of the company-years scored and landed inside the guided range in only {{err_Sales_Plan_inside_share}}. Earnings per share beat the January midpoint in {{err_EPS_Plan_beat_share}}. The exception is segment profit in a charge year, where the miss arrives all at once.

## The outlook moves when the charge is booked

In all {{large_misses}} large misses, the profit outlook did not come down until the release that reported the charge. Lockheed booked its 2025 losses in the second quarter and cut its outlook that day to ${{walk_LMT_2025_SegmentOP_Fcst_Q2}} million; the actual was ${{bridge_LMT_2025_actual_op}} million. Northrop booked its 2025 B-21 loss in the first quarter and cut to ${{walk_NOC_2025_SegmentOP_Fcst_Q1}} million; the actual was ${{bridge_NOC_2025_actual_op}} million. When the charge came in the fourth quarter there was no warning at all: Lockheed's October 2024 outlook was ${{walk_LMT_2024_SegmentOP_Fcst_Q3}} million, above its plan, and it reported ${{bridge_LMT_2024_actual_op}} million. Northrop held ${{walk_NOC_2023_SegmentOP_Fcst_Q3}} million through October 2023 and reported ${{bridge_NOC_2023_actual_op}} million. Across all years, the median miss on segment profit fell from {{err_SegmentOP_Plan_median_abs}} against the January plan to {{err_SegmentOP_Fcst_Q3_median_abs}} against the October update.

## What it means for a program finance team

At these companies the annual plan inherits its error from a few fixed-price development programs, and in these years the company outlook did not move until a program's estimate at completion did. That puts the early warning in program-level earned value. The repository pairs the public data with one synthetic program that walks through that mechanism: earned value slips, the composite EAC passes the contract price, and cost-to-cost revenue recognition books a reach-forward loss.

## Limits

Guidance is the public plan, not the internal budget. {{bridge_company_years}} bridge company-years is a small sample, so the findings describe these companies and years rather than estimate a rate. L3Harris published its guidance from early 2022 to late 2023 only as images, so those vintages are missing. RTX and L3Harris do not guide segment profit in dollars, so they count in the accuracy figures but not in the bridge. A program charge counts only when the filing ties at least {{charge_threshold}} of losses in a year to a named or described program.
