"""Sheet writers for the Excel FP&A pack: shared formatting plus the three formula sheets.

Inputs go in as values; every derived column is an Excel formula so the workbook recalculates
on open. tests/test_export_xlsx.py evaluates the formulas with the `formulas` library.
"""
import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

FONT, BOLD = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
LINK = Font(name="Arial", size=10, underline="single")
HEAD_FILL = PatternFill("solid", fgColor="DDE3EA")
MONEY, PCT, EPS, RATIO = "#,##0", "0.0%", "0.00", "0.000"
EDGAR = "https://www.sec.gov/Archives/edgar/data/{cik}/{folder}/{doc}"


def sec_url(cik, accession, document) -> str:
    return EDGAR.format(cik=int(cik), folder=str(accession).replace("-", ""), doc=document)


def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA:
        return None
    return v.item() if hasattr(v, "item") else v


def table_sheet(wb, title, header, rows, formats=None, widths=None):
    """Write header + rows (cells may be values or '=formulas'); format, freeze, size. Returns ws."""
    ws = wb.create_sheet(title)
    ws.append(header)
    for c in ws[1]:
        c.font, c.fill = BOLD, HEAD_FILL
    for row in rows:
        ws.append([_clean(v) for v in row])
    formats, widths = formats or {}, widths or {}
    for i, name in enumerate(header, 1):
        col = get_column_letter(i)
        for cell in ws[col][1:]:
            cell.font = FONT
            if name in formats:
                cell.number_format = formats[name]
        ws.column_dimensions[col].width = widths.get(name, max(10, min(40, len(name) + 4)))
    ws.freeze_panes = "A2"
    return ws


def link_column(ws, col_idx, urls):
    """Turn column col_idx (1-based) of data rows into SEC hyperlinks."""
    for r, url in enumerate(urls, 2):
        cell = ws.cell(r, col_idx)
        cell.hyperlink, cell.font = url, LINK


def bridge_sheet(wb, bridge: pd.DataFrame):
    header = ["ticker", "fiscal_year", "plan_sales", "plan_op", "actual_sales", "actual_op",
              "named_charges", "volume", "other", "check"]
    rows = []
    for r, b in enumerate(bridge.itertuples(index=False), 2):
        rows.append([b.ticker, b.fiscal_year, b.plan_sales, b.plan_op, b.actual_sales, b.actual_op,
                     b.named_charges,
                     f"=(E{r}-C{r})*D{r}/C{r}",
                     f"=F{r}-D{r}-H{r}-G{r}",
                     f"=D{r}+H{r}+G{r}+I{r}-F{r}"])
    fmt = {k: MONEY for k in header[2:]}
    return table_sheet(wb, "Bridge", header, rows, fmt)


def guidance_sheet(wb, err: pd.DataFrame, links: pd.DataFrame):
    header = ["ticker", "fiscal_year", "scenario", "release_date", "metric", "basis", "measure",
              "low", "high", "mid", "actual", "error_vs_mid", "inside_range", "sec_filing"]
    keys = ["ticker", "fiscal_year", "scenario", "release_date", "account", "basis", "measure"]
    m = err.merge(links, on=keys, how="left", validate="one_to_one")
    if m["accession"].isna().any():
        raise ValueError("guidance rows without a curated SEC source")
    rows = []
    for r, g in enumerate(m.itertuples(index=False), 2):
        rows.append([g.ticker, g.fiscal_year, g.scenario, g.release_date, g.account, g.basis, g.measure,
                     g.low, g.high, f"=(H{r}+I{r})/2", g.actual, f"=K{r}/J{r}-1",
                     f"=IF(AND(K{r}>=H{r},K{r}<=I{r}),1,0)", g.accession])
    ws = table_sheet(wb, "Guidance", header, rows, {"error_vs_mid": PCT},
                     {"measure": 36, "sec_filing": 24, "release_date": 13})
    for r, g in enumerate(m.itertuples(index=False), 2):
        fmt = EPS if g.account == "EPS" else MONEY
        for col in "HIJK":
            ws[f"{col}{r}"].number_format = fmt
    link_column(ws, 14, [sec_url(c, a, d) for c, a, d in m[["cik", "accession", "document"]].itertuples(index=False)])
    return ws


def program_sheet(wb, evm: pd.DataFrame):
    header = ["month", "period", "program", "pv", "ev", "ac", "bac", "cpi", "spi", "eac_composite", "source"]
    rows = []
    for r, p in enumerate(evm.itertuples(index=False), 2):
        rows.append([p.month, p.period, p.program, p.pv, p.ev, p.ac, p.bac,
                     f"=E{r}/F{r}", f"=E{r}/D{r}", f"=F{r}+(G{r}-E{r})/(H{r}*I{r})", p.source])
    fmt = {"pv": "#,##0.000", "ev": "#,##0.000", "ac": "#,##0.000", "bac": "#,##0.000",
           "cpi": RATIO, "spi": RATIO, "eac_composite": "#,##0.000"}
    return table_sheet(wb, "Program (SYNTHETIC)", header, rows, fmt, {"program": 28})
