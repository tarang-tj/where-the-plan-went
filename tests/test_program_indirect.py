"""Costpoint-style YTD catch-up allocation, worked by hand across three periods."""

import pytest

from wtpw.program import indirect

# Company fringe pool cost per period: 10, 14, 6. Company direct labor base: 100 each period.
# Program direct labor: 40, 50, 30 (other projects make up the rest of the base).
#   P1: YTD rate = 10 / 100 = 0.10;  alloc = 0.10 x 40  - 0    = 4.0
#   P2: YTD rate = 24 / 200 = 0.12;  alloc = 0.12 x 90  - 4.0  = 6.8
#   P3: YTD rate = 30 / 300 = 0.10;  alloc = 0.10 x 120 - 10.8 = 1.2
# P3 is the catch-up: the YTD rate fell, so P3 absorbs less than 0.10 x 30 = 3.0.


def test_ytd_rate_and_period_allocation():
    assert indirect.ytd_rate(24, 200) == pytest.approx(0.12)
    assert indirect.period_allocation(0.12, 90, 4.0) == pytest.approx(6.8)


def test_three_period_ytd_catch_up():
    rates, alloc = indirect.allocate_pool([10, 14, 6], [100, 100, 100], {"P": [40, 50, 30]}, [2024] * 3)
    assert rates == pytest.approx([0.10, 0.12, 0.10])
    assert alloc["P"] == pytest.approx([4.0, 6.8, 1.2])
    # YTD allocation equals YTD rate x YTD base at every period end.
    assert sum(alloc["P"]) == pytest.approx(0.10 * 120)


def test_other_projects_absorb_the_rest():
    pools = [10, 14, 6]
    _, alloc = indirect.allocate_pool(pools, [100, 100, 100], {"P": [40, 50, 30], "OTHER": [60, 50, 70]},
                                      [2024] * 3)
    assert sum(alloc["P"]) + sum(alloc["OTHER"]) == pytest.approx(sum(pools))
    assert sum(alloc["P"]) < sum(pools)


def test_fiscal_year_resets_ytd():
    # Period 2 starts a new year, so its rate is 14 / 100 with no prior allocation.
    rates, alloc = indirect.allocate_pool([10, 14], [100, 100], {"P": [40, 50]}, [2024, 2025])
    assert rates == pytest.approx([0.10, 0.14])
    assert alloc["P"] == pytest.approx([4.0, 7.0])


def test_bad_inputs_fail_loud():
    with pytest.raises(ValueError):
        indirect.ytd_rate(5, 0)
    with pytest.raises(ValueError):
        indirect.ytd_rate(5, -1)
    with pytest.raises(ValueError):
        indirect.allocate_pool([1, 2], [10], {"P": [1, 1]}, [2024, 2024])
    with pytest.raises(ValueError):
        indirect.allocate_pool([1], [10], {"P": [20]}, [2024])
