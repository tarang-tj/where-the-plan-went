# Enterprise crosswalk

This project runs on Databricks. The finance teams it imitates run planning in tools like OneStream, accounting in Deltek Costpoint, and ERP in Microsoft Dynamics 365 Finance. This page maps each piece of the model here to the structure those tools use for the same job, taken from their public documentation. It is a reading of the documentation, not experience operating those systems.

## The plan-versus-actual cube

| In this project | OneStream | What it means |
|---|---|---|
| `gold_cube.entity` (company, company.segment) | Entity dimension | Who the number belongs to; segments roll up to the company. |
| `gold_cube.scenario` (Plan, Fcst_Q1..Q3, Actual, Actual_XBRL) | Scenario dimension | Separate data sets for plan, forecast and actual. OneStream scenarios "do not consolidate" into each other, which is why the variance is computed, not summed. |
| `gold_cube.account` (Sales, SegmentOP, EPS, FCF, ProgramCharge, NetEAC) | Account dimension (Revenue, Expense, Flow, NonFinancial and other types) | The line item. A per-share figure like EPS would fit the NonFinancial type (a modeling choice, not a documented rule). |
| `gold_cube.fiscal_year` | Time dimension | Annual here; OneStream supports monthly to yearly input frequency. |
| `gold_cube.ud1_program`, `ud2_basis` | User Defined dimensions UD1 to UD8 | Extra analysis axes. Here: the program behind a charge, and GAAP versus non-GAAP. |

Source: OneStream documentation, Cube > Dimensions Overview, Scenario Dimension, Account Dimension, User Defined Dimensions (documentation.onestream.com).

## The program ledger (synthetic program FPD-1)

| In this project | Deltek Costpoint | What it means |
|---|---|---|
| `program_ledger.project` (FPD1.01, .02, .03) | Project, with work breakdown levels | Costs are charged to a project at the lowest level and roll up. |
| `program_ledger.org` | Organization | The performing department. |
| `program_ledger.account` (DirectLabor, Material, Subcontract, Fringe, Overhead, GA) | Account; PROJ_ORG_ACCT validation | Every charge is a valid project x organization x account combination. |
| `wtpw.program.indirect` YTD rates | Indirect rate computation: pools, allocation groups | Year-to-date rate = pool cost / pool base; each period allocates rate x base less what was already allocated. |
| EAC by WBS in `program_evm` | ETC entry by project, organization and account | The estimate to complete that drives the estimate at completion. |

Source: Deltek Costpoint online help, Indirect Rate Computation (7.1.1) and Projects domain (8.1, 8.2) (help.deltek.com).

## Revenue recognition and the account string

| In this project | Dynamics 365 Finance | What it means |
|---|---|---|
| `program_revrec.pct_complete` = cumulative cost / EAC | Project cost template, completion based on Amount | Percent complete measured by cost, the method behind cumulative catch-up. |
| `catch_up` and `loss_provision_*` | Revenue recognition (formerly "estimate") on fixed-price projects | Estimate changes book a catch-up; a loss contract books the loss when it is foreseen. |
| `entity` + `account` + `ud1_program` + `ud2_basis` | Main account + financial dimensions under an account structure | One ledger string per combination. |

Source: Microsoft Learn, Dynamics 365 Project Operations revenue recognition cost templates and percentage-of-completion pages; Dynamics 365 Finance financial dimensions and ledger pages (learn.microsoft.com).

## What the platform does here that a planning tool also does

- Medallion layers (bronze as filed, silver typed and keyed, gold for analysis) follow Databricks' published pattern (docs.databricks.com, lakehouse/medallion).
- Control totals before analysis: segments less eliminations tie to the consolidated figure, release actuals tie to the 10-K, and every hand-entered number cites the filing sentence it came from. These are the same tie-outs a close or a consolidation runs.
