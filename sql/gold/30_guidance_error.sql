-- name: gold_guidance_error
-- How far each guidance vintage landed from the actual on the same measure and basis:
-- actual / midpoint - 1, and whether the actual fell inside the guided range. A vintage is scored
-- only against an Actual printed under the same measure label (NOC 2021 Plan "mtm-adjusted eps" is
-- not scored against a transaction-adjusted actual).
SELECT g.ticker, g.fiscal_year, g.scenario, g.release_date, g.account, g.basis, g.measure,
       g.low, g.high, g.mid, a.mid AS actual,
       a.mid / g.mid - 1 AS error_vs_mid,
       CASE WHEN a.mid BETWEEN g.low AND g.high THEN 1 ELSE 0 END AS inside_range
FROM silver_guidance g
JOIN silver_guidance a
  ON a.ticker = g.ticker AND a.fiscal_year = g.fiscal_year AND a.entity = g.entity
 AND a.account = g.account AND a.basis = g.basis AND a.measure = g.measure AND a.scenario = 'Actual'
WHERE g.scenario <> 'Actual'
