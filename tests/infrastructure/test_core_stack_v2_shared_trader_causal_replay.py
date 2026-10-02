from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_position_world_lineage import (
    capture_position_entry_world,
    compare_position_world_now,
)
from qore.infrastructure.core_stack_v2.shared_trader_causal_replay import (
    SharedTraderCausalReplayFrame,
    SharedTraderCausalReplaySequence,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
    TraderSharedOpportunityAssessment,
    TraderSharedOpportunityDisposition,
)

T0 = datetime(2026, 9, 29, 20, 0, tzinfo=UTC)
SHA_A = "a" * 64
SHA_B = "b" * 64


def _snapshot(
    *,
    snapshot_id: str,
    observed_at: datetime,
    evidence_cutoff_at: datetime,
) -> SharedTraderIntelligenceSnapshot:
    return SharedTraderIntelligenceSnapshot(
        snapshot_id=snapshot_id,
        observed_at=observed_at,
        evidence_cutoff_at=evidence_cutoff_at,
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        market_family="METALS",
        trader_horizon="D1",
        world_state="RISK_ON",
        market_regime="TRENDING",
        macro_regime="DISINFLATIONARY",
        rates_state="FALLING",
        usd_state="WEAKENING",
        liquidity_state="NORMAL",
        volatility_state="NORMAL",
        commodity_state="METALS_FIRM",
        agricultural_state="INSUFFICIENT",
        cross_asset_state="COHERENT",
        relationship_coherence=SharedSupportState.STRONG,
        relationship_stability=SharedSupportState.STRONG,
        relationship_age_ms=1_000,
        directional_hypothesis=(
            SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
        ),
        continuation_support=SharedSupportState.ELEVATED,
        reversal_support=SharedSupportState.LOW,
        failure_hazard=SharedSupportState.LOW,
        positive_tail_support=SharedSupportState.ELEVATED,
        systemic_stress=SharedSupportState.LOW,
        regime_transition_state=SharedRegimeTransitionState.STABLE,
        epistemic_state=SharedEpistemicState.PARTIALLY_KNOWN,
        uncertainty_bps=2500,
        confidence_bps=6500,
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


def _assessment(assessed_at: datetime) -> TraderSharedOpportunityAssessment:
    return TraderSharedOpportunityAssessment(
        alert_id="alert-001",
        trader_id="TRADER-001",
        assessed_at=assessed_at,
        disposition=TraderSharedOpportunityDisposition.WAIT,
        methodology_validated=False,
        evidence_refs=("trader:setup-not-ready",),
    )


def _frame(
    *,
    frame_id: str = "frame-001",
    decision_time: datetime = T0,
) -> SharedTraderCausalReplayFrame:
    snapshot = _snapshot(
        snapshot_id="snapshot-001",
        observed_at=T0 - timedelta(seconds=2),
        evidence_cutoff_at=T0 - timedelta(seconds=3),
    )
    return SharedTraderCausalReplayFrame(
        frame_id=frame_id,
        decision_time=decision_time,
        shared_snapshot=snapshot,
        trader_assessment=_assessment(T0 - timedelta(seconds=1)),
        position_entry_world=None,
        position_world_delta=None,
        source_data_fingerprints=(SHA_A,),
        policy_fingerprints=(SHA_B,),
        provenance_refs=("replay:source-001",),
    )


def test_replay_frame_is_deterministic_and_future_free() -> None:
    first = _frame()
    second = _frame()

    assert first.fingerprint() == second.fingerprint()
    assert first.future_market_data_used is False
    assert first.future_outcome_used is False
    assert first.future_report_used is False
    assert first.future_weather_used is False
    assert first.future_roll_state_used is False
    assert first.outcome_evidence_refs == ()
    assert first.productive_behavior_authority is False


def test_replay_rejects_future_shared_snapshot() -> None:
    frame = _frame()
    future = replace(
        frame.shared_snapshot,
        observed_at=T0 + timedelta(seconds=1),
        evidence_cutoff_at=T0,
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="snapshot from the future",
    ):
        replace(frame, shared_snapshot=future)


def test_replay_rejects_future_trader_assessment() -> None:
    frame = _frame()

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="future Trader assessment",
    ):
        replace(
            frame,
            trader_assessment=_assessment(T0 + timedelta(seconds=1)),
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "future_market_data_used",
        "future_outcome_used",
        "future_report_used",
        "future_weather_used",
        "future_roll_state_used",
    ),
)
def test_replay_rejects_every_future_information_class(
    field_name: str,
) -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="future information",
    ):
        replace(_frame(), **{field_name: True})


