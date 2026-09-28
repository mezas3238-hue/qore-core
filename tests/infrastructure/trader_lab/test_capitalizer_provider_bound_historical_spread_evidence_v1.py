from __future__ import annotations

from dataclasses import dataclass

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_provider_bound_historical_spread_evidence_v1 as spread,
)


@dataclass
class _Tick:
    timestamp: int
    tick: int


def test_decode_ctrader_absolute_then_delta_timestamps() -> None:
    rows = spread._decode_tick_times(
        (
            _Tick(timestamp=1_000_000, tick=100_000),
            _Tick(timestamp=100, tick=100_001),
            _Tick(timestamp=250, tick=100_002),
        )
    )
    assert rows == (
        (1_000_000, 100_000),
        (999_900, 100_001),
        (999_650, 100_002),
    )


def test_decode_rejects_negative_delta() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        spread._decode_tick_times(
            (
                _Tick(timestamp=1_000_000, tick=100_000),
                _Tick(timestamp=-1, tick=100_001),
            )
        )


def test_evidence_contract_is_fixed() -> None:
    assert spread.LOOKBACK_SECONDS == 60
    assert spread.MAX_QUOTE_AGE_MS == 30_000
    assert spread.MIN_REQUEST_INTERVAL_SECONDS >= 0.25
