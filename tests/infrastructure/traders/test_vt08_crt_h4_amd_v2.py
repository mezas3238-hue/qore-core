from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    SOURCE_TIMING_AMBIGUOUS_MARKETS,
    SUPPORTED_MARKETS,
    Vt08CrtH4AmdV2AbstainReason,
    Vt08CrtH4AmdV2Candle,
    Vt08CrtH4AmdV2Scenario,
    Vt08CrtH4AmdV2Setup,
    Vt08CrtH4AmdV2SourceContext,
    Vt08CrtH4AmdV2TimingFamily,
    Vt08CrtH4AmdV2ValidationError,
    Vt08CrtH4AmdV2WickProfile,
    evaluate_continuation_expansion_candle3,
    evaluate_reversal_expansion_candle2,
    timing_family_for_market,
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


def _context(
    side: DemoTradingSetupSide | None,
    wick: Vt08CrtH4AmdV2WickProfile,
) -> Vt08CrtH4AmdV2SourceContext:
    return Vt08CrtH4AmdV2SourceContext(
        bias_side=side,
        wick_profile=wick,
        provenance="human-owner-primary-video/source-context",
    )


def test_v2_supports_exact_core_11_market_set_without_guessing_gold_timing() -> None:
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
    assert timing_family_for_market("EURUSD") is Vt08CrtH4AmdV2TimingFamily.FOREX
    assert timing_family_for_market("NAS100") is Vt08CrtH4AmdV2TimingFamily.FUTURES
    assert (
        timing_family_for_market("XAUUSD")
        is Vt08CrtH4AmdV2TimingFamily.SOURCE_UNRESOLVED
    )
    assert SOURCE_TIMING_AMBIGUOUS_MARKETS == frozenset({"XAUUSD"})


def test_unresolved_video_wick_language_is_not_converted_to_numeric_threshold() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    reference = _candle(day, "100", "105", "95", "102", minutes=240)
    bars = (
        _candle(day + timedelta(hours=4), "99", "99.5", "94.5", "96"),
        _candle(day + timedelta(hours=4, minutes=15), "96", "101", "95", "100"),
    )
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=day + timedelta(hours=8),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.UNRESOLVED,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.WICK_CLASSIFICATION_REQUIRED
    )


def test_source_bias_is_explicit_context_not_an_invented_daily_formula() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    reference = _candle(day, "100", "105", "95", "102", minutes=240)
    bars = (
        _candle(day + timedelta(hours=4), "99", "99.5", "94.5", "96"),
        _candle(day + timedelta(hours=4, minutes=15), "96", "101", "95", "100"),
    )
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=day + timedelta(hours=8),
        observed_m15=bars,
        context=_context(None, Vt08CrtH4AmdV2WickProfile.SHALLOW),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.BIAS_CONTEXT_REQUIRED


def test_video_shallow_candle2_plus_reference_run_and_cisd_yields_setup() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    reference = _candle(day, "100", "105", "95", "102", minutes=240)
    bars = (
        _candle(day + timedelta(hours=4), "99", "99.5", "94.5", "96"),
        _candle(day + timedelta(hours=4, minutes=15), "96", "101", "95", "100"),
    )
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=day + timedelta(hours=8),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
        ),
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.scenario is Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2
    assert result.setup.side is DemoTradingSetupSide.LONG
    assert result.setup.stop_loss == Decimal("94.5")
    assert result.setup.protected_swing_extreme == Decimal("94.5")
    assert result.setup.take_profit is None


def test_video_large_candle2_does_not_get_forced_into_same_candle_trade() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    reference = _candle(day, "100", "105", "95", "102", minutes=240)
    bars = (
        _candle(day + timedelta(hours=4), "99", "99.5", "90", "96"),
        _candle(day + timedelta(hours=4, minutes=15), "96", "101", "95", "100"),
    )
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=day + timedelta(hours=8),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.LARGE,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.WAIT_FOR_CANDLE3


def test_video_large_candle2_reversal_then_shallow_candle3_cisd_yields_continuation() -> None:
    day = datetime(2026, 1, 3, tzinfo=UTC)
    reference = _candle(day, "100", "105", "95", "102", minutes=240)
    candle2 = _candle(
        day + timedelta(hours=4),
        "100",
        "103",
        "90",
        "98",
        minutes=240,
    )
    c3 = day + timedelta(hours=8)
    bars = (
        _candle(c3, "98", "98.5", "96", "97"),
        _candle(c3 + timedelta(minutes=15), "97", "100", "96.5", "99"),
    )
    result = evaluate_continuation_expansion_candle3(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2=candle2,
        h4_candle3_closes_at=c3 + timedelta(hours=4),
        observed_m15=bars,
        candle2_wick_profile=Vt08CrtH4AmdV2WickProfile.LARGE,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
        ),
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert (
        result.setup.scenario
        is Vt08CrtH4AmdV2Scenario.CONTINUATION_EXPANSION_C3
    )
    assert result.setup.stop_loss == Decimal("96")
    assert result.setup.take_profit is None


def test_universal_take_profit_is_explicitly_prohibited() -> None:
    with pytest.raises(Vt08CrtH4AmdV2ValidationError):
        Vt08CrtH4AmdV2Setup(
            side=DemoTradingSetupSide.LONG,
            scenario=Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2,
            entry_price=Decimal("100"),
            stop_loss=Decimal("99"),
            signal_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
            expires_at=datetime(2026, 1, 1, 4, tzinfo=UTC),
            cisd_level=Decimal("99.5"),
            protected_swing_extreme=Decimal("99"),
            wick_profile=Vt08CrtH4AmdV2WickProfile.SHALLOW,
            take_profit=Decimal("110"),  # type: ignore[arg-type]
        )
