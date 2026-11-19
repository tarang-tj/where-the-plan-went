"""The Excel pack's formulas, evaluated by the `formulas` library, reproduce the gold CSVs.

openpyxl writes no cached values, so reading the saved cells would only return formula text.
"""
from pathlib import Path

import formulas
import pandas as pd
import pytest

from wtpw.export_xlsx import build

GOLD = Path("data/work/gold_local")
BOOK = "where-the-plan-went.xlsx"


@pytest.fixture(scope="module")
def cells(tmp_path_factory):
    path = build(out=tmp_path_factory.mktemp("xlsx") / BOOK)
    solution = formulas.ExcelModel().loads(str(path)).finish().calculate()

    def get(sheet, ref):
        return solution[f"'[{BOOK}]{sheet.upper()}'!{ref}"].value[0][0]
    return get


def test_bridge_formulas_match_gold(cells):
    gold = pd.read_csv(GOLD / "gold_bridge.csv")
    assert len(gold) > 0
    for r, b in enumerate(gold.itertuples(index=False), 2):
        assert (cells("Bridge", f"A{r}"), cells("Bridge", f"B{r}")) == (b.ticker, b.fiscal_year)
        assert abs(cells("Bridge", f"H{r}") - b.volume) < 1e-6, (b.ticker, b.fiscal_year, "volume")
        assert abs(cells("Bridge", f"I{r}") - b.other) < 1e-6, (b.ticker, b.fiscal_year, "other")
        assert abs(cells("Bridge", f"J{r}")) < 1e-6, (b.ticker, b.fiscal_year, "check")


def test_guidance_error_formulas_match_gold(cells):
    gold = pd.read_csv(GOLD / "gold_guidance_error.csv")
    assert len(gold) > 0
    for r, g in enumerate(gold.itertuples(index=False), 2):
        key = (g.ticker, g.fiscal_year, g.scenario, g.account, g.measure)
        assert (cells("Guidance", f"A{r}"), cells("Guidance", f"C{r}"), cells("Guidance", f"G{r}")) == \
            (g.ticker, g.scenario, g.measure), key
        assert abs(cells("Guidance", f"J{r}") - g.mid) < 1e-9, key
        assert abs(cells("Guidance", f"L{r}") - g.error_vs_mid) < 1e-9, key
        assert cells("Guidance", f"M{r}") == g.inside_range, key


def test_program_formulas_match_evm_csv(cells):
    evm = pd.read_csv("data/program/program_evm.csv")
    sheet = "Program (SYNTHETIC)"
    for r, p in enumerate(evm.itertuples(index=False), 2):
        # program_evm.csv is rounded to 3 decimals, so compare at that precision
        assert round(cells(sheet, f"H{r}"), 3) == pytest.approx(p.cpi, abs=1e-9), (p.month, "cpi")
        assert round(cells(sheet, f"I{r}"), 3) == pytest.approx(p.spi, abs=1e-9), (p.month, "spi")
        assert round(cells(sheet, f"J{r}"), 3) == pytest.approx(p.eac_composite, abs=1e-9), (p.month, "eac")


def test_eac_sheet_money_column_is_millions(tmp_path):
    """LMT 2018-2022 NetEAC is printed in billions; the $M column must hold 1,900 not 1.9."""
    import openpyxl

    from wtpw.export_xlsx import build
    path = tmp_path / "pack.xlsx"
    build(path)
    ws = openpyxl.load_workbook(path)["EAC"]
    head = [c.value for c in ws[1]]
    rows = [dict(zip(head, (c.value for c in r))) for r in ws.iter_rows(min_row=2)]
    lmt18 = next(r for r in rows if r["ticker"] == "LMT" and r["fiscal_year"] == 2018 and r["metric"] == "NetEAC")
    assert lmt18["unit"] == "USD_B" and lmt18["value_usd_m"] == 1900.0
