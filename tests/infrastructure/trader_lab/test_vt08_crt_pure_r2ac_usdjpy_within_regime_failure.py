from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2ac_usdjpy_within_regime_failure import (
    BAD_END,
    BAD_START,
    EFF5_HIGH,
    EFF5_LOW,
    END,
    MARKET,
    START,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2ac_frozen_regime_and_bad_year() -> None:
    assert MARKET is CrtPureMarket.USDJPY
    assert EFF5_LOW == Decimal("0.10")
    assert EFF5_HIGH == Decimal("0.20")
    assert BAD_START.isoformat() == "2019-09-21T00:00:00+00:00"
    assert BAD_END.isoformat() == "2020-09-21T00:00:00+00:00"


def test_r2ac_consumed_window_is_2018_2026() -> None:
    assert START.isoformat() == "2018-09-21T00:00:00+00:00"
    assert END.isoformat() == "2026-09-21T00:00:00+00:00"
