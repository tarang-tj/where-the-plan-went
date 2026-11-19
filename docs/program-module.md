# Program module: Program FPD-1 (synthetic)

**Program FPD-1 is synthetic.** Every number in `data/program/` is invented by
`src/wtpw/program/simulate.py` with fixed rules and no randomness. It is not drawn from
any real program, company, contract, or filing, and every row carries `source = SYNTHETIC`.
The purpose is to show how monthly cost data on a fixed-price development contract flows
through earned value to an estimate at completion (EAC), then into cost-to-cost revenue
and a reach-forward loss.

Run `python -m wtpw.program` to write the three tables. Amounts are $M, 3 decimals.

## The program

A 36-month fixed-price development contract, transaction price 520, initial budget at
completion (BAC) 480 fully burdened, with work planned on an S-curve. Through month 19 the
program runs slightly over cost (CPI about 0.97) and slightly behind (SPI 0.98). In month 20
a design rework on FPD1.02 starts: it adds cost that earns no value for eight months and
slows the schedule. The composite EAC jumps from about 500 to about 525, above the price,
and a reach-forward loss is booked in month 20. The program finishes at a cost of 534.864,
a loss of 14.864.

## The tables

**`program_ledger.csv`** is the cost ledger, one row per period, project, org and account,
in the shape a Costpoint labor and cost distribution would take. Projects are the WBS
elements FPD1.01 (systems engineering), FPD1.02 (hardware design) and FPD1.03 (integration
and test). Direct accounts are DirectLabor, Material and Subcontract; burden accounts are
Fringe, Overhead and GA. An analyst uses this table to answer "where did the money go"
and to reconcile the ledger to the EVM actuals: the ledger sum for each month equals the
monthly change in AC exactly, which the tests check.

**`program_evm.csv`** is the monthly EVM status: PV, EV, AC, BAC, CPI, SPI, CV, SV, the
three EAC forms, ETC, VAC and TCPI, using the NSF EVM Gold Card formulas
(https://www.nsf.gov/od/ori/evm-gold-card). EAC = BAC / CPI and EAC = AC + (BAC - EV) / CPI
are algebraically the same number, so their columns match; the composite form, which also
divides by SPI, is the one this module uses as the current estimate. TCPI is blank in month
36 because no work is left and the index is undefined. An analyst reads this table to see
when the trend broke (month 20) and how far the independent estimates sit from the budget.

**`program_revrec.csv`** is revenue under the cost-to-cost input method (ASC 606-10-25-31,
measure of progress). Percent complete is cumulative cost over the current EAC, capped at 1;
cumulative revenue is that percent times the price. `catch_up` is the part of the period
revenue caused by the estimate change alone: revenue at the new EAC minus revenue at the
prior EAC for the same cumulative cost. It is zero when the EAC does not move. When the EAC
exceeds the price, the full expected loss is recognized at once (ASC 605-35-25-46, loss
provisions). Part of that loss is already inside revenue minus cost to date; the
`loss_provision_balance` holds the rest, so cumulative gross profit equals minus
(EAC - price) from month 20 on and never shows a margin. As later costs are incurred the
provision is used up, which is why `loss_provision_period` turns negative after month 26.

## Indirect rates, Costpoint style

The burden lines come from three company pools computed the way Deltek Costpoint describes
(https://help.deltek.com/Product/Costpoint/7.1.1/GA/pjx_Indirect_Rate_Computation.html):
fringe and overhead on a direct labor base, and G&A on a total cost input base (direct
labor, material, subcontract, fringe and overhead). The YTD rate is YTD pool cost over YTD
pool base. Each period a project gets the YTD rate times its YTD base, minus what it was
already allocated year to date. When the rate moves, this method trues up earlier months
inside the current period, which is the catch-up. The base includes other company projects,
so FPD-1 absorbs only its share of each pool. YTD totals reset each fiscal year.

## How this maps to the systems

- **Costpoint.** The ledger key is project x org x account, the same validation structure
  Costpoint uses, and the indirect pools follow its YTD rate computation above. ETC by
  project, org and account would sit alongside these rows.
- **D365 Finance.** Project cost templates with Amount-based completion compute percent
  complete from cost amounts, which matches the cost-to-cost logic in `revrec.py`. Source:
  Microsoft Learn, revenue recognition cost templates (learn.microsoft.com, page
  rev-rec-cost-templates).
- **OneStream.** The EVM and revrec tables separate an Actual view (AC, cost incurred) from
  an estimate view (EAC). In OneStream these would be different members of the Scenario
  dimension, Actual and an EAC or Forecast scenario, which do not consolidate into each
  other. Source: OneStream documentation, Dimensions Overview and Scenario Dimension
  (documentation.onestream.com).

## Limits

This is a teaching model. The EAC here is a formula, where a real program would use a
bottom-up management EAC reviewed each quarter. There are no fee, award, or
contract-modification mechanics, and no cost-accounting-standards or FAR allowability logic.
