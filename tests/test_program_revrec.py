"""Cost-to-cost revenue, cumulative catch-up and the reach-forward loss period, by hand."""

import pytest

from wtpw.program import revrec

PRICE = 100.0
# Period: cum cost, EAC
#   P1: 20, 80   pct 0.25 rev 25  period 25  catch-up 0           provision 0
#   P2: 40, 80   pct 0.50 rev 50  period 25  catch-up 0           provision 0
#   P3: 60, 120  pct 0.50 rev 50  period 0   catch-up 50-75 = -25 loss 20:
#                provision = 20 - (60 - 50) = 10; cum GP = 50 - 60 - 10 = -20
#   P4: 90, 120  pct 0.75 rev 75  period 25  catch-up 0  provision = 20 - 15 = 5 (period -5); GP -20
#   P5: 120,120  pct 1.00 rev 100 period 25  catch-up 0  provision 0 (period -5); GP -20
COSTS = [20, 40, 60, 90, 120]
EACS = [80, 80, 120, 120, 120]


@pytest.fixture
def rows():
    return revrec.recognize(COSTS, EACS, PRICE)


def col(rows, key):
    return [r[key] for r in rows]


def test_cost_to_cost_revenue(rows):
    assert col(rows, "pct_complete") == pytest.approx([0.25, 0.5, 0.5, 0.75, 1.0])
    assert col(rows, "cum_revenue") == pytest.approx([25, 50, 50, 75, 100])
    assert col(rows, "period_revenue") == pytest.approx([25, 25, 0, 25, 25])


def test_catch_up_on_estimate_change(rows):
    assert col(rows, "catch_up") == pytest.approx([0, 0, -25, 0, 0])


def test_loss_period_books_full_loss(rows):
    assert col(rows, "loss_provision_balance") == pytest.approx([0, 0, 10, 5, 0])
    assert col(rows, "loss_provision_period") == pytest.approx([0, 0, 10, -5, -5])
    assert col(rows, "cum_gross_profit") == pytest.approx([5, 10, -20, -20, -20])


def test_unchanged_eac_has_zero_catch_up():
    rows = revrec.recognize([10, 30, 60, 90], [90, 90, 90, 90], PRICE)
    assert col(rows, "catch_up") == pytest.approx([0, 0, 0, 0])
    assert sum(col(rows, "period_revenue")) == pytest.approx(PRICE)


def test_pct_capped_at_one():
    assert revrec.pct_complete(130, 120) == 1.0


def test_bad_inputs_fail_loud():
    with pytest.raises(ValueError):
        revrec.recognize([10, 5], [50, 50], PRICE)  # cumulative cost falls
    with pytest.raises(ValueError):
        revrec.recognize([60], [50], PRICE)  # EAC below cost incurred
    with pytest.raises(ValueError):
        revrec.recognize([10], [50], 0)
    with pytest.raises(ValueError):
        revrec.pct_complete(10, 0)
