"""Excel FP&A pack from the gold tables: bridge, guidance error, cube, curated EAC and charges, program EVM.

Usage: python -m wtpw.export_xlsx   -> outputs/where-the-plan-went.xlsx
Inputs are written as values and derived columns as formulas (volume, other, check, mid, error,
inside, CPI, SPI, EAC). tests/test_export_xlsx.py evaluates those formulas against the CSVs.
"""
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from wtpw.xlsx_sheets import (
    BOLD,
    FONT,
    MONEY,
    bridge_sheet,
    guidance_sheet,
    link_column,
    program_sheet,
    sec_url,
    table_sheet,
)

GOLD = Path("data/work/gold_local")
OUT = Path("outputs/where-the-plan-went.xlsx")


def _curated(curated: Path, kind: str) -> pd.DataFrame:
    return pd.concat([pd.read_csv(p) for p in sorted(curated.glob(f"{kind}_*.csv"))], ignore_index=True)


def readme(wb):
    ws = wb.active
    ws.title = "README"
    lines = [
        "Where the plan went: defense-prime guidance vs actual, from SEC filings",
        "Amounts are $M unless the metric is EPS ($ per share). Every number outside the Program sheet traces to an SEC filing.",
        "",
        "Sheets",
        "Bridge: plan segment operating profit to actual, per company-year. Inputs are values; volume, other",
        "  and check are formulas. volume = (actual_sales - plan_sales) * plan_op / plan_sales;",
        "  other = actual_op - plan_op - volume - named_charges (charges negative); check must be 0.",
        "Guidance: every guidance vintage (Plan, Fcst_Q1..Q3) scored against the actual on the same measure",
        "  and basis. mid, error_vs_mid = actual / mid - 1 and inside_range are formulas. sec_filing links the release.",
        "Cube: gold_cube as a flat Excel table with filters (insert a PivotTable on it).",
        "EAC: curated net, favorable and unfavorable EAC adjustments with the filing quote and link.",
        "Charges: curated named program charges with the filing quote and link.",
        "Program (SYNTHETIC): Program FPD-1 is SYNTHETIC. It is invented by src/wtpw/program and is not a real",
        "  program, company or contract. PV, EV, AC, BAC are values; CPI, SPI and composite EAC are formulas.",
        "Sources: filing counts by company and form, and how to reproduce this workbook.",
        "",
        "Data: SEC EDGAR 10-K, 10-Q and 8-K earnings releases (XBRL facts plus hand-curated release text).",
        "",
        "Gates (make gate): ruff, pytest, curation contract, quote check (every curated quote and its numbers are",
        "  found in the cached filing), reconcile (tie-breaks, segment sums, guidance chain, release actuals vs XBRL",
        "  within 0.5%), findings. tests/test_export_xlsx.py evaluates this",
        "  workbook's formulas and checks them against the gold CSVs and program_evm.csv.",
    ]
    for i, t in enumerate(lines, 1):
        ws.cell(i, 1, t).font = BOLD if i in (1, 4) else FONT
    ws.column_dimensions["A"].width = 110


def curated_sheet(wb, title, df, money_col):
    cols = [c for c in df.columns if c != "cik"]
    ws = table_sheet(wb, title, cols, df[cols].itertuples(index=False), {money_col: MONEY},
                     {"quote": 100, "accession": 24, "document": 26, "program": 32, "segment": 22})
    link_column(ws, cols.index("accession") + 1,
                [sec_url(c, a, d) for c, a, d in df[["cik", "accession", "document"]].itertuples(index=False)])
    return ws


def cube_sheet(wb, cube):
    ws = table_sheet(wb, "Cube", list(cube.columns), cube.itertuples(index=False),
                     {"value_usd_m": "#,##0.00", "low": "#,##0.00", "high": "#,##0.00"}, {"accession": 24})
    tab = Table(displayName="GoldCube", ref=ws.dimensions)
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
    ws.add_table(tab)
    return ws


def sources_sheet(wb, filings: pd.DataFrame, manifest: Path):
    counts = filings.groupby(["ticker", "form"]).size().reset_index(name="filings")
    rows = list(counts.itertuples(index=False)) + [("All", "All", len(filings))]
    ws = table_sheet(wb, "Sources", ["ticker", "form", "filings"], rows, {"filings": MONEY})
    notes = [
        "Filings indexed in data/work/filings.csv (EDGAR submissions JSON).",
        f"Raw downloads in data/raw/manifest.jsonl: {_lines(manifest)} files, each with URL, sha256 and fetch time.",
        "Reproduce:",
        "  SEC_UA='name email' make fetch facts   (networked, cached once)",
        "  make program local findings            (synthetic program, DuckDB medallion, numbers.csv)",
        "  make xlsx                              (this workbook)",
    ]
    for i, t in enumerate(notes, 1):
        ws.cell(i, 5, t).font = BOLD if i == 3 else FONT
    ws.column_dimensions["E"].width = 90
    return ws


def _lines(path: Path) -> str:
    if not path.exists():
        return "not present"
    return str(sum(1 for line in path.read_text().splitlines() if line.strip()))


def build(out: Path = OUT, gold: Path = GOLD, curated: Path = Path("curated"),
          program: Path = Path("data/program"), work: Path = Path("data/work"),
          manifest: Path = Path("data/raw/manifest.jsonl")) -> Path:
    wb = Workbook()
    readme(wb)
    bridge_sheet(wb, pd.read_csv(gold / "gold_bridge.csv"))
    links = (_curated(curated, "guidance").rename(columns={"vintage": "scenario", "metric": "account"})
             [["ticker", "fiscal_year", "scenario", "release_date", "account", "basis", "measure",
               "cik", "accession", "document"]])
    guidance_sheet(wb, pd.read_csv(gold / "gold_guidance_error.csv"), links)
    cube_sheet(wb, pd.read_csv(gold / "gold_cube.csv"))
    eac = _curated(curated, "eac")
    # The curated value is as printed (some LMT years in billions); the sheet's money column is $M.
    eac.insert(eac.columns.get_loc("value") + 1, "value_usd_m",
               eac["value"].astype(float) * eac["unit"].map({"USD_B": 1000.0, "USD_M": 1.0}))
    if eac["value_usd_m"].isna().any():
        raise ValueError("EAC row with a unit other than USD_M or USD_B")
    curated_sheet(wb, "EAC", eac, "value_usd_m")
    curated_sheet(wb, "Charges", _curated(curated, "charges"), "amount")
    program_sheet(wb, pd.read_csv(program / "program_evm.csv"))
    sources_sheet(wb, pd.read_csv(work / "filings.csv"), manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Pin document timestamps so an unchanged build writes a byte-identical workbook.
    stamp = datetime(2026, 1, 1)
    wb.properties.created = wb.properties.modified = stamp
    wb.save(out)
    return out


def main() -> None:
    print(f"wrote {build()}")


if __name__ == "__main__":
    main()
