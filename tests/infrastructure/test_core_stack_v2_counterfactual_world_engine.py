from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.counterfactual_world_engine import (
    CounterfactualWorldKind,
    build_counterfactual_world_distribution,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)


def _observation() -> SharedOpportunitySourceObservation:
    now = datetime(2026, 9, 30, 19, 0, tzinfo=UTC)
    return SharedOpportunitySourceObservation(
        observation_id="mc18-test",
        asset="NAS100",
        as_of=now,
        evidence_cutoff_at=now,
        direction_sign=1,
        data_integrity_bps=10_000,
        compression_bps=4_000,
        liquidity_accumulation_bps=5_000,
        failed_auction_bps=2_000,
        displacement_bps=7_000,
        acceptance_bps=7_500,
        absorption_bps=3_000,
        leader_confirmation_bps=8_000,
        leader_divergence_bps=2_000,
        momentum_persistence_bps=7_000,
        momentum_decay_bps=2_000,
        structural_fragility_bps=2_500,
        liquidity_vacuum_bps=2_000,
        regime_transition_bps=2_000,
        anomaly_bps=1_000,
        provenance_refs=("mc18:test",),
    )


def test_counterfactual_distribution_is_bounded_and_complete() -> None:
    result = build_counterfactual_world_distribution(_observation())
    assert sum(item.probability_bps for item in result.paths) == 10_000
    assert {item.kind for item in result.paths} == set(CounterfactualWorldKind)
    assert result.productive_authority is False


def test_unknown_shock_is_never_removed() -> None:
    result = build_counterfactual_world_distribution(_observation())
    unknown = next(
        item for item in result.paths if item.kind is CounterfactualWorldKind.UNKNOWN_SHOCK
    )
    assert unknown.probability_bps > 0


def test_counterfactual_generation_is_deterministic() -> None:
    first = build_counterfactual_world_distribution(_observation())
    second = build_counterfactual_world_distribution(_observation())
    assert first.fingerprint() == second.fingerprint()
