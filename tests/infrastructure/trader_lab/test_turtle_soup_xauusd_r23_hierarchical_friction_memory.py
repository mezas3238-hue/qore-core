from __future__ import annotations

from collections import Counter
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r21_cautious_mixed_subtype_memory as r21,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r23_hierarchical_friction_memory as r23,
)


def test_break_even_requirement_increases_when_rr_is_small() -> None:
    low = r23._break_even_hit_requirement(Decimal("0.5"))
    high = r23._break_even_hit_requirement(Decimal("2.0"))
    assert low > high
    assert low == Decimal("1.10") / Decimal("1.5")


def test_wilson_lower_is_below_observed_rate() -> None:
    observed = 80 / 100
    lower = r23._wilson_lower(80, 100)
    assert 0 < lower < observed


def test_stable_subtype_requires_same_majority_all_periods() -> None:
    rows = []
    for period in r23.PERIODS:
        rows.extend(
            {"period": period, "structural_label": r21.RECOVERABLE}
            for _ in range(4)
        )
        rows.append({"period": period, "structural_label": r21.ABSTAIN})
    result = r23._stable_subtype(rows)
    assert result["stable"] is True
    assert result["classification"] == r21.RECOVERABLE


def test_resilience_requires_every_period_and_combined_confidence() -> None:
    rows = []
    for period in r23.PERIODS:
        rows.extend(
            {
                "period": period,
                "selected_dol_reached": True,
                "planned_rr": "2.0",
            }
            for _ in range(18)
        )
        rows.extend(
            {
                "period": period,
                "selected_dol_reached": False,
                "planned_rr": "2.0",
            }
            for _ in range(2)
        )
    result = r23._resilience_classification(rows)
    assert result["classification"] == r23.RESILIENT


def test_non_resilient_when_each_period_is_below_break_even() -> None:
    rows = []
    for period in r23.PERIODS:
        rows.extend(
            {
                "period": period,
                "selected_dol_reached": True,
                "planned_rr": "0.5",
            }
            for _ in range(4)
        )
        rows.extend(
            {
                "period": period,
                "selected_dol_reached": False,
                "planned_rr": "0.5",
            }
            for _ in range(16)
        )
    result = r23._resilience_classification(rows)
    assert result["classification"] == r23.NON_RESILIENT


def test_strict_majority_rejects_tie() -> None:
    assert r23._strict_majority(Counter({"A": 5, "B": 5})) is None