def test_replay_rejects_outcome_evidence_inside_decision_frame() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot contain outcome evidence",
    ):
        replace(
            _frame(),
            outcome_evidence_refs=("outcome:future-profit",),
        )


def test_replay_tracks_position_only_after_it_exists() -> None:
    entry_snapshot = _snapshot(
        snapshot_id="snapshot-entry-001",
        observed_at=T0 - timedelta(seconds=1),
        evidence_cutoff_at=T0 - timedelta(seconds=2),
    )
    entry = capture_position_entry_world(
        entry_world_record_id="entry-world-001",
        position_id="position-001",
        trader_id="TRADER-001",
        opened_at=T0,
        snapshot=entry_snapshot,
        provenance_refs=("position-open:001",),
    )
    current_snapshot = _snapshot(
        snapshot_id="snapshot-current-002",
        observed_at=T0 + timedelta(hours=1),
        evidence_cutoff_at=T0 + timedelta(hours=1) - timedelta(seconds=1),
    )
    delta = compare_position_world_now(
        delta_observation_id="delta-001",
        entry=entry,
        current_snapshot=current_snapshot,
        compared_at=current_snapshot.observed_at,
        provenance_refs=("entry-world:001",),
    )
    frame = SharedTraderCausalReplayFrame(
        frame_id="frame-position-001",
        decision_time=current_snapshot.observed_at,
        shared_snapshot=current_snapshot,
        trader_assessment=None,
        position_entry_world=entry,
        position_world_delta=delta,
        source_data_fingerprints=(SHA_A,),
        policy_fingerprints=(SHA_B,),
        provenance_refs=("replay:position-001",),
    )

    assert frame.position_entry_world is not None
    assert frame.position_world_delta is not None


def test_replay_rejects_position_that_did_not_exist_yet() -> None:
    frame = _frame()
    future_open = T0 + timedelta(seconds=1)
    future_entry = capture_position_entry_world(
        entry_world_record_id="entry-world-001",
        position_id="position-001",
        trader_id="TRADER-001",
        opened_at=future_open,
        snapshot=_snapshot(
            snapshot_id="snapshot-entry-001",
            observed_at=T0,
            evidence_cutoff_at=T0 - timedelta(seconds=1),
        ),
        provenance_refs=("position-open:001",),
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="future position",
    ):
        replace(frame, position_entry_world=future_entry)


def test_replay_sequence_must_be_chronological_and_unique() -> None:
    first = _frame(frame_id="frame-001", decision_time=T0)
    second = replace(
        _frame(
            frame_id="frame-002",
            decision_time=T0 + timedelta(minutes=1),
        ),
        shared_snapshot=_snapshot(
            snapshot_id="snapshot-002",
            observed_at=T0,
            evidence_cutoff_at=T0 - timedelta(seconds=1),
        ),
        trader_assessment=None,
    )

    sequence = SharedTraderCausalReplaySequence(
        replay_id="replay-001",
        dataset_fingerprint=SHA_A,
        frames=(first, second),
        protected_holdout=False,
    )
    assert len(sequence.fingerprint()) == 64

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="chronological and deterministic",
    ):
        replace(sequence, frames=(second, first))

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="frame ids must be unique",
    ):
        replace(sequence, frames=(first, first))


def test_protected_holdout_cannot_open_without_explicit_authorization() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="requires explicit authorization",
    ):
        SharedTraderCausalReplaySequence(
            replay_id="replay-protected-001",
            dataset_fingerprint=SHA_A,
            frames=(_frame(),),
            protected_holdout=True,
            protected_holdout_open_authorized=False,
        )


def test_replay_cannot_mutate_policy_or_productive_behavior() -> None:
    sequence = SharedTraderCausalReplaySequence(
        replay_id="replay-001",
        dataset_fingerprint=SHA_A,
        frames=(_frame(),),
        protected_holdout=False,
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot mutate policy or productive behavior",
    ):
        replace(sequence, outcome_aware_policy_mutation=True)
