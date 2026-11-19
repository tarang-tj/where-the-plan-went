-- name: gold_cube
-- OneStream-style cube in long form: Entity x Scenario x Account x Time, UD1 = program, UD2 = basis.
-- Scenarios: Plan, Fcst_Q1..Q3, Actual (as reported in the year-end release, same measure as the
-- guidance) and Actual_XBRL (as tagged in the 10-K; segment drill-down and the cross-check).
-- Program charges enter as negative ProgramCharge; EAC series as disclosed.
SELECT ticker, fiscal_year, entity, scenario, account, CAST(NULL AS STRING) AS ud1_program,
       basis AS ud2_basis, mid AS value_usd_m, low, high, 'release' AS source, accession
FROM silver_guidance
UNION ALL
SELECT ticker, fiscal_year, ticker, 'Actual_XBRL', account, CAST(NULL AS STRING), 'GAAP',
       value_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'xbrl_consolidated', accession
FROM silver_consolidated_actuals WHERE account = 'Sales'
UNION ALL
SELECT ticker, fiscal_year, ticker, 'Actual_XBRL', 'SegmentOP', CAST(NULL AS STRING), method,
       segment_op_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'xbrl_segments', accession
FROM silver_segment_totals
UNION ALL
SELECT ticker, fiscal_year, ticker || '.' || entity, 'Actual_XBRL', account, CAST(NULL AS STRING), 'GAAP',
       value_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'xbrl_segments', accession
FROM silver_segment_actuals
UNION ALL
SELECT ticker, fiscal_year, ticker || '.' || segment, 'Actual', 'ProgramCharge', program, 'disclosed',
       -amount_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'disclosure', accession
FROM silver_charges
UNION ALL
SELECT ticker, fiscal_year, entity, 'Actual', account, CAST(NULL AS STRING), 'disclosed',
       value_usd_m, CAST(NULL AS DOUBLE), CAST(NULL AS DOUBLE), 'disclosure', accession
FROM silver_eac
