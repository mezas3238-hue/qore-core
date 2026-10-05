from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.global_market_relational_graph import (
    RelationDirection,
    RelationEpistemicGrade,
)
from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    ComparabilityConfidence,
    RelationalComparabilityState,
)
from qore.infrastructure.core_stack_v2.shared_b5_relational_science import (
    B5RelationalScienceError,
    RelationalSample,
    RelationshipLifecycleState,
    observe_lead_lag,
    observe_structural_divergence,
    populate_relationship_lifecycle,
)

START = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def _sample(
    index: int,
    source: int,
    target: int,
    *,
    comparable: bool = True,
    freshness_ms: int = 100,
) -> RelationalSample:
    return RelationalSample(
        observed_at=START + timedelta(minutes=index),
        source_value_bps=source,
        target_value_bps=target,
        comparability_state=(
            RelationalComparabilityState.COMPARABLE
            if comparable
            else RelationalComparabilityState.STALE_PEER
        ),
        comparability_confidence=(
            ComparabilityConfidence.HIGH
            if comparable
            else ComparabilityConfidence.LOW
        ),
        source_freshness_ms=freshness_ms,
        target_freshness_ms=freshness_ms,
        provenance_refs=(f"sealed:sample:{index:02d}",),
    )


def test_b11_lifecycle_exposes_required_owner_states_and_death_on_staleness() -> None:
    assert {item.value for item in RelationshipLifecycleState} == {
        "BIRTH",
        "ACTIVE",
        "DEGRADED",
        "STALE",
        "DEAD",
    }
    values = (100, 130, 110, 170, 125, 180, 140)
    samples = tuple(_sample(i, value, value * 2 + (i % 2)) for i, value in enumerate(values))
    samples += (
        _sample(7, 150, 300, comparable=False),
        _sample(8, 160, 320, comparable=False),
    )
    receipt = populate_relationship_lifecycle(
        relation_id="B11:TEST",
        samples=samples,
        window_size=4,
        dead_after_stale_windows=2,
    )
    states = tuple(item.state for item in receipt.transitions)
    assert RelationshipLifecycleState.BIRTH in states
    assert RelationshipLifecycleState.ACTIVE in states
    assert RelationshipLifecycleState.STALE in states
    assert receipt.current_state is RelationshipLifecycleState.DEAD
    assert receipt.productive_authority is False
    assert len(receipt.fingerprint()) == 64


def test_b11_stale_when_freshness_breaks_even_if_values_are_correlated() -> None:
    samples = tuple(
        _sample(i, 100 + i * 10, 200 + i * 20, freshness_ms=900_000)
        for i in range(6)
    )
    receipt = populate_relationship_lifecycle(
        relation_id="B11:FRESHNESS",
        samples=samples,
        window_size=4,
        max_freshness_ms=300_000,
    )
    assert receipt.current_state is RelationshipLifecycleState.STALE


def test_b12_detects_temporal_precedence_without_causation() -> None:
    source_changes = (7, -4, 12, 3, -9, 15, 2, -6, 11, 5, -8)
    source = [100]
    for delta in source_changes:
        source.append(source[-1] + delta)
    target = [200, 200]
    for delta in source_changes[:-1]:
        target.append(target[-1] + delta)
    samples = tuple(
        _sample(i, source[i], target[i])
        for i in range(min(len(source), len(target)))
    )
    observation = observe_lead_lag(
        relation_id="B12:SOURCE_LEADS",
        samples=samples,
        max_lag_steps=3,
        step_ms=60_000,
        minimum_abs_r_bps=7_000,
    )
    assert observation.direction is RelationDirection.SOURCE_TO_TARGET
    assert observation.lag_steps == 1
    assert observation.temporal_precedence_observed is True
    assert observation.epistemic_grade is RelationEpistemicGrade.TEMPORAL_DEPENDENCY
    assert observation.causation_claimed is False


