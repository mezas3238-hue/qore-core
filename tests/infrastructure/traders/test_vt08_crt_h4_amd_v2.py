from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.contracts import DemoTradingDecision, DemoTradingSetupSide
from qore.infrastructure.traders.vt08_crt_h4_amd_v2 import (
    FOREX_H4_ANCHOR_HOURS,
    FUTURES_H4_ANCHOR_HOURS,
    SOURCE_FOREX_H4_ANCHOR_HOURS,
    SOURCE_FUTURES_H4_ANCHOR_HOURS,
    SOURCE_TIMING_AMBIGUOUS_MARKETS,
    SUPPORTED_MARKETS,
    Vt08CrtH4AmdV2AbstainReason,
    Vt08CrtH4AmdV2Candle,
    Vt08CrtH4AmdV2ConfirmedOpportunity,
    Vt08CrtH4AmdV2EntryModel,
    Vt08CrtH4AmdV2Evaluation,
    Vt08CrtH4AmdV2ExecutionPlan,
    Vt08CrtH4AmdV2PointOfInterest,
    Vt08CrtH4AmdV2PoiType,
    Vt08CrtH4AmdV2Scenario,
    Vt08CrtH4AmdV2SourceContext,
    Vt08CrtH4AmdV2TargetType,
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
    point_of_interest_reached: bool | None = True,
    execution_plan: Vt08CrtH4AmdV2ExecutionPlan | None = None,
) -> Vt08CrtH4AmdV2SourceContext:
    poi_provenance = (
        "human-owner-primary-video/source-defined-poi"
        if point_of_interest_reached is not None
        else None
    )
    return Vt08CrtH4AmdV2SourceContext(
        bias_side=side,
        wick_profile=wick,
        point_of_interest_reached=point_of_interest_reached,
        point_of_interest_provenance=poi_provenance,
        observed_at=observed_at,
        provenance="human-owner-primary-video/source-context",
        execution_plan=execution_plan,
    )


def _execution_plan(
    *,
    anchor: datetime,
    side: DemoTradingSetupSide = DemoTradingSetupSide.LONG,
    entry: str = "100",
    stop: str = "94.5",
    target: str = "111",
) -> Vt08CrtH4AmdV2ExecutionPlan:
    entry_price = Decimal(entry)
    return Vt08CrtH4AmdV2ExecutionPlan(
        entry_model=Vt08CrtH4AmdV2EntryModel.CISD_CONFIRMATION_CLOSE,
        entry_price=entry_price,
        methodological_stop=Decimal(stop),
        target_type=Vt08CrtH4AmdV2TargetType.CONDITIONED_TWO_R,
        target_price=Decimal(target),
        poi=Vt08CrtH4AmdV2PointOfInterest(
            poi_type=Vt08CrtH4AmdV2PoiType.FAIR_VALUE_GAP,
            timeframe="M15",
            formed_at=anchor,
            confirmed_at=anchor,
            lower_bound=entry_price - Decimal("1"),
            upper_bound=entry_price + Decimal("1"),
            direction=side,
            source_timestamp="06:15-06:44",
            evidence_ids=("video-example-fvg",),
            selection_reason="reached FVG preceding CISD",
        ),
        created_at=anchor,
        valid_until=anchor + timedelta(hours=4),
        source_timestamps=("06:15-06:44", "09:08-09:58"),
        evidence_ids=("cisd-confirmation", "protected-swing"),
    )


def _c2_case(
    anchor: datetime | None = None,
) -> tuple[datetime, Vt08CrtH4AmdV2Candle, tuple[Vt08CrtH4AmdV2Candle, ...]]:
    if anchor is None:
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


def test_v2_supports_only_owner_authorized_forex_and_futures_markets() -> None:
    assert set(SUPPORTED_MARKETS) == {
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
        "USDCAD",
        "NAS100",
        "SP500",
        "GBPJPY",
        "AUDJPY",
        "US30",
    }
    assert timing_family_for_market("EURUSD") is Vt08CrtH4AmdV2TimingFamily.FOREX
    assert timing_family_for_market("NAS100") is Vt08CrtH4AmdV2TimingFamily.FUTURES
    assert timing_family_for_market("XAUUSD") is None
    assert SOURCE_TIMING_AMBIGUOUS_MARKETS == frozenset()


def test_source_cycle_and_owner_operating_scope_are_kept_separate() -> None:
    assert SOURCE_FOREX_H4_ANCHOR_HOURS == (1, 5, 9, 13, 17, 21)
    assert SOURCE_FUTURES_H4_ANCHOR_HOURS == (2, 6, 10, 14, 18, 22)
    assert FOREX_H4_ANCHOR_HOURS == (1, 5, 9)
    assert FUTURES_H4_ANCHOR_HOURS == (2, 6, 10)
    assert source_anchor_hours_for_market("GBPUSD") == (1, 5, 9)
    assert source_anchor_hours_for_market("NAS100") == (2, 6, 10)
    assert source_anchor_hours_for_market("XAUUSD") is None


