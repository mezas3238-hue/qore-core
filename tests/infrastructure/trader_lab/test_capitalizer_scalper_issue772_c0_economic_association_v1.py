"""Preregistered E0 test: association is not proof of feed causation."""
from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_issue772_c0_economic_association_v1 import (
    adjusted_diff,
    block_bootstrap,
    performance,
    quantile,
)


def record(
    day: int,
    symbol: str,
    partial: bool,
    r: str,
    inherited: bool = False,
) -> dict:
    return {
        "symbol": symbol,
        "session": "ASIA" if symbol == "AUDJPY" else "LONDON",
        "operating_date": f"2026-07-{day:02d}",
        "inherited": inherited,
        "partial": partial,
        "h1_strict_signature_changed": partial,
        "trade": {"realized_gross_r": r},
    }


def test_adjusted_delta_equal_when_symbols_differ_only_in_baseline() -> None:
    # Pooled means differ through market composition, but adjusted is zero.
    rows = [
        record(1, "AUDJPY", True, "-1"),
        record(2, "AUDJPY", False, "-1"),
        record(3, "GBPUSD", True, "1"),
        record(4, "GBPUSD", False, "1"),
    ]
    assert adjusted_diff(rows) == pytest.approx(0.0)


def test_adjusted_delta_uses_within_market_R_not_direction_or_PF() -> None:
    rows = [
        record(1, "AUDJPY", True, "-1"),
        record(2, "AUDJPY", False, "0"),
        record(3, "GBPUSD", True, "2"),
        record(4, "GBPUSD", False, "1"),
    ]
    assert adjusted_diff(rows) == pytest.approx(0)
    # Each cell has its own two trade signs.
    rows[2]["trade"]["realized_gross_r"] = "-1"
    assert adjusted_diff(rows) == pytest.approx(-1.5)


def test_cost_is_not_mislabeled_real_broker_cost() -> None:
    x = performance([record(1, "AUDJPY", True, "1"),
                     record(2, "AUDJPY", False, "-1")])
    assert x["N"] == 2
    assert x["gross"]["expectancy"] == "0"
    assert Decimal(x["assumed_cost_0p025R"]["expectancy"]) == Decimal("-0.025")


def test_circular_block_bootstrap_preserves_date_clusters() -> None:
    rows = [
        record(day, "AUDJPY", bool(day % 2), "1" if day % 2 else "-1")
        for day in range(1, 21)
    ]
    a = block_bootstrap(rows, n=100, seed=44)
    b = block_bootstrap(rows, n=100, seed=44)
    assert a == b
    assert a["CI95"][0] <= a["median"] <= a["CI95"][1]
    assert a["not_confirmatory"]


def test_bootstrap_rejects_uninformative_small_sample() -> None:
    with pytest.raises(ValueError, match="too few"):
        block_bootstrap(
            [record(1, "AUDJPY", True, "1")], n=20
        )


def test_quantile_interpolation() -> None:
    assert quantile([10, 0], .5) == pytest.approx(5.0)
