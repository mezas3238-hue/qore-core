from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as r1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCausalSeriesKind,
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
    CapitalizerLiquiditySideTaken,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    CapitalizerFractalAlignmentObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    CapitalizerSourcePOIKind,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    CapitalizerSourceEntryRoute,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)


def _bar(
    index: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM1Bar:
    opened = datetime(2024, 1, 1, 12, index, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=5,
    )


def _cisd(direction: CapitalizerSourceDirection) -> CapitalizerCISDObservation:
    return CapitalizerCISDObservation(
        direction=direction,
        causal_series_kind=(
            CapitalizerCausalSeriesKind.DOWN_CLOSE_SERIES
            if direction is CapitalizerSourceDirection.BULLISH
            else CapitalizerCausalSeriesKind.UP_CLOSE_SERIES
        ),
        causal_series_open=Decimal("100"),
        confirmation_close=Decimal("101"),
        important_level_reached=True,
        higher_timeframe_closure_confirmed=True,
        structural_confirmed=True,
        setup_confirmed=True,
        reasons=("TEST",),
    )


def _protected(
    direction: CapitalizerSourceDirection,
) -> CapitalizerProtectedSwingObservation:
    return CapitalizerProtectedSwingObservation(
        direction=direction,
        swing_price=Decimal("99"),
        origin=CapitalizerProtectedSwingOrigin.FAIR_VALUE_GAP,
        closure_through_causal_series_confirmed=True,
        confirmed=True,
        reasons=("TEST",),
    )


def test_no_chase_requires_entry_to_remain_inside_confirmed_pd_array() -> None:
    confirmed = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    entry = confirmed + timedelta(minutes=1)

    inside = r1.assess_no_chase_entry(
        entry_price=Decimal("100.5"),
        pd_array_lower=Decimal("100"),
        pd_array_upper=Decimal("101"),
        pd_array_confirmed_at=confirmed,
        entry_at=entry,
    )
    outside = r1.assess_no_chase_entry(
        entry_price=Decimal("101.1"),
        pd_array_lower=Decimal("100"),
        pd_array_upper=Decimal("101"),
        pd_array_confirmed_at=confirmed,
        entry_at=entry,
    )

    assert inside.confirmed is True
    assert outside.confirmed is False
    assert inside.tolerance_used is False


def test_target_resolver_fails_closed_on_multiple_valid_targets() -> None:
    now = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    candidates = (
        r1.CapitalizerStructuralTargetCandidate(
            kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
            target_price=Decimal("105"),
            observed_at=now - timedelta(hours=1),
            untouched=True,
            higher_timeframe=True,
        ),
        r1.CapitalizerStructuralTargetCandidate(
            kind=CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            target_price=Decimal("107"),
            observed_at=now - timedelta(hours=2),
            untouched=True,
            higher_timeframe=True,
        ),
    )

    result = r1.resolve_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        decision_at=now,
        candidates=candidates,
    )

    assert result.resolved is False
    assert result.observation is None
    assert result.numeric_priority_used is False


def test_target_resolver_accepts_one_unambiguous_causal_target() -> None:
    now = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    candidate = r1.CapitalizerStructuralTargetCandidate(
        kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
        target_price=Decimal("105"),
        observed_at=now - timedelta(hours=1),
        untouched=True,
        higher_timeframe=True,
    )

    result = r1.resolve_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=Decimal("100"),
        decision_at=now,
        candidates=(candidate,),
    )

    assert result.resolved is True
    assert result.observation is not None
    assert result.observation.target_price == Decimal("105")


def test_wick_formation_requires_level_cisd_and_protected_swing() -> None:
    direction = CapitalizerSourceDirection.BULLISH
    result = r1.assess_wick_formation(
        direction=direction,
        important_level_reached=True,
        intracandle_cisd=_cisd(direction),
        protected_swing=_protected(direction),
    )
    missing = r1.assess_wick_formation(
        direction=direction,
        important_level_reached=True,
        intracandle_cisd=None,
        protected_swing=_protected(direction),
    )

    assert result.confirmed is True
    assert missing.confirmed is False
    assert result.numeric_wick_threshold_used is False


def test_m1_mss_confirms_first_close_through_latest_swing() -> None:
    bars = (
        _bar(0, open_="100", high="101", low="99", close="100"),
        _bar(1, open_="100", high="103", low="99.5", close="101"),
        _bar(2, open_="101", high="102", low="100", close="101"),
        _bar(3, open_="101", high="104.5", low="100.5", close="104"),
    )

    result = r1.detect_m1_mss(
        bars=bars,
        direction=CapitalizerSourceDirection.BULLISH,
        after=bars[2].opened_at,
        before=bars[3].closed_at,
    )

    assert result.confirmed is True
    assert result.swing_price == Decimal("103")
    assert result.confirmed_at == bars[3].closed_at
    assert result.future_bar_used is False


def test_m1_order_block_requires_opposing_series_poi_and_cisd() -> None:
    series = (
        CapitalizerSourceBar(
            open=Decimal("101"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("100"),
        ),
    )
    result = r1.assess_m1_order_block(
        direction=CapitalizerSourceDirection.BULLISH,
        causal_series=series,
        poi_reached=True,
        cisd=_cisd(CapitalizerSourceDirection.BULLISH),
    )

    assert result.confirmed is True
    assert result.opposing_candle_count == 1


def test_route_resolver_never_invents_priority_when_both_confirm() -> None:
    direction = CapitalizerSourceDirection.BULLISH
    fractal = CapitalizerFractalAlignmentObservation(
        direction=direction,
        higher_timeframe_bias_aligned=True,
        h1_closure_confirmed=True,
        m15_cisd_confirmed=True,
        m1_protected_swing_confirmed=True,
        confirmed=True,
        reasons=("TEST",),
    )
    ftm = CapitalizerFailureToManipulateObservation(
        taken_side=CapitalizerLiquiditySideTaken.HIGH,
        continuation_direction=direction,
        expected_reversal_direction=CapitalizerSourceDirection.BEARISH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd_confirmed=False,
        continuation_protected_swing_confirmed=True,
        higher_timeframe_bias_aligned=True,
        confirmed=True,
        reasons=("TEST",),
    )

    ambiguous = r1.resolve_source_entry_route(
        fractal_alignment=fractal,
        failure_to_manipulate=ftm,
    )
    fractal_only = r1.resolve_source_entry_route(
        fractal_alignment=fractal,
        failure_to_manipulate=None,
    )

    assert ambiguous.resolved is False
    assert ambiguous.route is None
    assert fractal_only.route is CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION


def test_htf_poi_context_retains_all_interactions_without_ranking() -> None:
    bar = CapitalizerSourceBar(
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("102"),
    )
    pois = (
        CapitalizerSourcePOI(
            kind=CapitalizerSourcePOIKind.SWING_LOW,
            lower_price=Decimal("96"),
            upper_price=Decimal("96"),
            source_bar_count=3,
        ),
        CapitalizerSourcePOI(
            kind=CapitalizerSourcePOIKind.BULLISH_FVG,
            lower_price=Decimal("101"),
            upper_price=Decimal("103"),
            source_bar_count=3,
        ),
    )

    result = r1.resolve_htf_poi_context(bar=bar, pois=pois)

    assert result.present is True
    assert len(result.interacting_pois) == 2
    assert result.numeric_score_used is False
