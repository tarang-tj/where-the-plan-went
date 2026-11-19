-- name: silver_guidance
-- Guidance vintages (Plan = first annual outlook, Fcst_Q1..Q3 = later updates) and the Actual on
-- the same measure, typed and in USD millions (billions as printed are converted here).
-- Every row passed curation_contract and quote_check against the cached filing before upload.
-- measure_family joins labels that name the same measure (reference/measure_families.csv, each
-- with a reason); any label not listed is its own family, so different measures never mix.
SELECT g.ticker, CAST(g.fiscal_year AS INT) AS fiscal_year, g.vintage AS scenario,
       CAST(g.release_date AS DATE) AS release_date, g.accession, g.document, g.entity,
       g.metric AS account, g.basis, g.measure, COALESCE(f.family, g.measure) AS measure_family,
       TRY_CAST(g.low AS DOUBLE) * g.scale AS low,
       TRY_CAST(g.high AS DOUBLE) * g.scale AS high,
       (TRY_CAST(g.low AS DOUBLE) + TRY_CAST(g.high AS DOUBLE)) / 2.0 * g.scale AS mid,
       TRY_CAST(g.prior_low AS DOUBLE) * g.scale AS prior_low,
       TRY_CAST(g.prior_high AS DOUBLE) * g.scale AS prior_high,
       CASE WHEN g.unit = 'USD_per_share' THEN 'USD_per_share' ELSE 'USD_M' END AS unit
FROM (SELECT *, CASE WHEN unit = 'USD_B' THEN 1000.0 ELSE 1.0 END AS scale FROM bronze_guidance) g
LEFT JOIN bronze_measure_families f ON f.ticker = g.ticker AND f.measure = g.measure
