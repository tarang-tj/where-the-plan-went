-- name: silver_segment_actuals
-- Annual segment sales and operating profit from each year's ORIGINAL 10-K (the earliest 10-K
-- carrying segment facts for that year), taken as one set so renamed or resegmented members
-- (Space Systems -> Space; RTX, NOC, LHX reorganizations) are never mixed across filings.
-- Within that filing: a fact on the OperatingSegmentsMember context wins over a segment-only
-- context (RTX tags both: external vs including intersegment), and Revenues wins over
-- RevenueFromContractWithCustomer... when both are tagged.
WITH candidates AS (
  SELECT ticker, fiscal_year, segment_name, accession, filing_date, value, consolidation_item, concept,
         CASE WHEN concept = 'us-gaap:OperatingIncomeLoss' THEN 'SegmentOP' ELSE 'Sales' END AS account
  FROM bronze_facts
  WHERE form = '10-K'
    AND duration_days BETWEEN 350 AND 380
    AND is_current_period
    AND concept IN ('us-gaap:Revenues', 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
                    'us-gaap:OperatingIncomeLoss')
    AND segment IS NOT NULL
    -- Reconciling items some filers (UTC-era RTX) tag on the segment axis; not segments.
    AND segment_name NOT IN ('TotalSegments', 'EliminationsAndOther', 'GeneralCorporateExpenses',
                             'AcquisitionAccountingAdjustments', 'FASCASOperatingAdjustment')
    AND other_dims = 0
    AND (consolidation_item IS NULL OR consolidation_item = 'us-gaap:OperatingSegmentsMember')
), original AS (
  SELECT ticker, fiscal_year, accession
  FROM (
    SELECT ticker, fiscal_year, accession,
           ROW_NUMBER() OVER (PARTITION BY ticker, fiscal_year ORDER BY MIN(filing_date), accession) AS rn
    FROM candidates GROUP BY ticker, fiscal_year, accession
  ) f
  WHERE rn = 1
), ranked AS (
  SELECT c.*,
         ROW_NUMBER() OVER (
           PARTITION BY c.ticker, c.fiscal_year, c.segment_name, c.account
           ORDER BY CASE WHEN c.consolidation_item = 'us-gaap:OperatingSegmentsMember' THEN 0 ELSE 1 END,
                    CASE WHEN c.concept = 'us-gaap:Revenues' THEN 0 ELSE 1 END
         ) AS rn
  FROM candidates c
  JOIN original o ON o.ticker = c.ticker AND o.fiscal_year = c.fiscal_year AND o.accession = c.accession
)
SELECT ticker, fiscal_year, segment_name AS entity, account,
       value / 1000000.0 AS value_usd_m, accession, filing_date
FROM ranked
WHERE rn = 1
