from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.market_physics_constraints import (
    MarketPhysicsState,
    MarketPhysicsViolation,
    assess_market_physics,
    classify_market_physics_state,
    learn_transition_constraints,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)

NOW = datetime(2026, 9, 30, 17, 0, tzinfo=UTC)


def _obs() -> SharedOpportunitySourceObservation:
    return SharedOpportunitySourceObservation(
        observation_id="physics-001",
        asset="NAS100",
        as_of=NOW,
        evidence_cutoff_at=NOW,
        direction_sign=1,
        data_integrity_bps=10_000,
        compression_bps=2_000,
        liquidity_accumulation_bps=3_000,
        failed_auction_bps=2_000,
        displacement_bps=8_000,
        acceptance_bps=7_000,
        absorption_bps=2_500,
        leader_confirmation_bps=8_000,
        leader_divergence_bps=2_000,
        momentum_persistence_bps=8_000,
        momentum_decay_bps=1_000,
        structural_fragility_bps=2_000,
        liquidity_vacuum_bps=2_000,
        regime_transition_bps=2_000,
        anomaly_bps=1_000,
        provenance_refs=("physics:test",),
    )


def test_consistent_source_state_is_admissible_and_authority_free() -> None:
    result = assess_market_physics(_obs())
    assert result.hard_constraints_pass is True
    assert result.explanation_admissible is True
    assert result.execution_authority is False
    assert result.risk_authority is False
    assert result.capital_authority is False


def test_incompatible_acceptance_and_failure_are_rejected() -> None:
    result = assess_market_physics(
        replace(_obs(), acceptance_bps=9_000, failed_auction_bps=9_000)
    )
    assert result.explanation_admissible is False
    assert MarketPhysicsViolation.ACCEPTANCE_AND_FAILED_AUCTION in result.violations


def test_learned_transition_is_evidence_not_hard_impossibility() -> None:
    constraints = learn_transition_constraints(
        (
            MarketPhysicsState.COMPRESSION,
            MarketPhysicsState.EXPANSION,
            MarketPhysicsState.EXPANSION,
        )
    )
    result = assess_market_physics(
        _obs(),
        previous_state=MarketPhysicsState.COMPRESSION,
        learned_constraints=constraints,
    )
    assert result.learned_transition_seen is True
    assert result.learned_transition_source_count == 1
    assert result.explanation_admissible is True


def test_unseen_transition_does_not_masquerade_as_physical_impossibility() -> None:
    constraints = learn_transition_constraints(
        (MarketPhysicsState.COMPRESSION, MarketPhysicsState.ACCEPTANCE)
    )
    result = assess_market_physics(
        _obs(),
        previous_state=MarketPhysicsState.RELATIONSHIP_BREAK,
        learned_constraints=constraints,
    )
    assert result.learned_transition_seen is False
    assert result.explanation_admissible is True


def test_state_classification_is_deterministic() -> None:
    assert classify_market_physics_state(_obs()) is classify_market_physics_state(_obs())
    assert assess_market_physics(_obs()).fingerprint() == assess_market_physics(_obs()).fingerprint()
