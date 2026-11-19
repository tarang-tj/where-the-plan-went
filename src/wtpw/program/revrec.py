"""Cost-to-cost revenue over time, cumulative catch-up, and reach-forward loss.

Measure of progress: cost-to-cost input method, as permitted under ASC 606-10-25-31
(measure of progress for performance obligations satisfied over time).
Loss provisions: ASC 605-35-25-46 (provision for the entire anticipated loss on a
contract, recognized in the period the loss becomes evident).

Per period t, given cumulative cost C_t, current EAC E_t and transaction price P:
- pct_t = min(C_t / E_t, 1)
- cumulative revenue R_t = pct_t x P, period revenue = R_t - R_(t-1)
- catch-up_t = pct(C_t, E_t) x P - pct(C_t, E_(t-1)) x P, the part of period revenue
  caused by the estimate change (zero when the EAC does not change)
- if E_t > P the full expected loss (E_t - P) is recognized by period t. Part of it is
  already inside revenue minus cost to date (C_t - R_t); the loss provision balance
  holds the rest, so cumulative gross profit = R_t - C_t - provision = -(E_t - P).
  Period provision = provision balance minus the provision already booked.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def _finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def pct_complete(cum_cost: float, eac: float) -> float:
    """Cost-to-cost percent complete = cumulative cost / EAC, capped at 1."""
    cost, est = _finite("cum_cost", cum_cost), _finite("eac", eac)
    if est <= 0:
        raise ValueError(f"pct_complete: EAC must be positive, got {est}")
    if cost < 0:
        raise ValueError(f"pct_complete: cumulative cost is negative ({cost})")
    return min(cost / est, 1.0)


def loss_provision_balance(cum_cost: float, eac: float, price: float) -> float:
    """Provision needed so that total recognized loss equals EAC - price (0 if no loss)."""
    if eac <= price:
        return 0.0
    cum_rev = pct_complete(cum_cost, eac) * price
    return (eac - price) - (cum_cost - cum_rev)


def recognize(cum_costs: Sequence[float], eacs: Sequence[float], price: float) -> list[dict[str, float]]:
    """Run cost-to-cost revenue recognition across periods. Returns one row per period."""
    p = _finite("price", price)
    if p <= 0:
        raise ValueError(f"transaction price must be positive, got {p}")
    if len(cum_costs) != len(eacs):
        raise ValueError("cum_costs and eacs must have the same length")
    rows: list[dict[str, float]] = []
    prior_rev = prior_prov = prior_cost = 0.0
    prior_eac: float | None = None
    for c, e in zip(cum_costs, eacs):
        c, e = _finite("cum_cost", c), _finite("eac", e)
        if c < prior_cost:
            raise ValueError(f"cumulative cost decreased from {prior_cost} to {c}")
        if e < c:
            raise ValueError(f"EAC {e} is below cumulative cost {c}")
        pct = pct_complete(c, e)
        cum_rev = pct * p
        catch_up = 0.0 if prior_eac is None else cum_rev - pct_complete(c, prior_eac) * p
        prov = loss_provision_balance(c, e, p)
        rows.append(
            {
                "cum_cost": c,
                "eac": e,
                "pct_complete": pct,
                "cum_revenue": cum_rev,
                "period_revenue": cum_rev - prior_rev,
                "catch_up": catch_up,
                "loss_provision_balance": prov,
                "loss_provision_period": prov - prior_prov,
                "period_cost": c - prior_cost,
                "cum_gross_profit": cum_rev - c - prov,
            }
        )
        prior_rev, prior_prov, prior_cost, prior_eac = cum_rev, prov, c, e
    return rows
