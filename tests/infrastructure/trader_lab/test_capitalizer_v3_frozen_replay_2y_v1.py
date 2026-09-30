from datetime import UTC, datetime, timedelta
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_v3_frozen_replay_2y_v1 import (
    IDENTITY,
    LOOKBACK_START,
    MATRIX_IDENTITY,
    WINDOW_END,
    WINDOW_START,
    _v3_window,
)


def test_v3_2y_window_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_FROZEN_REPLAY_2Y_V1"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_V3_FROZEN_REPLAY_2Y_V1"
    assert WINDOW_START == datetime(2024, 9, 17, tzinfo=UTC)
    assert WINDOW_END == datetime(2026, 9, 17, tzinfo=UTC)
    assert LOOKBACK_START == WINDOW_START - timedelta(days=21)


def test_v3_window_adapter_restores_frozen_module_globals() -> None:
    mutable_v3: Any = v3
    original = (
        mutable_v3.WINDOW_START,
        mutable_v3.WINDOW_END,
        mutable_v3.LOOKBACK_START,
    )

    with _v3_window():
        assert mutable_v3.WINDOW_START == WINDOW_START
        assert mutable_v3.WINDOW_END == WINDOW_END
        assert mutable_v3.LOOKBACK_START == LOOKBACK_START

    assert (
        mutable_v3.WINDOW_START,
        mutable_v3.WINDOW_END,
        mutable_v3.LOOKBACK_START,
    ) == original
