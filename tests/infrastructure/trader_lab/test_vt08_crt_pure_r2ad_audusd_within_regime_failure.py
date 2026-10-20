from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2ad_audusd_within_regime_failure import (
    BAD_END,
    BAD_START,
    EFF1_HIGH,
    EFF1_LOW,
    END,
    MARKET,
    START,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2ad_frozen_regime_and_bad_year() -> None:
    assert MARKET is CrtPureMarket.AUDUSD
    assert EFF1_LOW == Decimal("0.10")
    assert EFF1_HIGH == Decimal("0.20")
    assert BAD_START.isoformat() == "2016-09-21T00:00:00+00:00"
    assert BAD_END.isoformat() == "2017-09-21T00:00:00+00:00"


def test_r2ad_consumed_window_is_2016_2026() -> None:
    assert START.isoformat() == "2016-09-21T00:00:00+00:00"
    assert END.isoformat() == "2026-09-21T00:00:00+00:00"
