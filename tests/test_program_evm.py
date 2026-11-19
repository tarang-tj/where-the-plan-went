"""Hand-computed checks of every EVM formula (NSF EVM Gold Card)."""

import math

import pytest

from wtpw.program import evm

# Textbook example worked by hand:
#   BAC = 1000, PV = 500, EV = 400, AC = 500
#   CPI = EV / AC = 400 / 500 = 0.8
#   SPI = EV / PV = 400 / 500 = 0.8
#   CV  = EV - AC = 400 - 500 = -100
#   SV  = EV - PV = 400 - 500 = -100
#   EAC_bac       = BAC / CPI = 1000 / 0.8 = 1250
#   EAC_cpi       = AC + (BAC - EV) / CPI = 500 + 600 / 0.8 = 500 + 750 = 1250
#   EAC_composite = AC + (BAC - EV) / (CPI x SPI) = 500 + 600 / 0.64 = 500 + 937.5 = 1437.5
#   ETC (composite) = 1437.5 - 500 = 937.5
#   VAC (composite) = 1000 - 1437.5 = -437.5
#   TCPI to composite EAC = (1000 - 400) / (1437.5 - 500) = 600 / 937.5 = 0.64
#   TCPI to EAC_cpi       = 600 / (1250 - 500) = 600 / 750 = 0.8
BAC, PV, EV, AC = 1000.0, 500.0, 400.0, 500.0


def test_indices_and_variances():
    assert evm.cpi(EV, AC) == pytest.approx(0.8)
    assert evm.spi(EV, PV) == pytest.approx(0.8)
    assert evm.cv(EV, AC) == pytest.approx(-100.0)
    assert evm.sv(EV, PV) == pytest.approx(-100.0)


def test_eac_forms():
    assert evm.eac_bac(BAC, EV, AC) == pytest.approx(1250.0)
    assert evm.eac_cpi(BAC, EV, AC) == pytest.approx(1250.0)
    assert evm.eac_composite(BAC, PV, EV, AC) == pytest.approx(1437.5)


def test_etc_vac_tcpi():
    assert evm.etc(1437.5, AC) == pytest.approx(937.5)
    assert evm.vac(BAC, 1437.5) == pytest.approx(-437.5)
    assert evm.tcpi_to_eac(BAC, EV, 1437.5, AC) == pytest.approx(0.64)
    assert evm.tcpi_to_eac(BAC, EV, 1250.0, AC) == pytest.approx(0.8)


def test_second_example_ahead_and_under():
    # BAC 200, PV 50, EV 60, AC 48: CPI 1.25, SPI 1.2, CV 12, SV 10,
    # EAC_cpi = 48 + 140 / 1.25 = 160, EAC_composite = 48 + 140 / 1.5 = 141.333...
    assert evm.cpi(60, 48) == pytest.approx(1.25)
    assert evm.spi(60, 50) == pytest.approx(1.2)
    assert evm.eac_cpi(200, 60, 48) == pytest.approx(160.0)
    assert evm.eac_composite(200, 50, 60, 48) == pytest.approx(48 + 140 / 1.5)


def test_metrics_bundle_matches_single_functions():
    m = evm.metrics(BAC, PV, EV, AC)
    assert m["eac_composite"] == pytest.approx(1437.5)
    assert m["etc"] == pytest.approx(937.5)
    assert m["vac"] == pytest.approx(-437.5)
    assert m["tcpi"] == pytest.approx(0.64)


def test_metrics_at_completion_tcpi_is_nan_not_inf():
    m = evm.metrics(100.0, 100.0, 100.0, 110.0)
    assert m["eac_composite"] == pytest.approx(110.0)
    assert math.isnan(m["tcpi"])


@pytest.mark.parametrize(
    "call",
    [
        lambda: evm.cpi(10, 0),
        lambda: evm.spi(10, 0),
        lambda: evm.eac_bac(100, 0, 10),
        lambda: evm.eac_cpi(100, 10, 0),
        lambda: evm.eac_composite(100, 0, 10, 10),
        lambda: evm.tcpi_to_eac(100, 50, 80, 80),
        lambda: evm.cpi(float("nan"), 1),
        lambda: evm.cv(float("inf"), 1),
    ],
)
def test_bad_inputs_fail_loud(call):
    with pytest.raises(ValueError):
        call()
