from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    FOREX_H4_ANCHOR_HOURS,
    FUTURES_H4_ANCHOR_HOURS,
    SOURCE_TIMING_AMBIGUOUS_MARKETS,
    SUPPORTED_MARKETS,
    Vt08CrtH4AmdV2AbstainReason,
    Vt08CrtH4AmdV2Candle,
    Vt08CrtH4AmdV2ConfirmedOpportunity,
    Vt08CrtH4AmdV2Scenario,
    Vt08CrtH4AmdV2SourceContext,
    Vt08CrtH4AmdV2TimingFamily,
    Vt08CrtH4AmdV2ValidationError,
    Vt08CrtH4AmdV2WickProfile,
    evaluate_continuation_expansion_candle3,
    evaluate_reversal_expansion_candle2,
    source_anchor_hours_for_market,
    timing_family_for_market,
)

_NY = ZoneInfo("America/New_York")


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
    *,
    observed_at: datetime,
) -> Vt08CrtH4AmdV2SourceContext:
    return Vt08CrtH4AmdV2SourceContext(
        bias_side=side,
        wick_profile=wick,
        observed_at=observed_at,
        provenance="human-owner-primary-video/source-context",
    )


def _c2_case() -> tuple[datetime, Vt08CrtH4AmdV2Candle, tuple[Vt08CrtH4AmdV2Candle, ...]]:
    anchor = datetime(2026, 1, 5, 1, 0, tzinfo=_NY)
    reference = _candle(
        anchor - timedelta(hours=4),
        "100",
        "105",
        "95",
        "102",
        minutes=240,
    )
    bars = (
        _candle(anchor, "99", "99.5", "94.5", "96"),
        _candle(anchor + timedelta(minutes=15), "96", "101", "95", "100"),
    )
    return anchor, reference, bars


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


def test_primary_video_full_h4_timing_families_are_frozen() -> None:
    assert FOREX_H4_ANCHOR_HOURS == (1, 5, 9, 13, 17, 21)
    assert FUTURES_H4_ANCHOR_HOURS == (2, 6, 10, 14, 18, 22)
    assert source_anchor_hours_for_market("GBPUSD") == FOREX_H4_ANCHOR_HOURS
    assert source_anchor_hours_for_market("NAS100") == FUTURES_H4_ANCHOR_HOURS
    assert source_anchor_hours_for_market("XAUUSD") is None


def test_xauusd_abstains_instead_of_guessing_a_timing_family() -> None:
    anchor, reference, bars = _c2_case()
    result = evaluate_reversal_expansion_candle2(
        symbol="XAUUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=anchor,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.TIMING_FAMILY_REQUIRED
    assert result.confirmed_opportunity is None
    assert result.setup is None


def test_unresolved_video_wick_language_is_not_converted_to_numeric_threshold() -> None:
    anchor, reference, bars = _c2_case()
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.UNRESOLVED,
            observed_at=anchor,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.WICK_CLASSIFICATION_REQUIRED
    )


def test_source_bias_is_explicit_context_not_an_invented_daily_formula() -> None:
    anchor, reference, bars = _c2_case()
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            None,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=anchor,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.BIAS_CONTEXT_REQUIRED


def test_video_shallow_candle2_plus_reference_run_and_cisd_confirms_opportunity_but_not_entry() -> None:
    anchor, reference, bars = _c2_case()
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=anchor,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.SOURCE_EXECUTION_CONTRACT_INCOMPLETE
    )
    assert result.setup is None
    opportunity = result.confirmed_opportunity
    assert opportunity is not None
    assert opportunity.scenario is Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2
    assert opportunity.side is DemoTradingSetupSide.LONG
    assert opportunity.confirmation_price == Decimal("100")
    assert opportunity.protected_swing_extreme == Decimal("94.5")
    assert opportunity.executable_entry_price is None
    assert opportunity.take_profit is None


def test_video_large_candle2_does_not_get_forced_into_same_candle_trade() -> None:
    anchor, reference, bars = _c2_case()
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.LARGE,
            observed_at=anchor,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.WAIT_FOR_CANDLE3
    assert result.confirmed_opportunity is None


def test_video_large_candle2_reversal_then_shallow_candle3_cisd_is_confirmation_only() -> None:
    reference_open = datetime(2026, 1, 5, 1, 0, tzinfo=_NY)
    reference = _candle(
        reference_open,
        "100",
        "105",
        "95",
        "102",
        minutes=240,
    )
    candle2 = _candle(
        reference_open + timedelta(hours=4),
        "100",
        "103",
        "90",
        "98",
        minutes=240,
    )
    c3 = reference_open + timedelta(hours=8)
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
            observed_at=c3,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.SOURCE_EXECUTION_CONTRACT_INCOMPLETE
    )
    assert result.setup is None
    opportunity = result.confirmed_opportunity
    assert opportunity is not None
    assert opportunity.scenario is Vt08CrtH4AmdV2Scenario.CONTINUATION_EXPANSION_C3
    assert opportunity.protected_swing_extreme == Decimal("96")
    assert opportunity.executable_entry_price is None
    assert opportunity.take_profit is None


def test_post_confirmation_context_is_rejected_as_oracle_state() -> None:
    anchor, reference, bars = _c2_case()
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=anchor + timedelta(hours=1),
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.NON_CAUSAL_SOURCE_CONTEXT
    )
    assert result.confirmed_opportunity is None


def test_non_source_h4_open_is_rejected() -> None:
    anchor, reference, bars = _c2_case()
    shifted = anchor + timedelta(hours=1)
    shifted_bars = tuple(
        _candle(
            shifted + timedelta(minutes=15 * index),
            str(bar.open),
            str(bar.high),
            str(bar.low),
            str(bar.close),
        )
        for index, bar in enumerate(bars)
    )
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=shifted + timedelta(hours=4),
        observed_m15=shifted_bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=shifted,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert (
        result.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.OUTSIDE_SOURCE_H4_ANCHOR
    )


def test_non_m15_confirmation_evidence_is_rejected() -> None:
    anchor, reference, _ = _c2_case()
    bars = (
        _candle(anchor, "99", "99.5", "94.5", "96", minutes=5),
        _candle(anchor + timedelta(minutes=5), "96", "101", "95", "100", minutes=5),
    )
    result = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=anchor,
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.INVALID_M15_EVIDENCE


def test_universal_executable_entry_and_take_profit_are_explicitly_prohibited() -> None:
    with pytest.raises(Vt08CrtH4AmdV2ValidationError):
        Vt08CrtH4AmdV2ConfirmedOpportunity(
            side=DemoTradingSetupSide.LONG,
            scenario=Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2,
            confirmation_price=Decimal("100"),
            signal_at=datetime(2026, 1, 5, 1, 30, tzinfo=_NY),
            expires_at=datetime(2026, 1, 5, 5, 0, tzinfo=_NY),
            cisd_level=Decimal("99"),
            protected_swing_extreme=Decimal("95"),
            wick_profile=Vt08CrtH4AmdV2WickProfile.SHALLOW,
            executable_entry_price=Decimal("100"),  # type: ignore[arg-type]
            take_profit=Decimal("110"),  # type: ignore[arg-type]
        )