def test_source_anchor_is_new_york_dst_aware_in_winter_and_summer() -> None:
    for anchor_utc in (
        datetime(2026, 1, 5, 6, 0, tzinfo=UTC),
        datetime(2026, 7, 6, 5, 0, tzinfo=UTC),
    ):
        local_anchor = anchor_utc.astimezone(_NY)
        assert local_anchor.hour == 1
        anchor, reference, bars = _c2_case(local_anchor)
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
        assert result.confirmed_opportunity is not None
        assert (
            result.abstain_reason
            is Vt08CrtH4AmdV2AbstainReason.EXECUTION_PLAN_REQUIRED
        )


def test_xauusd_is_outside_owner_forex_and_futures_scope() -> None:
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
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.UNSUPPORTED_MARKET
    assert result.confirmed_opportunity is None
    assert result.setup is None


def test_source_poi_reach_is_required_before_cisd_confirmation() -> None:
    anchor, reference, bars = _c2_case()
    unresolved = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=anchor,
            point_of_interest_reached=None,
        ),
    )
    assert unresolved.decision is DemoTradingDecision.ABSTAIN
    assert (
        unresolved.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.POINT_OF_INTEREST_REQUIRED
    )

    absent = evaluate_reversal_expansion_candle2(
        symbol="EURUSD",
        h4_reference=reference,
        h4_candle2_closes_at=anchor + timedelta(hours=4),
        observed_m15=bars,
        context=_context(
            DemoTradingSetupSide.LONG,
            Vt08CrtH4AmdV2WickProfile.SHALLOW,
            observed_at=anchor,
            point_of_interest_reached=False,
        ),
    )
    assert absent.decision is DemoTradingDecision.ABSTAIN
    assert (
        absent.abstain_reason
        is Vt08CrtH4AmdV2AbstainReason.POINT_OF_INTEREST_NOT_REACHED
    )


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


def test_video_shallow_candle2_plus_reference_run_and_cisd_without_plan_abstains_locally(
) -> None:
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
        is Vt08CrtH4AmdV2AbstainReason.EXECUTION_PLAN_REQUIRED
    )
    assert result.setup is None
    opportunity = result.confirmed_opportunity
    assert opportunity is not None
    assert opportunity.scenario is Vt08CrtH4AmdV2Scenario.REVERSAL_EXPANSION_C2
    assert opportunity.side is DemoTradingSetupSide.LONG
    assert opportunity.confirmation_price == Decimal("100")
    assert opportunity.protected_swing_extreme == Decimal("94.5")
    assert opportunity.point_of_interest_provenance.endswith("source-defined-poi")
    assert opportunity.executable_entry_price is None
    assert opportunity.take_profit is None


def test_candle2_resolved_source_plan_emits_exact_long_setup() -> None:
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
            execution_plan=_execution_plan(anchor=anchor),
        ),
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.setup is not None
    assert result.setup.entry_price == Decimal("100")
    assert result.setup.stop_price == Decimal("94.5")
    assert result.setup.target_price == Decimal("111")
    assert result.setup.expected_r == Decimal("2")
    assert result.setup.source_identity == "youtube:FAKWJ-1NlLE"
    assert len(result.setup.evidence_fingerprint) == 64


def test_conditioned_two_r_target_cannot_hide_different_geometry() -> None:
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
            execution_plan=_execution_plan(anchor=anchor, target="110"),
        ),
    )
    assert result.decision is DemoTradingDecision.ABSTAIN
    assert result.abstain_reason is Vt08CrtH4AmdV2AbstainReason.INVALID_TARGET


def test_same_evidence_produces_identical_setup_and_fingerprints() -> None:
    anchor, reference, bars = _c2_case()
    context = _context(
        DemoTradingSetupSide.LONG,
        Vt08CrtH4AmdV2WickProfile.SHALLOW,
        observed_at=anchor,
        execution_plan=_execution_plan(anchor=anchor),
    )

    def evaluate() -> Vt08CrtH4AmdV2Evaluation:
        return evaluate_reversal_expansion_candle2(
            symbol="EURUSD",
            h4_reference=reference,
            h4_candle2_closes_at=anchor + timedelta(hours=4),
            observed_m15=bars,
            context=context,
        )

    first = evaluate()
    second = evaluate()
    assert first == second
    assert first.setup is not None
    assert second.setup is not None
    assert first.setup.evidence_fingerprint == second.setup.evidence_fingerprint
    assert first.methodology_fingerprint == second.methodology_fingerprint


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


def test_video_large_candle2_reversal_then_shallow_candle3_cisd_can_emit_setup() -> None:
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
            execution_plan=_execution_plan(
                anchor=c3,
                entry="99",
                stop="96",
                target="105",
            ),
        ),
    )
    assert result.decision is DemoTradingDecision.SETUP
    assert result.abstain_reason is None
    assert result.setup is not None
    assert result.setup.entry_price == Decimal("99")
    assert result.setup.stop_price == Decimal("96")
    assert result.setup.target_price == Decimal("105")
    assert result.setup.expected_r == Decimal("2")
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


def test_source_cycle_anchor_outside_owner_operating_scope_is_rejected() -> None:
    anchor = datetime(2026, 1, 5, 13, 0, tzinfo=_NY)
    _, reference, bars = _c2_case(anchor)
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


def test_legacy_confirmed_opportunity_still_cannot_smuggle_untyped_geometry() -> None:
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
            point_of_interest_provenance="primary-video/source-defined-poi",
            executable_entry_price=Decimal("100"),  # type: ignore[arg-type]
            take_profit=Decimal("110"),  # type: ignore[arg-type]
        )
