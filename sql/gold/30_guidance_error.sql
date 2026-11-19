-- name: gold_guidance_error
-- How far each guidance vintage landed from the actual: actual / midpoint - 1, and whether the
-- actual fell inside the guided range.
SELECT g.ticker, g.fiscal_year, g.scenario, g.release_date, g.account, g.low, g.high, g.mid,
       a.value_usd_m AS actual,
       a.value_usd_m / g.mid - 1 AS error_vs_mid,
       CASE WHEN a.value_usd_m BETWEEN g.low AND g.high THEN 1 ELSE 0 END AS inside_range
FROM silver_guidance g
JOIN gold_cube a ON a.ticker = g.ticker AND a.fiscal_year = g.fiscal_year AND a.entity = g.ticker
                AND a.account = g.account AND a.scenario = 'Actual'