def test_b12_rejects_irregular_cadence_and_noncomparability() -> None:
    samples = tuple(_sample(i, i * 10, i * 11) for i in range(8))
    irregular = list(samples)
    irregular[-1] = RelationalSample(
        observed_at=irregular[-1].observed_at + timedelta(seconds=1),
        source_value_bps=irregular[-1].source_value_bps,
        target_value_bps=irregular[-1].target_value_bps,
        comparability_state=irregular[-1].comparability_state,
        comparability_confidence=irregular[-1].comparability_confidence,
        source_freshness_ms=100,
        target_freshness_ms=100,
        provenance_refs=("sealed:irregular",),
    )
    with pytest.raises(B5RelationalScienceError, match="uniform predeclared cadence"):
        observe_lead_lag(
            relation_id="B12:IRREGULAR",
            samples=tuple(irregular),
            max_lag_steps=2,
            step_ms=60_000,
        )

    not_comparable = samples[:-1] + (
        _sample(7, 70, 77, comparable=False),
    )
    with pytest.raises(B5RelationalScienceError, match="fully comparable"):
        observe_lead_lag(
            relation_id="B12:NOT-COMPARABLE",
            samples=not_comparable,
            max_lag_steps=2,
            step_ms=60_000,
        )


def test_b13_structural_divergence_is_descriptive_only() -> None:
    samples = tuple(
        _sample(i, 100 + i * 60, 600 - i * 55)
        for i in range(6)
    )
    observation = observe_structural_divergence(
        relation_id="B13:OPPOSING",
        samples=samples,
        window_size=5,
        minimum_leg_move_bps=100,
    )
    assert observation.divergent is True
    assert observation.divergence_bps > 0
    assert observation.causation_claimed is False
    assert observation.outcome_used is False
    assert observation.future_market_used is False


def test_b13_rejects_noncomparable_window_and_outcome_samples() -> None:
    samples = tuple(_sample(i, i * 20, 200 - i * 20) for i in range(4))
    bad = samples[:-1] + (_sample(3, 60, 140, comparable=False),)
    with pytest.raises(B5RelationalScienceError, match="fully comparable"):
        observe_structural_divergence(
            relation_id="B13:BLOCKED",
            samples=bad,
            window_size=4,
        )

    with pytest.raises(B5RelationalScienceError, match="outcomes or future"):
        RelationalSample(
            observed_at=START,
            source_value_bps=1,
            target_value_bps=2,
            comparability_state=RelationalComparabilityState.COMPARABLE,
            comparability_confidence=ComparabilityConfidence.HIGH,
            source_freshness_ms=1,
            target_freshness_ms=1,
            provenance_refs=("sealed:forbidden",),
            outcome_used=True,
        )


def test_b11_lifecycle_executes_degraded_after_birth() -> None:
    source_values = (100, 101, 103, 102, 105, 103)
    target_values = (200, 197, 194, 192, 189, 186)
    samples = tuple(
        _sample(i, source_values[i], target_values[i])
        for i in range(len(source_values))
    )
    receipt = populate_relationship_lifecycle(
        relation_id="B11:DEGRADED",
        samples=samples,
        window_size=5,
        active_threshold_bps=6_000,
        degraded_threshold_bps=3_000,
    )
    states = tuple(item.state for item in receipt.transitions)
    assert states == (
        RelationshipLifecycleState.BIRTH,
        RelationshipLifecycleState.DEGRADED,
    )
    assert receipt.current_state is RelationshipLifecycleState.DEGRADED



def test_b11_degraded_strength_births_before_it_can_degrade_or_die() -> None:
    source_values = (0, 1, 3, 6, 10)
    target_values = (0, -2, -4, -3, -4)
    samples = tuple(
        _sample(i, source_values[i], target_values[i])
        for i in range(len(source_values))
    )
    samples += (
        _sample(5, 11, -5, comparable=False),
        _sample(6, 12, -6, comparable=False),
    )

    receipt = populate_relationship_lifecycle(
        relation_id="B11:DEGRADED-BIRTH",
        samples=samples,
        window_size=5,
        active_threshold_bps=6_000,
        degraded_threshold_bps=3_000,
        dead_after_stale_windows=2,
    )

    states = tuple(item.state for item in receipt.transitions)
    assert states == (
        RelationshipLifecycleState.BIRTH,
        RelationshipLifecycleState.STALE,
        RelationshipLifecycleState.DEAD,
    )
    assert receipt.transitions[0].reason_codes == (
        "RELATION_FIRST_OBSERVED_DEGRADED_STRENGTH",
    )
    assert receipt.current_state is RelationshipLifecycleState.DEAD
