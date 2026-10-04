from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.global_market_relational_graph import (
    RelationDirection,
    RelationEpistemicGrade,
)
from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    ComparabilityConfidence,
    RelationalComparabilityState,
)
from qore.infrastructure.core_stack_v2.shared_b5_asset_world import (
    AgriculturalWorldReceipt,
    AssetWorldState,
    B5AssetWorldError,
    assess_agricultural_world,
    assess_commodity_world,
    dated_gc_contracts_from_evidence,
    energy_reference_objects_from_evidence,
)
from qore.infrastructure.core_stack_v2.shared_b5_relational_science import (
    B5RelationalScienceError,
    RelationalSample,
    RelationshipLifecycleState,
    observe_lead_lag,
    observe_structural_divergence,
    populate_relationship_lifecycle,
)

NOW = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]


def _sample(
    minute: int,
    source: int,
    target: int,
    *,
    state: RelationalComparabilityState = RelationalComparabilityState.COMPARABLE,
    confidence: ComparabilityConfidence = ComparabilityConfidence.HIGH,
    outcome_used: bool = False,
    future_market_used: bool = False,
) -> RelationalSample:
    return RelationalSample(
        observed_at=NOW + timedelta(minutes=minute),
        source_value_bps=source,
        target_value_bps=target,
        comparability_state=state,
        comparability_confidence=confidence,
        source_freshness_ms=100,
        target_freshness_ms=120,
        provenance_refs=(f"sample:{minute:02d}",),
        outcome_used=outcome_used,
        future_market_used=future_market_used,
    )


def test_b11_relationship_lifecycle_populates_birth_active_stale_dead() -> None:
    samples = (
        _sample(0, 0, 0),
        _sample(1, 100, 100),
        _sample(2, -50, -50),
        _sample(3, 200, 200),
        _sample(4, -100, -100),
        _sample(5, 250, 250),
        _sample(
            6,
            300,
            300,
            state=RelationalComparabilityState.STALE_PEER,
            confidence=ComparabilityConfidence.LOW,
        ),
        _sample(
            7,
            350,
            350,
            state=RelationalComparabilityState.STALE_PEER,
            confidence=ComparabilityConfidence.LOW,
        ),
    )

    receipt = populate_relationship_lifecycle(
        relation_id="US2000->USTEC:M1",
        samples=samples,
        window_size=5,
        dead_after_stale_windows=2,
    )

    states = tuple(item.state for item in receipt.transitions)
    assert RelationshipLifecycleState.BIRTH in states
    assert RelationshipLifecycleState.ACTIVE in states
    assert RelationshipLifecycleState.STALE in states
    assert RelationshipLifecycleState.DEAD in states
    assert receipt.current_state is RelationshipLifecycleState.DEAD
    assert len(receipt.fingerprint()) == 64
    assert receipt.outcome_used is False
    assert receipt.future_market_used is False
    assert receipt.productive_authority is False


def test_b11_lifecycle_is_deterministic() -> None:
    samples = tuple(_sample(i, i * 100, i * 100) for i in range(8))
    left = populate_relationship_lifecycle(
        relation_id="A:B:M5",
        samples=samples,
        window_size=4,
    )
    right = populate_relationship_lifecycle(
        relation_id="A:B:M5",
        samples=samples,
        window_size=4,
    )
    assert left == right
    assert left.fingerprint() == right.fingerprint()


def test_b12_lead_lag_detects_temporal_precedence_without_causal_claim() -> None:
    source = (0, 500, -300, 800, -700, 200, 900, -450, 150, 650, -200, 400)
    target = (100, -100) + source[:-2]
    samples = tuple(
        _sample(index, source[index], target[index])
        for index in range(len(source))
    )

    observation = observe_lead_lag(
        relation_id="LEAD_TEST",
        samples=samples,
        max_lag_steps=4,
        step_ms=60_000,
        minimum_abs_r_bps=8_000,
    )

    assert observation.direction is RelationDirection.SOURCE_TO_TARGET
    assert observation.lag_steps == 2
    assert observation.lag_ms == 120_000
    assert observation.pearson_r_bps == 10_000
    assert observation.epistemic_grade is RelationEpistemicGrade.TEMPORAL_DEPENDENCY
    assert observation.temporal_precedence_observed is True
    assert observation.causation_claimed is False
    assert observation.outcome_used is False
    assert observation.future_market_used is False


def test_b12_zero_lag_association_does_not_become_causation() -> None:
    values = (0, 500, -300, 800, -700, 200, 900, -450)
    samples = tuple(_sample(index, value, value) for index, value in enumerate(values))

    observation = observe_lead_lag(
        relation_id="SIMULTANEOUS",
        samples=samples,
        max_lag_steps=2,
        minimum_abs_r_bps=8_000,
    )

    assert observation.direction is RelationDirection.UNRESOLVED
    assert observation.lag_steps == 0
    assert observation.epistemic_grade is RelationEpistemicGrade.ASSOCIATION
    assert observation.temporal_precedence_observed is False
    assert observation.causation_claimed is False


def test_b12_rejects_noncomparable_population() -> None:
    samples = tuple(
        _sample(
            index,
            index * 100,
            index * 90,
            state=(
                RelationalComparabilityState.STALE_PEER
                if index == 4
                else RelationalComparabilityState.COMPARABLE
            ),
            confidence=(
                ComparabilityConfidence.LOW
                if index == 4
                else ComparabilityConfidence.HIGH
            ),
        )
        for index in range(8)
    )
    with pytest.raises(B5RelationalScienceError, match="fully comparable"):
        observe_lead_lag(relation_id="FAIL", samples=samples, max_lag_steps=2)


