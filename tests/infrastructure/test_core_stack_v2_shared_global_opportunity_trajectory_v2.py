from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityHeadThreshold,
    SharedOpportunityMechanism,
    SharedOpportunityTrajectoryPolicy,
    assess_opportunity_trajectory,
    opportunity_mechanism_scores,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedOpportunityMaturity,
)

T0 = datetime(2026, 9, 30, 4, 0, tzinfo=UTC)


def _observation(minute: int, *, expansion: int = 5_000) -> SharedOpportunitySourceObservation:
    return SharedOpportunitySourceObservation(
        observation_id=f"v2-{minute}",
        asset="NAS100",
        as_of=T0 + timedelta(minutes=minute),
        evidence_cutoff_at=T0 + timedelta(minutes=minute),
        direction_sign=1,
        data_integrity_bps=10_000,
        compression_bps=expansion,
        liquidity_accumulation_bps=expansion,
        failed_auction_bps=2_000,
        displacement_bps=expansion,
        acceptance_bps=4_000,
        absorption_bps=2_000,
        leader_confirmation_bps=4_000,
        leader_divergence_bps=2_000,
        momentum_persistence_bps=4_000,
        momentum_decay_bps=2_000,
        structural_fragility_bps=2_000,
        liquidity_vacuum_bps=expansion,
        regime_transition_bps=2_000,
        anomaly_bps=1_500,
        provenance_refs=("source-only-v2-test",),
    )


def _policy() -> SharedOpportunityTrajectoryPolicy:
    heads = tuple(
        SharedOpportunityHeadThreshold(
            mechanism=mechanism,
            early_level_bps=4_000,
            developing_level_bps=6_000,
            mature_level_bps=7_500,
            positive_velocity_bps=500,
            persistence_bps=5_000,
        )
        for mechanism in SharedOpportunityMechanism
    )
    return SharedOpportunityTrajectoryPolicy(
        policy_id="sti2-v2-test",
        sequence_window=6,
        heads=heads,
        minimum_integrity_bps=9_500,
        source_only_calibration=True,
        evidence_refs=("r8-source-only",),
    )


def test_mechanism_heads_are_separate() -> None:
    scores = opportunity_mechanism_scores(_observation(0, expansion=8_000))
    assert scores[SharedOpportunityMechanism.EXPANSION] == 8_000
    assert scores[SharedOpportunityMechanism.CONTINUATION] < 8_000
    assert set(scores) == set(SharedOpportunityMechanism)


def test_trajectory_detects_emergence_before_aggregate_maturity() -> None:
    sequence = tuple(
        _observation(index, expansion=value)
        for index, value in enumerate((3_000, 3_500, 4_000, 4_500, 5_000, 5_800))
    )
    result = assess_opportunity_trajectory(sequence, policy=_policy())

    assert result.maturity is SharedOpportunityMaturity.EARLY
    assert result.dominant_mechanism is SharedOpportunityMechanism.EXPANSION
    assert result.creates_trader_setup is False
    assert result.execution_authority is False


def test_trajectory_can_mature_mechanism_head() -> None:
    sequence = tuple(
        _observation(index, expansion=value)
        for index, value in enumerate((5_000, 6_000, 7_000, 8_000, 8_200, 8_400))
    )
    result = assess_opportunity_trajectory(sequence, policy=_policy())

    assert result.maturity is SharedOpportunityMaturity.MATURE
    assert result.dominant_mechanism is SharedOpportunityMechanism.EXPANSION


def test_bad_integrity_fails_to_insufficient() -> None:
    last = _observation(5, expansion=8_000)
    bad = SharedOpportunitySourceObservation(
        **{
            name: getattr(last, name)
            for name in last.__dataclass_fields__
            if name != "data_integrity_bps"
        },
        data_integrity_bps=7_000,
    )
    sequence = tuple(_observation(i) for i in range(5)) + (bad,)
    result = assess_opportunity_trajectory(sequence, policy=_policy())

    assert result.maturity is SharedOpportunityMaturity.INSUFFICIENT
    assert result.dominant_mechanism is None
