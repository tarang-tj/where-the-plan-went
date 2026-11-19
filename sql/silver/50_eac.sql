-- name: silver_eac
-- Disclosed EAC (profit booking rate) adjustment series in USD millions (billions as printed are
-- converted), signed so positive = increased operating income.
SELECT ticker, CAST(fiscal_year AS INT) AS fiscal_year, entity, metric AS account,
       CAST(value AS DOUBLE) * CASE WHEN unit = 'USD_B' THEN 1000.0 ELSE 1.0 END AS value_usd_m,
       accession, document
FROM bronze_eac
