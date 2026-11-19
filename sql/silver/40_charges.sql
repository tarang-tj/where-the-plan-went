-- name: silver_charges
-- Disclosed program charges (reach-forward losses), pre-tax, USD millions, positive = loss.
SELECT ticker, CAST(fiscal_year AS INT) AS fiscal_year, quarter, segment, program,
       CAST(amount AS DOUBLE) AS amount_usd_m, accession, document
FROM bronze_charges
