"""Costpoint-style indirect rate pools with the year-to-date (YTD) catch-up method.

Structure follows Deltek Costpoint indirect rate computation:
https://help.deltek.com/Product/Costpoint/7.1.1/GA/pjx_Indirect_Rate_Computation.html

- YTD rate = YTD pool cost / YTD pool base
- period allocation to a project = YTD rate x YTD project base - prior YTD allocation

Pools here: fringe (base: direct labor), overhead (base: direct labor), and G&A
(base: total cost input = direct labor + material + subcontract + fringe + overhead).
The YTD running totals reset at the start of each fiscal year.
All amounts used in this repo are SYNTHETIC.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

DELTEK_HELP = "https://help.deltek.com/Product/Costpoint/7.1.1/GA/pjx_Indirect_Rate_Computation.html"


def _finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def ytd_rate(ytd_pool_cost: float, ytd_pool_base: float) -> float:
    """YTD rate = YTD pool cost / YTD pool base. Zero base raises ValueError."""
    cost = _finite("ytd_pool_cost", ytd_pool_cost)
    base = _finite("ytd_pool_base", ytd_pool_base)
    if base == 0:
        raise ValueError("YTD rate: pool base is zero, the rate is undefined")
    if base < 0:
        raise ValueError(f"YTD rate: pool base is negative ({base})")
    return cost / base


def period_allocation(rate: float, ytd_project_base: float, prior_ytd_allocation: float) -> float:
    """Period allocation = YTD rate x YTD project base - prior-period YTD allocation."""
    return _finite("rate", rate) * _finite("ytd_project_base", ytd_project_base) - _finite(
        "prior_ytd_allocation", prior_ytd_allocation
    )


def allocate_pool(
    pool_costs: Sequence[float],
    pool_bases: Sequence[float],
    project_bases: dict[str, Sequence[float]],
    fiscal_years: Sequence[int],
) -> tuple[list[float], dict[str, list[float]]]:
    """Run the YTD catch-up allocation of one pool across periods.

    pool_costs and pool_bases are company-level period amounts (the base covers all
    projects, including ones not passed in project_bases). project_bases maps a
    project id to its period base amounts. Returns (YTD rate per period,
    {project: period allocation per period}).
    """
    n = len(pool_costs)
    if len(pool_bases) != n or len(fiscal_years) != n:
        raise ValueError("pool_costs, pool_bases and fiscal_years must have the same length")
    for proj, base in project_bases.items():
        if len(base) != n:
            raise ValueError(f"project {proj}: base has {len(base)} periods, expected {n}")
    rates: list[float] = []
    alloc: dict[str, list[float]] = {p: [] for p in project_bases}
    ytd_cost = ytd_base = 0.0
    ytd_proj = {p: 0.0 for p in project_bases}
    ytd_alloc = {p: 0.0 for p in project_bases}
    for i in range(n):
        if i > 0 and fiscal_years[i] != fiscal_years[i - 1]:
            ytd_cost = ytd_base = 0.0
            ytd_proj = {p: 0.0 for p in project_bases}
            ytd_alloc = {p: 0.0 for p in project_bases}
        ytd_cost += _finite("pool_cost", pool_costs[i])
        ytd_base += _finite("pool_base", pool_bases[i])
        rate = ytd_rate(ytd_cost, ytd_base)
        rates.append(rate)
        for p in project_bases:
            ytd_proj[p] += _finite("project_base", project_bases[p][i])
            amount = period_allocation(rate, ytd_proj[p], ytd_alloc[p])
            ytd_alloc[p] += amount
            alloc[p].append(amount)
    proj_total = [sum(project_bases[p][i] for p in project_bases) for i in range(n)]
    for i in range(n):
        if proj_total[i] > pool_bases[i] + 1e-9:
            raise ValueError(f"period {i}: project bases exceed the company pool base")
    return rates, alloc
