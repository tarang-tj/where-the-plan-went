-- name: silver_guidance
-- Guidance vintages (Plan = first annual outlook, Fcst_Q1..Q3 = later updates) and the Actual on
-- the same measure, typed and in USD millions (billions as printed are converted here).
-- Every row passed curation_contract and quote_check against the cached filing before upload.
SELECT ticker, CAST(fiscal_year AS INT) AS fiscal_year, vintage AS scenario,
       CAST(release_date AS DATE) AS release_date, accession, document, entity, metric AS account,
       basis, measure,
       TRY_CAST(low AS DOUBLE) * scale AS low,
       TRY_CAST(high AS DOUBLE) * scale AS high,
       (TRY_CAST(low AS DOUBLE) + TRY_CAST(high AS DOUBLE)) / 2.0 * scale AS mid,
       TRY_CAST(prior_low AS DOUBLE) * scale AS prior_low,
       TRY_CAST(prior_high AS DOUBLE) * scale AS prior_high,
       CASE WHEN unit = 'USD_per_share' THEN 'USD_per_share' ELSE 'USD_M' END AS unit
FROM (SELECT *, CASE WHEN unit = 'USD_B' THEN 1000.0 ELSE 1.0 END AS scale FROM bronze_guidance) g
