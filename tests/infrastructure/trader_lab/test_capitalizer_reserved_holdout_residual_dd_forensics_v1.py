from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_reserved_holdout_residual_dd_forensics_v1 as lab,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)


def _trade(value: str, index: int) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="NAS100",
        session="NEW_YORK",
        operating_date=f"2026-01-{index + 1:02d}",
        side="LONG",
        entry_at=f"2026-01-{index + 1:02d}T10:00:00+00:00",
        exit_at=f"2026-01-{index + 1:02d}T10:10:00+00:00",
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=value,
        exit_reason="STOP" if Decimal(value) < 0 else "TARGET",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def test_max_dd_segment_is_exact_peak_to_trough() -> None:
    rows = tuple(
        _trade(value, index)
        for index, value in enumerate(("2", "-1", "-2", "1", "-3", "4"))
    )
    start, end, dd = lab._max_dd_segment(rows)
    assert start == 1
    assert end == 4
    assert dd == Decimal("5")


def test_rolling_worst_uses_contiguous_window() -> None:
    rows = tuple(
        _trade(value, index)
        for index, value in enumerate(("1", "-1", "-2", "3", "-1"))
    )
    result = lab._rolling_worst(rows, length=2)
    assert result["start_index"] == 1
    assert result["end_index"] == 2
    assert Decimal(str(result["sum_r"])) == Decimal("-3")
