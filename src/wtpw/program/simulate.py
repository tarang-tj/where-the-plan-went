"""Deterministic simulation of "Program FPD-1 (synthetic)", a fixed-price development program.

SYNTHETIC DATA. Every number here is invented for illustration. Nothing is drawn from a
real program, company, or filing. No randomness is used: the same code gives the same tables.

Shape: 36 months, transaction price 520 ($M), initial BAC 480 ($M, fully burdened),
plan on an S-curve. A design-rework event starting in month 20 adds cost on FPD1.02 and
slows earned value, so the composite EAC passes the price and a reach-forward loss is booked.
"""

from __future__ import annotations

import pandas as pd

from wtpw.program import evm, indirect, revrec

SOURCE = "SYNTHETIC"
PROGRAM = "Program FPD-1 (synthetic)"
MONTHS, PRICE, BAC, START_YEAR = 36, 520.0, 480.0, 2024
REWORK_START, REWORK_END, REWORK_PER_MONTH = 20, 27, 5.0  # burdened $M on FPD1.02
PLAN_CPI = 0.97
PLAN_RATES = {"Fringe": 0.30, "Overhead": 0.70, "GA": 0.12}
# Deterministic month-to-month swings in company pool spending, so YTD rates move.
WIGGLE = {"Fringe": (1.03, 0.98, 1.01, 0.98), "Overhead": (0.97, 1.04, 0.99, 1.00), "GA": (1.02, 0.99, 0.98, 1.01)}
OTHER_DL, OTHER_NONLABOR = 6.0, 5.0  # other projects in the company base, $M per month
WBS_SHARE = {"FPD1.01": 0.25, "FPD1.02": 0.50, "FPD1.03": 0.25}
LABOR_ORG = {"FPD1.01": "1.10.SE", "FPD1.02": "1.20.HW", "FPD1.03": "1.30.IT"}
SCM_ORG = "1.40.SCM"
MIX = {"DirectLabor": 0.5, "Material": 0.3, "Subcontract": 0.2}
REWORK_MIX = {"DirectLabor": 0.7, "Material": 0.3, "Subcontract": 0.0}


def s_curve(t: int) -> float:
    """Cumulative plan fraction at month t (smoothstep 3x^2 - 2x^3)."""
    x = t / MONTHS
    return 3 * x**2 - 2 * x**3


def schedule_factor(t: int) -> float:
    """EV as a fraction of PV: slightly behind, a dip during rework, recovery to 1 at month 36."""
    if t < REWORK_START:
        return 0.98
    if t <= REWORK_END + 1:
        return 0.92
    return 0.92 + 0.08 * (t - REWORK_END - 1) / (MONTHS - REWORK_END - 1)


