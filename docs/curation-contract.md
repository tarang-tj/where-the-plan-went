# Curation contract

Three numbers in this project cannot come from XBRL: what each company guided, the EAC (profit booking rate) adjustment totals, and the named program charges. They are copied by hand from the filings into `curated/`, and two gates keep that copying honest:

- `python -m wtpw.curation_contract` checks the header, the allowed values and duplicate keys.
- `python -m wtpw.quote_check` reloads each cited filing from the local cache and fails unless the row's quote appears in it word for word and every number in the row is printed inside that quote.

Nothing here is estimated, interpolated or carried forward. If a filing does not print a number, the row does not exist, and the gap is listed in the coverage notes.

## Files

One file per kind and company: `curated/guidance_<TICKER>.csv`, `curated/charges_<TICKER>.csv`, `curated/eac_<TICKER>.csv`. Headers are fixed (see `src/wtpw/curation_contract.py`).

## Guidance (`guidance_<TICKER>.csv`)

| Column | Rule |
|---|---|
| `fiscal_year` | The year the outlook is for. |
| `vintage` | `Plan`: the first numeric outlook for that year, normally in the fourth-quarter release of the prior year (January or February). `Fcst_Q1`, `Fcst_Q2`, `Fcst_Q3`: the outlook printed in that year's first, second and third quarter releases. `Actual`: the full-year result from the next fourth-quarter release, on the same measure as the guidance. |
| `release_date`, `accession`, `document` | The 8-K (Item 2.02) and its Exhibit 99.1 file name, from `data/work/filings.csv`. |
| `entity` | The ticker for company totals. |
| `metric` | `Sales`, `SegmentOP` (total segment operating profit or income, in dollars), `EPS`, `FCF`. Margins and percentages are out of scope. |
| `basis`, `measure` | `GAAP` or `non-GAAP`, and the company's own label in lower case ("net sales", "adjusted sales", "mtm-adjusted eps", "business segment operating profit"). |
| `low`, `high` | The range as printed. A point estimate ("~$6,600") has low = high. Verbal ranges ("low $13 billion", "mid to high single digits") are not recorded. |
| `unit` | `USD_M`, `USD_B` (as printed, e.g. "$86.5 - $87.0 billion"), or `USD_per_share`. Silver converts billions to millions. |
| `prior_low`, `prior_high` | Only when the same table prints the previous outlook beside the current one. Used for the chain check (an update's printed prior must equal the earlier vintage). |
| `quote` | Contiguous text from the filing as returned by `wtpw.quote_check.filing_text()` (lower case, tags removed, spaces collapsed). At least 12 characters, and it must contain every number in the row. |

## EAC adjustments (`eac_<TICKER>.csv`)

`metric` is `NetEAC`, `FavEAC` or `UnfavEAC`, in USD millions, signed so that positive means the adjustment increased operating income. `entity` is the ticker or `<TICKER>.<Segment>`. Source: that year's 10-K, or a later 10-K when it restates the year (cite the one you quote).

## Program charges (`charges_<TICKER>.csv`)

A pre-tax loss of at least $100 million that the filing attributes to a named or described program (reach-forward losses, loss provisions on a specific contract). `amount` is positive for a loss. `quarter` is the quarter the filing says the loss was recognized, or `FY` when only the annual amount is stated. `basis` is `reach-forward loss` when the filing uses that term, otherwise `charge`.

## Coverage notes

Each company's curator lists, per fiscal year and vintage, what was found and what the filings do not provide (for example "GD: guidance given on the call only, not in the release").
