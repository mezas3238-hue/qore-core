from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.latent_state_reconstruction import (
    LatentMarketState,
    reconstruct_latent_state,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)


def _obs():
    now = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)
    return SharedOpportunitySourceObservation(
        observation_id="mc06-test",
        asset="NAS100",
        as_of=now,
        evidence_cutoff_at=now,
        direction_sign=1,
        data_integrity_bps=9900,
        compression_bps=5000,
        liquidity_accumulation_bps=6000,
        failed_auction_bps=2000,
        displacement_bps=7000,
        acceptance_bps=7000,
        absorption_bps=6500,
        leader_confirmation_bps=7500,
        leader_divergence_bps=2000,
        momentum_persistence_bps=7000,
        momentum_decay_bps=2000,
        structural_fragility_bps=2500,
        liquidity_vacuum_bps=2000,
        regime_transition_bps=2000,
        anomaly_bps=1000,
        provenance_refs=("mc06:test",),
    )


def test_all_latent_states_have_normalized_weights() -> None:
    belief = reconstruct_latent_state(_obs())
    assert {item.state for item in belief.estimates} == set(LatentMarketState)
    assert sum(item.weight_bps for item in belief.estimates) == 10_000


def test_institutional_like_never_claims_actor_identity() -> None:
    belief = reconstruct_latent_state(_obs())
    item = next(
        row
        for row in belief.estimates
        if row.state is LatentMarketState.INSTITUTIONAL_PARTICIPATION_LIKE
    )
    assert item.actor_identity_claimed is False


def test_reconstruction_is_deterministic_and_source_only() -> None:
    first = reconstruct_latent_state(_obs())
    second = reconstruct_latent_state(_obs())
    assert first.fingerprint() == second.fingerprint()
    assert first.future_market_used is False
    assert first.outcome_used is False
