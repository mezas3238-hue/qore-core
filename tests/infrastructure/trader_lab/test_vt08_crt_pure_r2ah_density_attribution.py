from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2ah_density_attribution import (
    CONFIGS,
    END,
    IDENTITY,
    _rate,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_density_identity_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AH_LONG_WINDOW_DENSITY_ATTRIBUTION_001"


def test_market_windows_match_long_replays() -> None:
    aud = CONFIGS[CrtPureMarket.AUDUSD]
    uj = CONFIGS[CrtPureMarket.USDJPY]

    assert aud.start.isoformat() == "2016-09-21T00:00:00+00:00"
    assert uj.start.isoformat() == "2014-09-21T00:00:00+00:00"
    assert END.isoformat() == "2026-09-21T00:00:00+00:00"


def test_efficiency_filters_match_current_target_labs() -> None:
    aud = CONFIGS[CrtPureMarket.AUDUSD]
    uj = CONFIGS[CrtPureMarket.USDJPY]

    assert aud.efficiency_index == 2
    assert aud.efficiency_low == Decimal("0.10")
    assert aud.efficiency_high == Decimal("0.20")

    assert uj.efficiency_index == 3
    assert uj.efficiency_low == Decimal("0.10")
    assert uj.efficiency_high == Decimal("0.20")


def test_rate_is_fail_safe_for_zero_denominator() -> None:
    assert _rate(5, 0) == 0.0
    assert _rate(1, 4) == 0.25
