from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.market_agency_model import (
    SharedAgencyMechanism,
    assess_market_agency,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedTraderIntelligenceValidationError,
)

NOW = datetime(2026, 9, 30, 16, 30, tzinfo=UTC)


def _obs() -> SharedOpportunitySourceObservation:
    return SharedOpportunitySourceObservation(
        observation_id="agency-001",
        asset="NAS100",
        as_of=NOW,
        evidence_cutoff_at=NOW,
        direction_sign=-1,
        data_integrity_bps=10_000,
        compression_bps=2_000,
        liquidity_accumulation_bps=3_000,
        failed_auction_bps=6_000,
        displacement_bps=8_000,
        acceptance_bps=3_000,
        absorption_bps=4_000,
        leader_confirmation_bps=2_500,
        leader_divergence_bps=8_000,
        momentum_persistence_bps=2_000,
        momentum_decay_bps=8_000,
        structural_fragility_bps=9_000,
        liquidity_vacuum_bps=9_000,
        regime_transition_bps=8_500,
        anomaly_bps=7_500,
        provenance_refs=("real-source:agency-test",),
    )


def test_market_agency_emits_mechanism_hypotheses_not_actor_identity() -> None:
    result = assess_market_agency(_obs())
    assert tuple(row.mechanism for row in result.hypotheses) == tuple(
        SharedAgencyMechanism
    )
    assert result.dominant_mechanism is not None
    assert all(row.actor_identity_claimed is False for row in result.hypotheses)
    assert all(
        row.calibrated_probability_claimed is False for row in result.hypotheses
    )
    assert result.execution_authority is False
    assert result.risk_authority is False
    assert result.capital_authority is False


def test_agency_assessment_is_deterministic() -> None:
    first = assess_market_agency(_obs())
    second = assess_market_agency(_obs())
    assert first.fingerprint() == second.fingerprint()


def test_bad_integrity_fails_to_insufficient_without_dominant_mechanism() -> None:
    result = assess_market_agency(replace(_obs(), data_integrity_bps=9_000))
    assert result.insufficient is True
    assert result.dominant_mechanism is None


def test_invalid_integrity_gate_is_rejected() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="minimum_integrity_bps",
    ):
        assess_market_agency(_obs(), minimum_integrity_bps=10_001)