def periods() -> list[tuple[int, str, int]]:
    return [(t, f"{START_YEAR + (t - 1) // 12}-{(t - 1) % 12 + 1:02d}", START_YEAR + (t - 1) // 12)
            for t in range(1, MONTHS + 1)]


def plan_pv_ev() -> tuple[list[float], list[float]]:
    pv = [round(BAC * s_curve(t), 3) for t in range(1, MONTHS + 1)]
    ev = [round(BAC * s_curve(t) * schedule_factor(t), 3) for t in range(1, MONTHS + 1)]
    return pv, ev


def direct_costs(ev: list[float]) -> dict[str, dict[str, list[float]]]:
    """Direct cost by WBS and account per month, backed out of a burdened target."""
    burden = (MIX["DirectLabor"] * (1 + PLAN_RATES["Fringe"] + PLAN_RATES["Overhead"])
              + 1 - MIX["DirectLabor"]) * (1 + PLAN_RATES["GA"])
    rework_burden = (REWORK_MIX["DirectLabor"] * (1 + PLAN_RATES["Fringe"] + PLAN_RATES["Overhead"])
                     + 1 - REWORK_MIX["DirectLabor"]) * (1 + PLAN_RATES["GA"])
    out = {w: {a: [] for a in MIX} for w in WBS_SHARE}
    for i, t in enumerate(range(1, MONTHS + 1)):
        direct = (ev[i] - (ev[i - 1] if i else 0.0)) / PLAN_CPI / burden
        rework = REWORK_PER_MONTH / rework_burden if REWORK_START <= t <= REWORK_END else 0.0
        for w, share in WBS_SHARE.items():
            for a, mix in MIX.items():
                extra = rework * REWORK_MIX[a] if w == "FPD1.02" else 0.0
                out[w][a].append(direct * share * mix + extra)
    return out


def _pool_costs(name: str, base: list[float]) -> list[float]:
    return [PLAN_RATES[name] * b * WIGGLE[name][i % 4] for i, b in enumerate(base)]


def build_ledger(ev: list[float]) -> pd.DataFrame:
    """Costpoint-style ledger rows: period, project (WBS), org, account, amount."""
    per = periods()
    fys = [fy for _, _, fy in per]
    d = direct_costs(ev)
    prog_dl = {w: d[w]["DirectLabor"] for w in WBS_SHARE}
    co_dl = [OTHER_DL + sum(prog_dl[w][i] for w in WBS_SHARE) for i in range(MONTHS)]
    fringe_cost, oh_cost = _pool_costs("Fringe", co_dl), _pool_costs("Overhead", co_dl)
    _, fringe = indirect.allocate_pool(fringe_cost, co_dl, prog_dl, fys)
    _, overhead = indirect.allocate_pool(oh_cost, co_dl, prog_dl, fys)
    co_nonlabor = [OTHER_NONLABOR + sum(d[w][a][i] for w in WBS_SHARE for a in ("Material", "Subcontract"))
                   for i in range(MONTHS)]
    co_tci = [co_dl[i] + co_nonlabor[i] + fringe_cost[i] + oh_cost[i] for i in range(MONTHS)]
    prog_tci = {w: [sum(d[w][a][i] for a in MIX) + fringe[w][i] + overhead[w][i] for i in range(MONTHS)]
                for w in WBS_SHARE}
    _, ga = indirect.allocate_pool(_pool_costs("GA", co_tci), co_tci, prog_tci, fys)
    rows = []
    for i, (t, period, fy) in enumerate(per):
        for w in WBS_SHARE:
            lines = [(LABOR_ORG[w], "DirectLabor", d[w]["DirectLabor"][i]),
                     (SCM_ORG, "Material", d[w]["Material"][i]),
                     (SCM_ORG, "Subcontract", d[w]["Subcontract"][i]),
                     (LABOR_ORG[w], "Fringe", fringe[w][i]),
                     (LABOR_ORG[w], "Overhead", overhead[w][i]),
                     (LABOR_ORG[w], "GA", ga[w][i])]
            for org, acct, amt in lines:
                if round(amt, 3) != 0:
                    rows.append({"month": t, "period": period, "fiscal_year": fy, "project": w, "org": org,
                                 "account": acct, "amount": round(amt, 3), "source": SOURCE})
    return pd.DataFrame(rows)


def build_evm(ledger: pd.DataFrame, pv: list[float], ev: list[float]) -> pd.DataFrame:
    monthly = ledger.groupby("month")["amount"].sum().reindex(range(1, MONTHS + 1), fill_value=0.0)
    ac = monthly.cumsum().round(3).tolist()
    rows = []
    for i, (t, period, _) in enumerate(periods()):
        m = evm.metrics(BAC, pv[i], ev[i], ac[i])
        rows.append({"month": t, "period": period, "program": PROGRAM, "bac": BAC, "pv": pv[i], "ev": ev[i],
                     "ac": ac[i], "ac_period": round(float(monthly.iloc[i]), 3), **m, "source": SOURCE})
    return pd.DataFrame(rows).round(3)


def build_revrec(evm_table: pd.DataFrame) -> pd.DataFrame:
    """Revenue uses the composite EAC as the current estimate each month."""
    rows = revrec.recognize(evm_table["ac"].tolist(), evm_table["eac_composite"].tolist(), PRICE)
    out = pd.DataFrame(rows)
    out.insert(0, "period", evm_table["period"])
    out.insert(0, "month", evm_table["month"])
    out["price"] = PRICE
    out["source"] = SOURCE
    return out.round(3)


def simulate() -> dict[str, pd.DataFrame]:
    pv, ev = plan_pv_ev()
    ledger = build_ledger(ev)
    evm_table = build_evm(ledger, pv, ev)
    return {"ledger": ledger, "evm": evm_table, "revrec": build_revrec(evm_table)}
