-- name: gold_bridge
-- Plan-to-actual bridge for segment operating profit, one row per company-year with a Plan:
--   plan midpoint
--   + volume: (actual sales - plan sales midpoint) x plan margin (plan OP mid / plan sales mid)
--   - named program charges disclosed for the year
--   + other: everything not explained above (rates, mix, other EAC movement), never hidden
--   = actual.  The four steps sum to actual by construction; the test checks it independently.
WITH plan AS (
  SELECT ticker, fiscal_year,
         MAX(CASE WHEN account = 'Sales' THEN mid END) AS plan_sales,
         MAX(CASE WHEN account = 'SegmentOP' THEN mid END) AS plan_op
  FROM silver_guidance WHERE scenario = 'Plan' GROUP BY ticker, fiscal_year
), actual AS (
  SELECT ticker, fiscal_year,
         MAX(CASE WHEN account = 'Sales' THEN value_usd_m END) AS actual_sales,
         MAX(CASE WHEN account = 'SegmentOP' THEN value_usd_m END) AS actual_op
  FROM gold_cube WHERE scenario = 'Actual' AND entity = ticker GROUP BY ticker, fiscal_year
), charges AS (
  SELECT ticker, fiscal_year, SUM(amount_usd_m) AS charges FROM silver_charges GROUP BY ticker, fiscal_year
)
SELECT p.ticker, p.fiscal_year, p.plan_op, p.plan_sales, a.actual_sales,
       (a.actual_sales - p.plan_sales) * p.plan_op / p.plan_sales AS volume,
       -COALESCE(c.charges, 0) AS named_charges,
       a.actual_op - p.plan_op - (a.actual_sales - p.plan_sales) * p.plan_op / p.plan_sales
         + COALESCE(c.charges, 0) AS other,
       a.actual_op
FROM plan p
JOIN actual a ON a.ticker = p.ticker AND a.fiscal_year = p.fiscal_year
LEFT JOIN charges c ON c.ticker = p.ticker AND c.fiscal_year = p.fiscal_year
WHERE p.plan_op IS NOT NULL AND a.actual_op IS NOT NULL
