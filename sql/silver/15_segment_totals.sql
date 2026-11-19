-- name: silver_segment_totals
-- Total segment operating income per company-year, from the year's own 10-K. When the filer tags
-- the total itself (OperatingSegmentsMember with no segment member, e.g. NOC after intersegment
-- profit eliminations) that figure is used; otherwise the reported segments are summed (LMT).
-- NOC tags its elimination as a POSITIVE fact that the filing subtracts, so it is never added.
WITH tagged AS (
  SELECT ticker, fiscal_year, MIN(value) / 1000000.0 AS total_usd_m, MIN(accession) AS accession
  FROM bronze_facts
  WHERE form = '10-K' AND is_current_period AND duration_days BETWEEN 350 AND 380
    AND concept = 'us-gaap:OperatingIncomeLoss'
    AND consolidation_item = 'us-gaap:OperatingSegmentsMember'
    AND segment IS NULL AND other_dims = 0
  GROUP BY ticker, fiscal_year
), summed AS (
  SELECT ticker, fiscal_year, SUM(value_usd_m) AS total_usd_m, MIN(accession) AS accession
  FROM silver_segment_actuals WHERE account = 'SegmentOP'
  GROUP BY ticker, fiscal_year
)
SELECT s.ticker, s.fiscal_year,
       COALESCE(t.total_usd_m, s.total_usd_m) AS segment_op_usd_m,
       CASE WHEN t.total_usd_m IS NOT NULL THEN 'tagged_total' ELSE 'sum_of_segments' END AS method,
       COALESCE(t.accession, s.accession) AS accession
FROM summed s LEFT JOIN tagged t ON t.ticker = s.ticker AND t.fiscal_year = s.fiscal_year
