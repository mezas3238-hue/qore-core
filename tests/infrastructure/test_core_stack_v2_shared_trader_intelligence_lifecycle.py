from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedAlertLifecycle,
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedIntelligenceClass,
    SharedOpportunityAlert,
    SharedOpportunityMaturity,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderCapability,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence_lifecycle import (
    SharedGlobalOpportunityBoard,
    build_trader_relevant_projection,
    transition_alert_lifecycle,
)

NOW = datetime(2026, 9, 29, 20, 30, tzinfo=UTC)
CUT = NOW - timedelta(seconds=1)


def _snapshot() -> SharedTraderIntelligenceSnapshot:
    return SharedTraderIntelligenceSnapshot(
        snapshot_id="snapshot-001",
        observed_at=NOW,
        evidence_cutoff_at=CUT,
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        market_family="METALS",
        trader_horizon="D1",
        world_state="TRANSITION",
        market_regime="TRENDING",
        macro_regime="DISINFLATIONARY",
        rates_state="FALLING",
        usd_state="WEAKENING",
        liquidity_state="NORMAL",
        volatility_state="ELEVATED",
        commodity_state="METALS_FIRM",
        agricultural_state="INSUFFICIENT",
        cross_asset_state="COHERENT",
        relationship_coherence=SharedSupportState.STRONG,
        relationship_stability=SharedSupportState.ELEVATED,
        relationship_age_ms=1_000,
        directional_hypothesis=(
            SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        ),
        continuation_support=SharedSupportState.ELEVATED,
        reversal_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.MODERATE,
        positive_tail_support=SharedSupportState.ELEVATED,
        systemic_stress=SharedSupportState.MODERATE,
        regime_transition_state=(
            SharedRegimeTransitionState.TRANSITION_DEVELOPING
        ),
        epistemic_state=SharedEpistemicState.PARTIALLY_KNOWN,
        uncertainty_bps=3000,
        confidence_bps=6000,
        confidence_calibration=(
            SharedConfidenceCalibrationState.UNCALIBRATED
        ),
        calibration_evidence_refs=(),
        data_quality_bps=9900,
        data_freshness_ms=200,
        causal_maturity="TEMPORAL_DEPENDENCY",
        supporting_evidence_refs=("fact:rates", "fact:usd"),
        contradicting_evidence_refs=(),
        missing_evidence=("missing:causal-certification",),
        provenance_refs=("world:001",),
        observation_horizon="H4",
        expected_validity_horizon="2D-5D",
        decay_horizon="24H",
    )


def _alert(
    *,
    alert_id: str = "alert-001",
    lifecycle: SharedAlertLifecycle = SharedAlertLifecycle.ACTIVE,
    maturity: SharedOpportunityMaturity = (
        SharedOpportunityMaturity.DEVELOPING
    ),
) -> SharedOpportunityAlert:
    return SharedOpportunityAlert(
        alert_id=alert_id,
        hypothesis_id="hypothesis-001",
        snapshot_id="snapshot-001",
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        created_at=NOW - timedelta(minutes=10),
        updated_at=NOW,
        evidence_cutoff_at=CUT,
        lifecycle=lifecycle,
        maturity=maturity,
        directional_hypothesis=(
            SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        ),
        expected_horizon="2D-5D",
        reason_codes=("USD_REGIME_WEAKENING",),
        evidence_refs=("fact:usd",),
    )


def _capability() -> SharedTraderCapability:
    return SharedTraderCapability(
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        markets=("XAUUSD",),
        horizons=("D1", "H4"),
        supported_intelligence_classes=(
            SharedIntelligenceClass.OPPORTUNITY,
            SharedIntelligenceClass.POSITION_THREAT,
            SharedIntelligenceClass.REGIME_TRANSITION,
        ),
        open_position_monitoring_capability=True,
    )


