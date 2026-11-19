-- name: silver_consolidated_actuals
-- Company-level annual sales and operating profit (no dimensions), as first reported.
SELECT ticker, fiscal_year, account, value / 1000000.0 AS value_usd_m, accession, filing_date
FROM (
  SELECT ticker, fiscal_year, accession, filing_date, value,
         CASE WHEN concept = 'us-gaap:OperatingIncomeLoss' THEN 'ConsolidatedOP' ELSE 'Sales' END AS account,
         ROW_NUMBER() OVER (
           PARTITION BY ticker, fiscal_year,
                        CASE WHEN concept = 'us-gaap:OperatingIncomeLoss' THEN 'ConsolidatedOP' ELSE 'Sales' END
           ORDER BY filing_date, CASE WHEN concept = 'us-gaap:Revenues' THEN 0 ELSE 1 END, accession
         ) AS rn
  FROM bronze_facts
  WHERE form = '10-K'
    AND duration_days BETWEEN 350 AND 380
    AND is_current_period
    AND concept IN ('us-gaap:Revenues', 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
                    'us-gaap:OperatingIncomeLoss')
    AND n_dims = 0
) ranked
WHERE rn = 1
