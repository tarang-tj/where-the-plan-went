-- name: gold_cube
-- OneStream-style cube in long form: Entity x Scenario x Account x Time, UD1 = program.
-- Actual Sales = consolidated; Actual SegmentOP = sum of reported segments (LMT's
-- "business segment operating profit"). Charges enter as negative ProgramCharge.
SELECT ticker, fiscal_year, entity, scenario, account, CAST(NULL AS STRING) AS ud1_program,
       mid AS value_usd_m, low, high, 'guidance' AS source, accession
FROM silver_guidance
UNION ALL
SELECT ticker, fiscal_year, ticker, 'Actual', account, CAST(NULL AS STRING),
       value_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'xbrl_consolidated', accession
FROM silver_consolidated_actuals WHERE account = 'Sales'
UNION ALL
SELECT ticker, fiscal_year, ticker, 'Actual', 'SegmentOP', CAST(NULL AS STRING),
       SUM(value_usd_m), CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'xbrl_segments', MIN(accession)
FROM silver_segment_actuals WHERE account = 'SegmentOP'
GROUP BY ticker, fiscal_year
UNION ALL
SELECT ticker, fiscal_year, ticker || '.' || entity, 'Actual', account, CAST(NULL AS STRING),
       value_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'xbrl_segments', accession
FROM silver_segment_actuals
UNION ALL
SELECT ticker, fiscal_year, ticker || '.' || segment, 'Actual', 'ProgramCharge', program,
       -amount_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'disclosure', accession
FROM silver_charges
UNION ALL
SELECT ticker, fiscal_year, entity, 'Actual', account, CAST(NULL AS STRING),
       value_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'disclosure', accession
FROM silver_eac