def test_unchanged_alert_state_is_deduplicated() -> None:
    transition = transition_alert_lifecycle(
        alert_id="alert-001",
        hypothesis_id="hypothesis-001",
        previous_state=SharedAlertLifecycle.ACTIVE,
        next_state=SharedAlertLifecycle.ACTIVE,
        transitioned_at=NOW,
        evidence_cutoff_at=CUT,
        reason_codes=("UNCHANGED_STATE",),
        provenance_refs=("snapshot:001",),
    )

    assert transition is None


def test_legal_alert_transition_is_auditable_and_deterministic() -> None:
    first = transition_alert_lifecycle(
        alert_id="alert-001",
        hypothesis_id="hypothesis-001",
        previous_state=SharedAlertLifecycle.ACTIVE,
        next_state=SharedAlertLifecycle.STRENGTHENING,
        transitioned_at=NOW,
        evidence_cutoff_at=CUT,
        reason_codes=("CONTINUATION_SUPPORT_RISING",),
        provenance_refs=("snapshot:001",),
    )
    second = transition_alert_lifecycle(
        alert_id="alert-001",
        hypothesis_id="hypothesis-001",
        previous_state=SharedAlertLifecycle.ACTIVE,
        next_state=SharedAlertLifecycle.STRENGTHENING,
        transitioned_at=NOW,
        evidence_cutoff_at=CUT,
        reason_codes=("CONTINUATION_SUPPORT_RISING",),
        provenance_refs=("snapshot:001",),
    )

    assert first is not None
    assert second is not None
    assert first.fingerprint() == second.fingerprint()


@pytest.mark.parametrize(
    "terminal",
    (
        SharedAlertLifecycle.RESOLVED,
        SharedAlertLifecycle.INVALIDATED,
        SharedAlertLifecycle.EXPIRED,
    ),
)
def test_terminal_alert_cannot_silently_resurrect(
    terminal: SharedAlertLifecycle,
) -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot transition or resurrect",
    ):
        transition_alert_lifecycle(
            alert_id="alert-001",
            hypothesis_id="hypothesis-001",
            previous_state=terminal,
            next_state=SharedAlertLifecycle.ACTIVE,
            transitioned_at=NOW,
            evidence_cutoff_at=CUT,
            reason_codes=("RESURRECTION_ATTEMPT",),
            provenance_refs=("snapshot:001",),
        )


def test_alert_transition_rejects_future_evidence() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot use future evidence",
    ):
        transition_alert_lifecycle(
            alert_id="alert-001",
            hypothesis_id="hypothesis-001",
            previous_state=SharedAlertLifecycle.ACTIVE,
            next_state=SharedAlertLifecycle.WEAKENING,
            transitioned_at=NOW,
            evidence_cutoff_at=NOW + timedelta(seconds=1),
            reason_codes=("FUTURE_EVIDENCE",),
            provenance_refs=("snapshot:001",),
        )


def test_empty_opportunity_board_is_valid() -> None:
    board = SharedGlobalOpportunityBoard(
        board_id="board-empty-001",
        as_of=NOW,
        evidence_cutoff_at=CUT,
        alerts=(),
    )

    assert board.is_empty is True
    assert board.ranking_is_order_priority is False
    assert board.execution_authority is False
    assert board.capital_authority is False
    assert board.risk_authority is False
    assert len(board.fingerprint()) == 64


def test_opportunity_board_is_attention_not_order_ranking() -> None:
    board = SharedGlobalOpportunityBoard(
        board_id="board-001",
        as_of=NOW,
        evidence_cutoff_at=CUT,
        alerts=(_alert(),),
    )

    assert board.is_empty is False

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="attention-only",
    ):
        SharedGlobalOpportunityBoard(
            board_id="board-002",
            as_of=NOW,
            evidence_cutoff_at=CUT,
            alerts=(_alert(),),
            ranking_is_order_priority=True,
        )


