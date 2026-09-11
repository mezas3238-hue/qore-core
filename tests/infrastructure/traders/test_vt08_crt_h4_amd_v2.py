from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    SUPPORTED_MARKETS,
    Vt08CrtH4AmdV2Candle,
    Vt08CrtH4AmdV2DailyMode,
    Vt08CrtH4AmdV2Scenario,
    daily_bias,
    evaluate_candle2_expansion,
    evaluate_candle3_continuation,
)


def _candle(
    opened: datetime,
    open_price: str,
    high_price: str,
    low_price: str,
    close_price: str,
    *,
    minutes: int = 15,
) -> Vt08CrtH4AmdV2Candle:
    return Vt08CrtH4AmdV2Candle(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=minutes),
        open=Decimal(open_price),
        high=Decimal(high_price),
        low=Decimal(low_price),
        close=Decimal(close_price),
    )


def test_reconstructed_v2_supports_exact_core_11_markets() -> None:
    assert set(SUPPORTED_MARKETS) == {
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


def test_daily_bias_is_required_and_distinguishes_continuation_from_reversal() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    reference = _candle(start, "100", "110", "90", "100", minutes=1440)
    continuation = _candle(
        start + timedelta(days=1), "100", "115", "95", "112", minutes=1440
    )
    reversal = _candle(
        start + timedelta(days=1), "100", "108", "85", "95", minutes=1440
    )
    cont_bias = daily_bias(reference, continuation)
    rev_bias = daily_bias(reference, reversal)
    assert cont_bias is not None
    assert cont_bias.side is DemoTradingSetupSide.LONG
    assert cont_bias.mode is Vt08CrtH4AmdV2DailyMode.CONTINUATION
    assert cont_bias.target == Decimal("115")
    assert rev_bias is not None
    assert rev_bias.side is DemoTradingSetupSide.LONG
    assert rev_bias.mode is Vt08CrtH4AmdV2DailyMode.REVERSAL


def test_shallow_candle2_wick_plus_m15_cisd_produces_same_candle_setup() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    daily_reference = _candle(
        day - timedelta(days=2), "100", "110", "90", "100", minutes=1440
    )
    daily_signal = _candle(
        day - timedelta(days=1), "100", "115", "95", "112", minutes=1440
    )
    h4_reference = _candle(day, "100", "105", "95", "102", minutes=240)
    c2_open = day + timedelta(hours=4)
    bars = (
        _candle(c2_open, "99", "99.5", "94.5", "96"),
        _candle(c2_open + timedelta(minutes=15), "96", "101", "95", "100"),
    )
    result = evaluate_candle2_expansion(
        symbol="EURUSD",
        daily_reference=daily_reference,
        daily_signal=daily_signal,
        h4_reference=h4_reference,
        h4_candle2_open=Decimal("99"),
        h4_candle2_closes_at=c2_open + timedelta(hours=4),
        observed_m15=bars,
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.scenario is Vt08CrtH4AmdV2Scenario.CANDLE2_EXPANSION
    assert result.setup.side is DemoTradingSetupSide.LONG
    assert result.setup.stop_loss == Decimal("94.5")
    assert result.setup.take_profit == Decimal("115")
    assert result.setup.manipulation_fraction_of_reference == Decimal("0.45")


def test_large_candle2_waits_for_candle3_and_requires_new_m15_cisd() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    daily_reference = _candle(
        day - timedelta(days=2), "100", "110", "90", "100", minutes=1440
    )
    daily_signal = _candle(
        day - timedelta(days=1), "100", "115", "95", "112", minutes=1440
    )
    h4_reference = _candle(day, "100", "105", "95", "102", minutes=240)
    h4_candle2 = _candle(
        day + timedelta(hours=4), "100", "103", "90", "98", minutes=240
    )
    c3_open = day + timedelta(hours=8)
    bars = (
        _candle(c3_open, "98", "98.5", "96", "97"),
        _candle(c3_open + timedelta(minutes=15), "97", "100", "96.5", "99"),
    )
    result = evaluate_candle3_continuation(
        symbol="EURUSD",
        daily_reference=daily_reference,
        daily_signal=daily_signal,
        h4_reference=h4_reference,
        h4_candle2=h4_candle2,
        h4_candle3_open=Decimal("98"),
        h4_candle3_closes_at=c3_open + timedelta(hours=4),
        observed_m15=bars,
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.scenario is Vt08CrtH4AmdV2Scenario.CANDLE3_CONTINUATION
    assert result.setup.stop_loss == Decimal("96")
    assert result.setup.take_profit == Decimal("115")


def test_no_daily_bias_means_no_intraday_setup_even_with_local_sweep() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    daily_reference = _candle(
        day - timedelta(days=2), "100", "110", "90", "100", minutes=1440
    )
    daily_signal = _candle(
        day - timedelta(days=1), "100", "108", "92", "101", minutes=1440
    )
    h4_reference = _candle(day, "100", "105", "95", "102", minutes=240)
    c2_open = day + timedelta(hours=4)
    bars = (
        _candle(c2_open, "99", "99.5", "94.5", "96"),
        _candle(c2_open + timedelta(minutes=15), "96", "101", "95", "100"),
    )
    result = evaluate_candle2_expansion(
        symbol="EURUSD",
        daily_reference=daily_reference,
        daily_signal=daily_signal,
        h4_reference=h4_reference,
        h4_candle2_open=Decimal("99"),
        h4_candle2_closes_at=c2_open + timedelta(hours=4),
        observed_m15=bars,
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
