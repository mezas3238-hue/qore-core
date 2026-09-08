from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.first_cohort_backtest import FirstCohortBacktestTrade
from qore.infrastructure.trader_lab.first_cohort_characterization import (
    _Bucket,
    _trend_regime,
    _volatility_regime,
)
from qore.infrastructure.trader_lab.first_cohort_characterization_aggregate import (
    FirstCohortCharacterizationError,
    run_characterization_aggregate,
)

_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_SYMBOLS = ("AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDJPY", "XAUUSD")


def _bar(close: float, *, spread: float = 0.001) -> OhlcSnapshot:
    return cast(
        OhlcSnapshot,
        SimpleNamespace(close=close, high=close + spread, low=close - spread),
    )


def test_past_only_regime_descriptors_distinguish_trend_and_volatility() -> None:
    trend = tuple(_bar(1.0 + index * 0.001) for index in range(60))
    assert _trend_regime(trend) == "trend"

    normal_then_high = tuple(
        [_bar(1.0, spread=0.0001) for _ in range(40)]
        + [_bar(1.0, spread=0.001) for _ in range(10)]
    )
    assert _volatility_regime(normal_then_high) == "high"


def test_bucket_records_fill_conversion_and_outcome_metrics() -> None:
    bucket = _Bucket()
    bucket.record(None)
    trade = cast(FirstCohortBacktestTrade, SimpleNamespace(return_rate=0))
    trade.return_rate = cast(object, None)  # type: ignore[attr-defined]