def test_b13_structural_divergence_uses_only_comparable_causal_window() -> None:
    samples = (
        _sample(0, 0, 0),
        _sample(1, 100, -100),
        _sample(2, 200, -200),
        _sample(3, 300, -300),
        _sample(4, 450, -500),
    )
    observation = observe_structural_divergence(
        relation_id="STRUCTURAL_DIVERGENCE",
        samples=samples,
        window_size=5,
        minimum_leg_move_bps=200,
    )

    assert observation.divergent is True
    assert observation.source_delta_bps == 450
    assert observation.target_delta_bps == -500
    assert observation.divergence_bps == 450
    assert observation.comparable_sample_count == 5
    assert observation.outcome_used is False
    assert observation.future_market_used is False


def test_b13_rejects_stale_relation_window() -> None:
    samples = (
        _sample(0, 0, 0),
        _sample(1, 100, -100),
        _sample(
            2,
            200,
            -200,
            state=RelationalComparabilityState.STALE_PEER,
            confidence=ComparabilityConfidence.LOW,
        ),
        _sample(3, 300, -300),
    )
    with pytest.raises(B5RelationalScienceError, match="fully comparable"):
        observe_structural_divergence(
            relation_id="STALE",
            samples=samples,
            window_size=4,
        )


def test_relational_samples_reject_outcome_or_future_data() -> None:
    with pytest.raises(B5RelationalScienceError, match="outcomes or future"):
        _sample(0, 1, 1, outcome_used=True)
    with pytest.raises(B5RelationalScienceError, match="outcomes or future"):
        _sample(0, 1, 1, future_market_used=True)


def test_b14_current_agriculture_is_known_blindspot_not_proxy() -> None:
    receipt = assess_agricultural_world(
        as_of=NOW,
        conceptual_market_count=16,
        provider_candidate_count=0,
        provider_count=1,
        secondary_provider_scientifically_admitted=False,
    )

    assert receipt.state is AssetWorldState.KNOWN_BLINDSPOT
    assert receipt.provider_candidate_count == 0
    assert receipt.synthetic_proxy_used is False
    assert receipt.relational_claims_authorized is False
    assert receipt.productive_authority is False
    assert len(receipt.fingerprint()) == 64


def test_b14_cannot_claim_nonblindspot_with_zero_provider_candidates() -> None:
    with pytest.raises(B5AssetWorldError, match="KNOWN_BLINDSPOT"):
        AgriculturalWorldReceipt(
            as_of=NOW,
            conceptual_market_count=16,
            provider_candidate_count=0,
            provider_count=1,
            state=AssetWorldState.UNRESOLVED,
            reason_codes=("NO_PROVIDER",),
            secondary_provider_scientifically_admitted=False,
        )


def test_b15_current_energy_and_gc_evidence_remains_unresolved() -> None:
    energy_path = (
        ROOT
        / "docs"
        / "shared"
        / "evidence"
        / "QORE_SHARED_GW2_ENERGY_REFERENCE_AUTHORITY_EVIDENCE_001.json"
    )
    gc_path = (
        ROOT
        / "docs"
        / "shared"
        / "evidence"
        / "QORE_SHARED_GW2_GC_FUTURES_CONTRACT_AUTHORITY_EVIDENCE_001.json"
    )
    energy = energy_reference_objects_from_evidence(
        json.loads(energy_path.read_text(encoding="utf-8"))
    )
    contracts = dated_gc_contracts_from_evidence(
        json.loads(gc_path.read_text(encoding="utf-8"))
    )

    receipt = assess_commodity_world(
        as_of=NOW,
        metal_reference_object_count=11,
        energy_reference_objects=energy,
        dated_contracts=contracts,
    )

    assert len(energy) == 3
    assert all(item.state is AssetWorldState.REFERENCE_OBJECT for item in energy)
    assert len(contracts) == 5
    assert receipt.metal_reference_object_count == 11
    assert receipt.energy_reference_object_count == 3
    assert receipt.dated_contract_count == 5
    assert receipt.expired_dated_contract_count == 5
    assert receipt.front_contract_verified_count == 0
    assert receipt.roll_semantics_verified_count == 0
    assert receipt.continuous_semantics_verified_count == 0
    assert receipt.state is AssetWorldState.UNRESOLVED
    assert "FRONT_CONTRACT_SELECTION_UNRESOLVED" in receipt.blockers
    assert "ROLL_SEMANTICS_UNRESOLVED" in receipt.blockers
    assert "CONTINUOUS_SERIES_CONSTRUCTION_UNRESOLVED" in receipt.blockers
    assert receipt.relational_claims_authorized is False
    assert receipt.productive_authority is False
    assert len(receipt.fingerprint()) == 64


def test_b15_reference_objects_never_imply_front_roll_or_continuous() -> None:
    energy_path = (
        ROOT
        / "docs"
        / "shared"
        / "evidence"
        / "QORE_SHARED_GW2_ENERGY_REFERENCE_AUTHORITY_EVIDENCE_001.json"
    )
    energy = energy_reference_objects_from_evidence(
        json.loads(energy_path.read_text(encoding="utf-8"))
    )
    assert all(item.state is AssetWorldState.REFERENCE_OBJECT for item in energy)
    assert all(item.tradable_product_identity_status == "UNRESOLVED" for item in energy)
    assert all(item.venue_status == "UNRESOLVED" for item in energy)