@pytest.mark.parametrize(
    ("lifecycle", "maturity"),
    (
        (
            SharedAlertLifecycle.RESOLVED,
            SharedOpportunityMaturity.DETERIORATING,
        ),
        (
            SharedAlertLifecycle.EXPIRED,
            SharedOpportunityMaturity.EXPIRED,
        ),
    ),
)
def test_terminal_or_expired_alert_cannot_remain_on_board(
    lifecycle: SharedAlertLifecycle,
    maturity: SharedOpportunityMaturity,
) -> None:
    with pytest.raises(SharedTraderIntelligenceValidationError):
        SharedGlobalOpportunityBoard(
            board_id="board-001",
            as_of=NOW,
            evidence_cutoff_at=CUT,
            alerts=(
                _alert(
                    lifecycle=lifecycle,
                    maturity=maturity,
                ),
            ),
        )


def test_projection_routes_only_supported_market_horizon_and_class() -> None:
    projection = build_trader_relevant_projection(
        projection_id="projection-001",
        snapshot=_snapshot(),
        capability=_capability(),
        projected_at=NOW + timedelta(seconds=1),
        intelligence_classes=(
            SharedIntelligenceClass.OPPORTUNITY,
            SharedIntelligenceClass.REGIME_TRANSITION,
        ),
        relevant_fact_refs=("fact:rates", "fact:usd"),
        omitted_fact_refs=("fact:irrelevant",),
    )

    assert projection.trader_id == "QORE_GLOBAL_MACRO_SWING_RESEARCH"
    assert projection.projection_changes_global_truth is False
    assert projection.execution_authority is False


def test_projection_rejects_unsupported_market() -> None:
    snapshot = _snapshot()
    capability = SharedTraderCapability(
        trader_id="OTHER-TRADER",
        markets=("EURUSD",),
        horizons=("D1",),
        supported_intelligence_classes=(
            SharedIntelligenceClass.OPPORTUNITY,
        ),
        open_position_monitoring_capability=False,
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="outside Trader routing capability",
    ):
        build_trader_relevant_projection(
            projection_id="projection-001",
            snapshot=snapshot,
            capability=capability,
            projected_at=NOW + timedelta(seconds=1),
            intelligence_classes=(SharedIntelligenceClass.OPPORTUNITY,),
            relevant_fact_refs=(),
            omitted_fact_refs=(),
        )


def test_projection_rejects_horizon_mismatch() -> None:
    capability = SharedTraderCapability(
        trader_id="OTHER-TRADER",
        markets=("XAUUSD",),
        horizons=("M1",),
        supported_intelligence_classes=(
            SharedIntelligenceClass.OPPORTUNITY,
        ),
        open_position_monitoring_capability=False,
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="horizon is outside",
    ):
        build_trader_relevant_projection(
            projection_id="projection-001",
            snapshot=_snapshot(),
            capability=capability,
            projected_at=NOW + timedelta(seconds=1),
            intelligence_classes=(SharedIntelligenceClass.OPPORTUNITY,),
            relevant_fact_refs=(),
            omitted_fact_refs=(),
        )


def test_projection_rejects_unsupported_intelligence_class() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="unsupported Trader intelligence class",
    ):
        build_trader_relevant_projection(
            projection_id="projection-001",
            snapshot=_snapshot(),
            capability=_capability(),
            projected_at=NOW + timedelta(seconds=1),
            intelligence_classes=(
                SharedIntelligenceClass.WORLD_EXPLANATION,
            ),
            relevant_fact_refs=(),
            omitted_fact_refs=(),
        )


def test_projection_cannot_consume_future_snapshot() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot consume future Shared snapshot",
    ):
        build_trader_relevant_projection(
            projection_id="projection-001",
            snapshot=_snapshot(),
            capability=_capability(),
            projected_at=NOW - timedelta(seconds=1),
            intelligence_classes=(SharedIntelligenceClass.OPPORTUNITY,),
            relevant_fact_refs=(),
            omitted_fact_refs=(),
        )
