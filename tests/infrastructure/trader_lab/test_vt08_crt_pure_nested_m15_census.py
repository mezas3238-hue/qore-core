"""N1 nested CRT directional and causal unit guards; no economics."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_nested_m15_census import (
    census_micro_crt,
    micro_crt_direction,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import M15Bar
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

T = datetime(2026, 1, 12, 12, 0, tzinfo=UTC)


def bar(i: int, open_: int, high: int, low: int, close: int) -> M15Bar:
    return M15Bar(
        opened_at=T + timedelta(minutes=i * 15),
        open_price=open_, high_price=high, low_price=low,
        close_price=close,
    )


def test_one_sided_low_sweep_and_later_close_above_own_midpoint_is_bullish() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(1, 100, 105, 85, 95),
        bar(2, 96, 106, 94, 104),
    ) is CrtPureCandidateDirection.BULLISH


def test_one_sided_high_sweep_and_later_close_below_own_midpoint_is_bearish() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(1, 100, 115, 95, 108),
        bar(2, 107, 108, 92, 95),
    ) is CrtPureCandidateDirection.BEARISH


def test_two_sided_sweep_is_ambiguous_not_directional() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(1, 100, 115, 85, 100),
        bar(2, 101, 106, 94, 105),
    ) is None


def test_no_sweep_is_not_new_crt() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(1, 100, 105, 95, 102),
        bar(2, 102, 109, 92, 107),
    ) is None


def test_micro_c2_must_close_back_within_micro_c1() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(1, 100, 115, 95, 112),
        bar(2, 100, 108, 91, 96),
    ) is None


def test_micro_c3_must_close_across_own_midpoint_not_only_wick() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(1, 100, 105, 85, 95),
        bar(2, 96, 107, 92, 99),
    ) is None


def test_no_equal_midpoint_confirmation() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(1, 100, 105, 85, 95),
        bar(2, 96, 106, 94, 100),
    ) is None


def test_noncontiguous_m15_not_construed_as_complete_micro() -> None:
    assert micro_crt_direction(
        bar(0, 100, 110, 90, 100),
        bar(2, 100, 105, 85, 95),
        bar(3, 96, 107, 94, 104),
    ) is None


def test_frozen_btcusd_excluded_without_market_access() -> None:
    with pytest.raises(ValueError, match="BTCUSD is frozen"):
        census_micro_crt(CrtPureMarket.BTCUSD, ())
