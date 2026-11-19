-- name: silver_eac
-- Disclosed EAC (profit booking rate) adjustment series, USD millions, sign as disclosed.
SELECT ticker, CAST(fiscal_year AS INT) AS fiscal_year, entity, metric AS account,
       CAST(value AS DOUBLE) AS value_usd_m, accession, document
FROM bronze_eac
