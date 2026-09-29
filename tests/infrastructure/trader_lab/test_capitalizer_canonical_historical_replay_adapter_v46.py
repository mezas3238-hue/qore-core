from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_historical_replay_adapter_v46 as adapter,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCausalSeriesKind,
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
    CapitalizerLiquiditySideTaken,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    derive_daily_bias,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    CapitalizerFractalAlignmentObservation,
    assess_fractal_alignment,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceClosureKind,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)

DECISION = datetime(2024, 1, 15, 8, 30, tzinfo=UTC)
DIRECTION = CapitalizerSourceDirection.BULLISH


def _closure() -> CapitalizerSourceClosureObservation:
    return CapitalizerSourceClosureObservation(
        kind=CapitalizerSourceClosureKind.CANDLE2_REVERSAL,
        direction=DIRECTION,
        point_of_interest_present=True,
        source_rule_satisfied=True,
        reasons=("TEST_HTF_CLOSURE",),
    )


def _cisd() -> CapitalizerCISDObservation:
    return CapitalizerCISDObservation(
        direction=DIRECTION,
        causal_series_kind=CapitalizerCausalSeriesKind.DOWN_CLOSE_SERIES,
        causal_series_open=Decimal("100"),
        confirmation_close=Decimal("101"),
        important_level_reached=True,
        higher_timeframe_closure_confirmed=True,
        structural_confirmed=True,
        setup_confirmed=True,
        reasons=("TEST_CISD",),
    )


def _protected() -> CapitalizerProtectedSwingObservation:
    return CapitalizerProtectedSwingObservation(
        direction=DIRECTION,
        swing_price=Decimal("99"),
        origin=CapitalizerProtectedSwingOrigin.FAIR_VALUE_GAP,
        closure_through_causal_series_confirmed=True,
        confirmed=True,
        reasons=("TEST_PROTECTED_SWING",),
    )


def _fractal() -> CapitalizerFractalAlignmentObservation:
    closure = _closure()
    return assess_fractal_alignment(
        higher_timeframe_bias=DIRECTION,
        h1_closure=closure,
        m15_cisd=_cisd(),
        m1_protected_swing=_protected(),
    )


def _target(
    *,
    second: bool = False,
) -> remediation.CapitalizerStructuralTargetResolution:
    candidates = [
        remediation.CapitalizerStructuralTargetCandidate(
            kind=CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW,
            target_price=Decimal("105"),
            observed_at=DECISION - timedelta(hours=2),
            untouched=True,
            higher_timeframe=True,
        )
    ]
    if second:
        candidates.append(
            remediation.CapitalizerStructuralTargetCandidate(
                kind=(
                    CapitalizerSourceTargetKind
                    .HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE
                ),
                target_price=Decimal("107"),
                observed_at=DECISION - timedelta(hours=3),
                untouched=True,
                higher_timeframe=True,
            )
        )
    return remediation.resolve_structural_target(
        direction=DIRECTION,
        entry_price=Decimal("100"),
        decision_at=DECISION,
        candidates=tuple(candidates),
    )


def _no_chase() -> remediation.CapitalizerNoChaseObservation:
    return remediation.assess_no_chase_entry(
        entry_price=Decimal("100"),
        pd_array_lower=Decimal("99.5"),
        pd_array_upper=Decimal("100.5"),
        pd_array_confirmed_at=DECISION - timedelta(minutes=3),
        entry_at=DECISION,
    )


def _wick() -> remediation.CapitalizerWickFormationObservation:
    return remediation.assess_wick_formation(
        direction=DIRECTION,
        important_level_reached=True,
        intracandle_cisd=_cisd(),
        protected_swing=_protected(),
    )


def _m1_mss() -> remediation.CapitalizerM1MSSObservation:
    return remediation.CapitalizerM1MSSObservation(
        direction=DIRECTION,
        swing_price=Decimal("99.8"),
        confirmed_at=DECISION - timedelta(minutes=2),
        confirmed=True,
        future_bar_used=False,
        reasons=("TEST_M1_MSS",),
    )


def _m1_ob() -> remediation.CapitalizerM1OrderBlockObservation:
    series = (
        CapitalizerSourceBar(
            open=Decimal("100.2"),
            high=Decimal("100.4"),
            low=Decimal("99.7"),
            close=Decimal("99.9"),
        ),
    )
    return remediation.assess_m1_order_block(
        direction=DIRECTION,
        causal_series=series,
        poi_reached=True,
        cisd=_cisd(),
    )


def _stamps(
    *,
    future_key: str | None = None,
) -> tuple[adapter.CapitalizerHistoricalEvidenceStamp, ...]:
    return tuple(
        adapter.CapitalizerHistoricalEvidenceStamp(
            key=key,
            observed_at=(
                DECISION + timedelta(minutes=1)
                if key == future_key
                else DECISION - timedelta(minutes=1)
            ),
        )
        for key in sorted(adapter.REQUIRED_EVIDENCE_KEYS)
    )


