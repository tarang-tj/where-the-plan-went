-- name: silver_guidance
-- Guidance vintages (Plan = first annual outlook, Fcst_Q1..Q3 = later updates), typed.
-- Every row passed quote_check against the cached filing before upload.
SELECT ticker, CAST(fiscal_year AS INT) AS fiscal_year, vintage AS scenario,
       CAST(release_date AS DATE) AS release_date, accession, document, entity, metric AS account, basis,
       CAST(low AS DOUBLE) AS low, CAST(high AS DOUBLE) AS high,
       (CAST(low AS DOUBLE) + CAST(high AS DOUBLE)) / 2.0 AS mid, unit
FROM bronze_guidance
