from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_position_world_lineage import (
    SharedPositionEntryWorldRecord,
    capture_position_entry_world,
    compare_position_world_now,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedConfidenceCalibrationState,
    SharedDirectionalHypothesis,
    SharedEpistemicState,
    SharedRegimeTransitionState,
    SharedSupportState,
    SharedTraderIntelligenceSnapshot,
    SharedTraderIntelligenceValidationError,
)

OPENED_AT = datetime(2026, 9, 29, 20, 30, tzinfo=UTC)
ENTRY_OBSERVED_AT = OPENED_AT - timedelta(milliseconds=500)
ENTRY_CUTOFF_AT = ENTRY_OBSERVED_AT - timedelta(milliseconds=100)


def _snapshot(
    *,
    snapshot_id: str,
    observed_at: datetime,
    evidence_cutoff_at: datetime,
    world_state: str = "RISK_ON",
    market_regime: str = "TRENDING",
    macro_regime: str = "DISINFLATIONARY",
    coherence: SharedSupportState = SharedSupportState.STRONG,
    stability: SharedSupportState = SharedSupportState.STRONG,
) -> SharedTraderIntelligenceSnapshot:
    return SharedTraderIntelligenceSnapshot(
        snapshot_id=snapshot_id,
        observed_at=observed_at,
        evidence_cutoff_at=evidence_cutoff_at,
        asset="XAUUSD",
        canonical_instrument_id="canonical:XAUUSD",
        market_family="METALS",
        trader_horizon="D1",
        world_state=world_state,
        market_regime=market_regime,
        macro_regime=macro_regime,
        rates_state="FALLING",
        usd_state="WEAKENING",
        liquidity_state="NORMAL",
        volatility_state="NORMAL",
        commodity_state="METALS_FIRM",
        agricultural_state="INSUFFICIENT",
        cross_asset_state="COHERENT",
        relationship_coherence=coherence,
        relationship_stability=stability,
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
        missing_evidence=("missing:certified-causal-edge",),
        provenance_refs=("world:entry",),
        observation_horizon="H4",
        expected_validity_horizon="2D-5D",
        decay_horizon="24H",
    )


def _entry_snapshot() -> SharedTraderIntelligenceSnapshot:
    return _snapshot(
        snapshot_id="snapshot-entry-001",
        observed_at=ENTRY_OBSERVED_AT,
        evidence_cutoff_at=ENTRY_CUTOFF_AT,
    )


def _entry_record() -> SharedPositionEntryWorldRecord:
    return capture_position_entry_world(
        entry_world_record_id="entry-world-001",
        position_id="position-001",
        trader_id="QORE_GLOBAL_MACRO_SWING_RESEARCH",
        opened_at=OPENED_AT,
        snapshot=_entry_snapshot(),
        provenance_refs=(
            "position-open:event-001",
            "snapshot:entry-001",
        ),
    )


def test_entry_world_is_bound_to_opening_event_and_preopen_snapshot() -> None:
    entry = _entry_record()

    assert entry.captured_at == OPENED_AT
    assert entry.snapshot_observed_at < OPENED_AT
    assert entry.post_hoc_reconstruction is False
    assert entry.position_management_authority is False
    assert entry.execution_authority is False
    assert entry.snapshot_fingerprint == _entry_snapshot().fingerprint()
    assert len(entry.fingerprint()) == 64


def test_entry_world_rejects_snapshot_observed_after_position_open() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="observed after position open",
    ):
        capture_position_entry_world(
            entry_world_record_id="entry-world-001",
            position_id="position-001",
            trader_id="TRADER-001",
            opened_at=OPENED_AT,
            snapshot=_snapshot(
                snapshot_id="snapshot-future-001",
                observed_at=OPENED_AT + timedelta(microseconds=1),
                evidence_cutoff_at=OPENED_AT,
            ),
            provenance_refs=("position-open:event-001",),
        )


def test_entry_world_rejects_post_hoc_commit_time() -> None:
    entry = _entry_record()

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="committed at the position opening event",
    ):
        replace(
            entry,
            captured_at=OPENED_AT + timedelta(seconds=1),
        )


def test_entry_world_cannot_claim_position_management_authority() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="causal observation only",
    ):
        replace(
            _entry_record(),
            position_management_authority=True,
        )