def _bundle(
    *,
    session: CapitalizerSession = CapitalizerSession.LONDON,
    symbol: str = "EURUSD",
    target: remediation.CapitalizerStructuralTargetResolution | None = None,
    fractal: CapitalizerFractalAlignmentObservation | None = None,
    ftm: CapitalizerFailureToManipulateObservation | None = None,
    stamps: tuple[adapter.CapitalizerHistoricalEvidenceStamp, ...] | None = None,
) -> adapter.CapitalizerCanonicalHistoricalBundle:
    closure = _closure()
    return adapter.CapitalizerCanonicalHistoricalBundle(
        symbol=symbol,
        side=CapitalizerSide.LONG,
        session=session,
        decision_at=DECISION,
        cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
        entry_price=Decimal("100"),
        daily_bias=derive_daily_bias(closure),
        htf_closure=closure,
        structural_target=_target() if target is None else target,
        protected_swing=_protected(),
        ict=adapter.CapitalizerCanonicalICTFacts(
            liquidity_reference_defined=True,
            liquidity_raid_observed=True,
            market_structure_shift_confirmed=True,
            displacement_significant=True,
            fvg_present_in_displacement=True,
            entry_retrace_into_valid_pd_array=True,
        ),
        no_chase=_no_chase(),
        ltf_cisd=_cisd(),
        fractal_alignment=_fractal() if fractal is None else fractal,
        failure_to_manipulate=ftm,
        wick_formation=_wick(),
        m1_mss=_m1_mss(),
        m1_fvg_confirmed=True,
        m1_order_block=_m1_ob(),
        evidence_timestamps=_stamps() if stamps is None else stamps,
    )


def test_valid_london_bundle_passes_both_gates_to_structural_plan() -> None:
    result = adapter.assess_canonical_historical_bundle(_bundle())

    assert result.dual_source_entry_acceptance.passes_to_qore_risk is True
    assert result.source_engine_assessment is not None
    assert result.source_engine_assessment.passes_to_qore_risk is True
    assert result.passes_to_qore_risk is True
    assert result.trade_plan_built is True

    plan = result.source_engine_assessment.trade_plan
    assert plan is not None
    assert plan.initial_stop_price == Decimal("99")
    assert plan.target_price == Decimal("105")
    assert plan.fixed_r_target_invented is False
    assert result.fixed_r_target_used is False
    assert result.outcome_aware is False


def test_asia_without_authentic_open_reference_fails_closed() -> None:
    bundle = _bundle(
        session=CapitalizerSession.ASIA,
        symbol="AUDUSD",
    )

    result = adapter.assess_canonical_historical_bundle(bundle)

    assert result.source_session.resolved is False
    assert result.source_session.eligible is False
    assert result.dual_source_entry_acceptance.passes_to_qore_risk is False
    assert result.passes_to_qore_risk is False
    assert result.trade_plan_built is False


def test_future_evidence_is_rejected_before_any_gate() -> None:
    with pytest.raises(ValueError, match="future evidence prohibited"):
        _bundle(stamps=_stamps(future_key="M1_MSS"))


def test_ambiguous_route_fails_closed_without_trade_plan() -> None:
    ftm = CapitalizerFailureToManipulateObservation(
        taken_side=CapitalizerLiquiditySideTaken.HIGH,
        continuation_direction=DIRECTION,
        expected_reversal_direction=CapitalizerSourceDirection.BEARISH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd_confirmed=False,
        continuation_protected_swing_confirmed=True,
        higher_timeframe_bias_aligned=True,
        confirmed=True,
        reasons=("TEST_FTM",),
    )

    result = adapter.assess_canonical_historical_bundle(
        _bundle(ftm=ftm)
    )

    assert result.route_resolution.resolved is False
    assert result.source_engine_assessment is None
    assert result.passes_to_qore_risk is False
    assert result.trade_plan_built is False


def test_ambiguous_target_cannot_create_trade_plan() -> None:
    unresolved = _target(second=True)
    assert unresolved.resolved is False

    result = adapter.assess_canonical_historical_bundle(
        _bundle(target=unresolved)
    )

    assert result.dual_source_entry_acceptance.passes_to_qore_risk is False
    assert result.source_engine_assessment is None
    assert result.passes_to_qore_risk is False
    assert result.trade_plan_built is False


def test_evidence_timestamp_keys_are_exact_and_unique() -> None:
    bundle = _bundle()
    assert {stamp.key for stamp in bundle.evidence_timestamps} == set(
        adapter.REQUIRED_EVIDENCE_KEYS
    )

    duplicate = (*bundle.evidence_timestamps[:-1], bundle.evidence_timestamps[0])
    with pytest.raises(ValueError, match="duplicate keys"):
        replace(bundle, evidence_timestamps=duplicate)
