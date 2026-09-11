from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    SUPPORTED_VT08_V2_MARKETS,
    Vt08CrtH4AmdV2AbstainReason,
    Vt08CrtH4AmdV2Bar,
    Vt08CrtH4AmdV2H4Candle,
    Vt08CrtH4AmdV2Input,
    Vt08CrtH4AmdV2Profile,
    Vt08CrtH4AmdV2ValidationError,
    evaluate_vt08_crt_h4_amd_v2,
)


def _h4(
    opened: datetime,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
) -> Vt08CrtH4AmdV2H4Candle:
    return Vt08CrtH4AmdV2H4Candle(
        opened_at=opened,
        closed_at=opened + timedelta(hours=4),
        open=Decimal(open_price),
        high=Decimal(high_price),
        low=Decimal(low_price),
        close=Decimal(close_price),
    )


def _bar(
    opened: datetime,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
) -> Vt08CrtH4AmdV2Bar:
    return Vt08CrtH4AmdV2Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_price),
        high=Decimal(high_price),
        low=Decimal(low_price),
        close=Decimal(close_price),
    )


def test_vt08_v2_supports_exact_core_11_market_set() -> None:
    assert set(SUPPORTED_VT08_V2_MARKETS) == {
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "XAUUSD",
        "NAS100",
        "SP500",
        "GBPJPY",
        "AUDJPY",
        "US30",
    }


def test_reversal_closure_wick_then_cisd_yields_long_without_v1_fvg_gate() -> None:
    base_at = datetime(2026, 1, 5, 0, tzinfo=UTC)
    base = _h4(base_at, "100", "110", "90", "105")
    signal = _h4(base.closed_at, "105", "108", "85", "95")
    current_at = signal.closed_at
    bars = (
        _bar(current_at, "100", "100.5", "97", "98"),
        _bar(current_at + timedelta(minutes=15), "98", "98.5", "95", "96"),
        _bar(current_at + timedelta(minutes=30), "96", "102", "95.5", "101"),
    )
    result = evaluate_vt08_crt_h4_amd_v2(
        Vt08CrtH4AmdV2Input(
            symbol="EURUSD",
            as_of=bars[-1].closed_at,
            previous_h4=(base, signal),
            current_h4_opened_at=current_at,
            current_h4_closes_at=current_at + timedelta(hours=4),
            current_m15=bars,
        )
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.LONG
    assert result.setup.profile is Vt08CrtH4AmdV2Profile.REVERSAL
    assert result.setup.cisd_level == Decimal("100")
    assert result.setup.entry_price == Decimal("101")
    assert result.setup.invalidation_price == Decimal("95")


def test_expansion_closure_yields_continuation_short_after_opposing_wick_and_cisd() -> None:
    base_at = datetime(2026, 1, 5, 0, tzinfo=UTC)
    base = _h4(base_at, "100", "110", "90", "100")
    signal = _h4(base.closed_at, "100", "105", "84", "85")
    current_at = signal.closed_at
    bars = (
        _bar(current_at, "100", "102.5", "99.5", "102"),
        _bar(current_at + timedelta(minutes=15), "102", "104", "101.5", "103"),
        _bar(current_at + timedelta(minutes=30), "103", "103.5", "98", "99"),
    )
    result = evaluate_vt08_crt_h4_amd_v2(
        Vt08CrtH4AmdV2Input(
            symbol="NAS100",
            as_of=bars[-1].closed_at,
            previous_h4=(base, signal),
            current_h4_opened_at=current_at,
            current_h4_closes_at=current_at + timedelta(hours=4),
            current_m15=bars,
        )
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.side is DemoTradingSetupSide.SHORT
    assert result.setup.profile is Vt08CrtH4AmdV2Profile.CONTINUATION
    assert result.setup.entry_price == Decimal("99")
    assert result.setup.invalidation_price == Decimal("104")


def test_unsupported_market_fails_closed_as_abstain() -> None:
    opened = datetime(2026, 1, 5, 0, tzinfo=UTC)
    base = _h4(opened, "100", "110", "90", "105")
    signal = _h4(base.closed_at, "105", "108", "85", "95")
    bar = _bar(signal.closed_at, "100", "101", "99", "100.5")
    result = evaluate_vt08_crt_h4_amd_v2(
        Vt08CrtH4AmdV2Input(
            symbol="BTCUSD",
            as_of=bar.closed_at,
            previous_h4=(base, signal),
            current_h4_opened_at=signal.closed_at,
            current_h4_closes_at=signal.closed_at + timedelta(hours=4),
            current_m15=(bar,),
        )
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.UNSUPPORTED_MARKET


def test_future_m15_bar_is_rejected() -> None:
    opened = datetime(2026, 1, 5, 0, tzinfo=UTC)
    base = _h4(opened, "100", "110", "90", "105")
    signal = _h4(base.closed_at, "105", "108", "85", "95")
    bar = _bar(signal.closed_at, "100", "101", "99", "100.5")
    with pytest.raises(Vt08CrtH4AmdV2ValidationError):
        Vt08CrtH4AmdV2Input(
            symbol="EURUSD",
            as_of=bar.opened_at,
            previous_h4=(base, signal),
            current_h4_opened_at=signal.closed_at,
            current_h4_closes_at=signal.closed_at + timedelta(hours=4),
            current_m15=(bar,),
        )