def test_world_now_delta_is_factual_not_threat_or_exit_command() -> None:
    current = _snapshot(
        snapshot_id="snapshot-current-002",
        observed_at=OPENED_AT + timedelta(hours=4),
        evidence_cutoff_at=OPENED_AT + timedelta(hours=4) - timedelta(seconds=1),
        world_state="TRANSITION",
        market_regime="WEAKENING_TREND",
        macro_regime="TRANSITION",
        coherence=SharedSupportState.LOW,
        stability=SharedSupportState.MODERATE,
    )

    delta = compare_position_world_now(
        delta_observation_id="world-delta-001",
        entry=_entry_record(),
        current_snapshot=current,
        compared_at=current.observed_at,
        provenance_refs=(
            "entry-world:001",
            "snapshot:current-002",
        ),
    )

    assert delta.world_state_changed is True
    assert delta.market_regime_changed is True
    assert delta.macro_regime_changed is True
    assert delta.relationship_coherence_changed is True
    assert delta.relationship_stability_changed is True
    assert delta.elapsed_since_entry_ms == 4 * 60 * 60 * 1000
    assert delta.threat_classification_authority is False
    assert delta.position_management_authority is False
    assert delta.execution_authority is False
    assert len(delta.fingerprint()) == 64


def test_world_now_delta_can_report_no_material_state_change() -> None:
    current = _snapshot(
        snapshot_id="snapshot-current-002",
        observed_at=OPENED_AT + timedelta(hours=1),
        evidence_cutoff_at=OPENED_AT + timedelta(hours=1) - timedelta(seconds=1),
    )

    delta = compare_position_world_now(
        delta_observation_id="world-delta-001",
        entry=_entry_record(),
        current_snapshot=current,
        compared_at=current.observed_at,
        provenance_refs=(
            "entry-world:001",
            "snapshot:current-002",
        ),
    )

    assert delta.world_state_changed is False
    assert delta.market_regime_changed is False
    assert delta.macro_regime_changed is False
    assert delta.relationship_coherence_changed is False
    assert delta.relationship_stability_changed is False


def test_world_now_delta_rejects_different_asset() -> None:
    current = replace(
        _snapshot(
            snapshot_id="snapshot-current-002",
            observed_at=OPENED_AT + timedelta(hours=1),
            evidence_cutoff_at=OPENED_AT,
        ),
        asset="EURUSD",
        canonical_instrument_id="canonical:EURUSD",
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="asset differs",
    ):
        compare_position_world_now(
            delta_observation_id="world-delta-001",
            entry=_entry_record(),
            current_snapshot=current,
            compared_at=current.observed_at,
            provenance_refs=("entry-world:001",),
        )


def test_world_now_delta_rejects_pre_entry_snapshot() -> None:
    current = _snapshot(
        snapshot_id="snapshot-current-invalid",
        observed_at=OPENED_AT - timedelta(seconds=1),
        evidence_cutoff_at=OPENED_AT - timedelta(seconds=2),
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot predate the position opening event",
    ):
        compare_position_world_now(
            delta_observation_id="world-delta-001",
            entry=_entry_record(),
            current_snapshot=current,
            compared_at=OPENED_AT,
            provenance_refs=("entry-world:001",),
        )


def test_world_now_delta_rejects_future_current_snapshot() -> None:
    current = _snapshot(
        snapshot_id="snapshot-current-future",
        observed_at=OPENED_AT + timedelta(hours=1),
        evidence_cutoff_at=OPENED_AT,
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="cannot consume a future current snapshot",
    ):
        compare_position_world_now(
            delta_observation_id="world-delta-001",
            entry=_entry_record(),
            current_snapshot=current,
            compared_at=OPENED_AT + timedelta(minutes=30),
            provenance_refs=("entry-world:001",),
        )


def test_world_now_delta_cannot_acquire_threat_or_execution_authority() -> None:
    current = _snapshot(
        snapshot_id="snapshot-current-002",
        observed_at=OPENED_AT + timedelta(hours=1),
        evidence_cutoff_at=OPENED_AT,
    )
    delta = compare_position_world_now(
        delta_observation_id="world-delta-001",
        entry=_entry_record(),
        current_snapshot=current,
        compared_at=current.observed_at,
        provenance_refs=("entry-world:001",),
    )

    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="factual comparison only",
    ):
        replace(delta, threat_classification_authority=True)
