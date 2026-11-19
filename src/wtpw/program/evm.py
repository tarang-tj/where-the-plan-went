"""Earned value management (EVM) formulas on cumulative values.

All inputs are cumulative to date: PV (planned value, BCWS), EV (earned value,
BCWP), AC (actual cost, ACWP), and BAC (budget at completion). Formulas follow
the NSF EVM Gold Card: https://www.nsf.gov/od/ori/evm-gold-card

Zero denominators raise ValueError. These functions never return inf or nan.
"""

from __future__ import annotations

import math

GOLD_CARD = "https://www.nsf.gov/od/ori/evm-gold-card"


def _check(name: str, value: float) -> float:
    if value is None or not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def _divide(num: float, den: float, what: str) -> float:
    if den == 0:
        raise ValueError(f"{what}: denominator is zero, the ratio is undefined")
    return num / den


def cpi(ev: float, ac: float) -> float:
    """Cost performance index, CPI = EV / AC (NSF EVM Gold Card)."""
    return _divide(_check("EV", ev), _check("AC", ac), "CPI = EV / AC")


def spi(ev: float, pv: float) -> float:
    """Schedule performance index, SPI = EV / PV (NSF EVM Gold Card)."""
    return _divide(_check("EV", ev), _check("PV", pv), "SPI = EV / PV")


def cv(ev: float, ac: float) -> float:
    """Cost variance, CV = EV - AC (NSF EVM Gold Card). Negative is an overrun."""
    return _check("EV", ev) - _check("AC", ac)


def sv(ev: float, pv: float) -> float:
    """Schedule variance, SV = EV - PV (NSF EVM Gold Card). Negative is behind plan."""
    return _check("EV", ev) - _check("PV", pv)


def eac_bac(bac: float, ev: float, ac: float) -> float:
    """EAC = BAC / CPI (NSF EVM Gold Card)."""
    return _divide(_check("BAC", bac), cpi(ev, ac), "EAC = BAC / CPI")


def eac_cpi(bac: float, ev: float, ac: float) -> float:
    """EAC = AC + (BAC - EV) / CPI (NSF EVM Gold Card)."""
    bac, ac_f = _check("BAC", bac), _check("AC", ac)
    return ac_f + _divide(bac - _check("EV", ev), cpi(ev, ac), "EAC = AC + (BAC - EV) / CPI")


def eac_composite(bac: float, pv: float, ev: float, ac: float) -> float:
    """EAC = AC + (BAC - EV) / (CPI x SPI) (NSF EVM Gold Card, composite index)."""
    bac, ac_f = _check("BAC", bac), _check("AC", ac)
    index = cpi(ev, ac) * spi(ev, pv)
    return ac_f + _divide(bac - _check("EV", ev), index, "EAC = AC + (BAC - EV) / (CPI x SPI)")


def etc(eac: float, ac: float) -> float:
    """Estimate to complete, ETC = EAC - AC (NSF EVM Gold Card)."""
    return _check("EAC", eac) - _check("AC", ac)


def vac(bac: float, eac: float) -> float:
    """Variance at completion, VAC = BAC - EAC (NSF EVM Gold Card)."""
    return _check("BAC", bac) - _check("EAC", eac)


def tcpi_to_eac(bac: float, ev: float, eac: float, ac: float) -> float:
    """To-complete performance index against the EAC, TCPI = (BAC - EV) / (EAC - AC).

    Source: NSF EVM Gold Card. Undefined (ValueError) when EAC equals AC.
    """
    work_left = _check("BAC", bac) - _check("EV", ev)
    return _divide(work_left, _check("EAC", eac) - _check("AC", ac), "TCPI = (BAC - EV) / (EAC - AC)")


def metrics(bac: float, pv: float, ev: float, ac: float) -> dict[str, float]:
    """All Gold Card metrics for one status date. TCPI uses the composite EAC.

    TCPI is reported as nan only at completion (EAC == AC, no work left), the one
    case where it is undefined by construction rather than by bad input.
    """
    eac_c = eac_composite(bac, pv, ev, ac)
    if eac_c == ac and bac == ev:
        tcpi = math.nan
    else:
        tcpi = tcpi_to_eac(bac, ev, eac_c, ac)
    return {
        "cpi": cpi(ev, ac),
        "spi": spi(ev, pv),
        "cv": cv(ev, ac),
        "sv": sv(ev, pv),
        "eac_bac": eac_bac(bac, ev, ac),
        "eac_cpi": eac_cpi(bac, ev, ac),
        "eac_composite": eac_c,
        "etc": etc(eac_c, ac),
        "vac": vac(bac, eac_c),
        "tcpi": tcpi,
    }
