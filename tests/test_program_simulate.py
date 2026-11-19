"""Invariants on the SYNTHETIC Program FPD-1 tables."""

import pandas as pd
import pytest

from wtpw.program import __main__ as cli
from wtpw.program import simulate as sim


@pytest.fixture(scope="module")
def tables():
    return sim.simulate()


def test_deterministic(tables):
    again = sim.simulate()
    for name, df in tables.items():
        pd.testing.assert_frame_equal(df, again[name])


def test_everything_labeled_synthetic(tables):
    for df in tables.values():
        assert set(df["source"]) == {"SYNTHETIC"}
    assert "synthetic" in sim.PROGRAM


def test_ledger_ties_to_ac(tables):
    ledger, evm_t = tables["ledger"], tables["evm"]
    per_month = ledger.groupby("month")["amount"].sum()
    increments = evm_t.set_index("month")["ac"].diff().fillna(evm_t["ac"].iloc[0])
    assert (per_month - increments).abs().max() < 1e-6
    assert ledger["amount"].sum() == pytest.approx(evm_t["ac"].iloc[-1], abs=1e-6)


def test_ledger_shape(tables):
    ledger = tables["ledger"]
    assert set(ledger["project"]) == {"FPD1.01", "FPD1.02", "FPD1.03"}
    assert set(ledger["account"]) == {"DirectLabor", "Material", "Subcontract", "Fringe", "Overhead", "GA"}
    assert ledger["month"].between(1, 36).all()


def test_plan_and_completion(tables):
    evm_t = tables["evm"]
    assert len(evm_t) == 36
    assert evm_t["pv"].iloc[-1] == pytest.approx(sim.BAC)
    assert evm_t["ev"].iloc[-1] == pytest.approx(sim.BAC)
    assert evm_t["eac_composite"].iloc[-1] == pytest.approx(evm_t["ac"].iloc[-1])


def test_loss_triggers_at_rework(tables):
    rr = tables["revrec"]
    before = rr[rr["month"] < sim.REWORK_START]
    after = rr[rr["month"] >= sim.REWORK_START]
    assert (before["eac"] <= sim.PRICE).all()
    assert (after["eac"] > sim.PRICE).all()
    assert rr.loc[rr["month"] == sim.REWORK_START, "loss_provision_period"].iloc[0] > 0


def test_no_margin_after_loss(tables):
    rr = tables["revrec"]
    after = rr[rr["month"] >= sim.REWORK_START]
    assert (after["cum_gross_profit"] < 0).all()
    expected = -(after["eac"] - sim.PRICE)
    assert (after["cum_gross_profit"] - expected).abs().max() < 2e-3  # 3-decimal rounding


def test_revenue_bounds_and_sums(tables):
    rr = tables["revrec"]
    assert (rr["cum_revenue"] <= sim.PRICE + 1e-9).all()
    assert rr["cum_revenue"].iloc[-1] == pytest.approx(sim.PRICE)
    assert rr["period_revenue"].sum() == pytest.approx(sim.PRICE, abs=5e-3)


def test_cli_writes_three_csvs(tmp_path, capsys):
    assert cli.main(["--out", str(tmp_path)]) == 0
    for name in ("ledger", "evm", "revrec"):
        df = pd.read_csv(tmp_path / f"program_{name}.csv")
        assert len(df) > 0
    assert "SYNTHETIC" in capsys.readouterr().out
