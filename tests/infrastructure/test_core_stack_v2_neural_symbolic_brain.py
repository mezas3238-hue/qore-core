from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.market_physics_constraints import (
    assess_market_physics,
)
from qore.infrastructure.core_stack_v2.neural_symbolic_brain import (
    CalibratedBeliefRef,
    FrozenLearnedRepresentationRef,
    NeuralSymbolicDisposition,
    arbitrate_neural_symbolic,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)

NOW = datetime(2026, 9, 30, 18, 30, tzinfo=UTC)


def _obs(**overrides) -> SharedOpportunitySourceObservation:
    values = {
        "observation_id": "mc11-obs",
        "asset": "NAS100",
        "as_of": NOW,
        "evidence_cutoff_at": NOW,
        "direction_sign": 1,
        "data_integrity_bps": 10_000,
        "compression_bps": 2_000,
        "liquidity_accumulation_bps": 3_000,
        "failed_auction_bps": 2_000,
        "displacement_bps": 8_000,
        "acceptance_bps": 7_000,
        "absorption_bps": 2_500,
        "leader_confirmation_bps": 8_000,
        "leader_divergence_bps": 2_000,
        "momentum_persistence_bps": 8_000,
        "momentum_decay_bps": 1_000,
        "structural_fragility_bps": 2_000,
        "liquidity_vacuum_bps": 2_000,
        "regime_transition_bps": 2_000,
        "anomaly_bps": 1_000,
        "provenance_refs": ("mc11:test-source",),
    }
    values.update(overrides)
    return SharedOpportunitySourceObservation(**values)


def _representation() -> FrozenLearnedRepresentationRef:
    return FrozenLearnedRepresentationRef(
        representation_fingerprint="a" * 64,
        concept_ids=("LATENT_CONCEPT_001",),
        probe_fingerprints=("b" * 64,),
        evidence_refs=("wp04:v3b",),
    )


def _calibration() -> CalibratedBeliefRef:
    return CalibratedBeliefRef(
        calibration_artifact_fingerprint="c" * 64,
        calibration_ece_bps=535,
        temporal_oos_pass=True,
        evidence_refs=("mc09:v2",),
    )


def _run(physics, support=8_000, contradiction=2_000, uncertainty=1_000):
    return arbitrate_neural_symbolic(
        representation=_representation(),
        belief_calibration=_calibration(),
        physics=physics,
        learned_support_bps=support,
        learned_contradiction_bps=contradiction,
        epistemic_uncertainty_bps=uncertainty,
        source_observation_refs=("source:mc11",),
        contradicting_evidence_refs=("contradiction:mc11",),
        causal_path_refs=("causal:path:mc11",),
    )


def test_supported_learned_evidence_remains_traceable() -> None:
    result = _run(assess_market_physics(_obs()))
    assert result.disposition is NeuralSymbolicDisposition.SUPPORTED
    assert result.assertiveness_bps == 6_000
    assert result.hard_constraint_veto is False
    assert len(result.fingerprint()) == 64


def test_hard_constraint_veto_dominates_large_learned_support() -> None:
    physics = assess_market_physics(
        _obs(acceptance_bps=9_000, failed_auction_bps=9_000)
    )
    result = _run(physics, support=10_000, contradiction=0, uncertainty=0)
    assert result.disposition is NeuralSymbolicDisposition.HARD_CONSTRAINT_VETO
    assert result.assertiveness_bps == 0
    assert result.hard_constraint_veto is True


def test_contradiction_remains_explicit() -> None:
    result = _run(
        assess_market_physics(_obs()),
        support=3_000,
        contradiction=7_000,
        uncertainty=2_000,
    )
    assert result.disposition is NeuralSymbolicDisposition.CONTESTED
    assert "CONTRADICTION_AT_LEAST_SUPPORT" in result.reason_codes


def test_zero_evidence_abstains() -> None:
    result = _run(
        assess_market_physics(_obs()),
        support=0,
        contradiction=0,
        uncertainty=9_000,
    )
    assert result.disposition is NeuralSymbolicDisposition.ABSTAIN
    assert result.assertiveness_bps == 0


def test_no_sovereign_authority_is_created() -> None:
    result = _run(assess_market_physics(_obs()))
    assert result.execution_authority is False
    assert result.risk_authority is False
    assert result.sizing_authority is False
    assert result.capital_authority is False
    assert result.methodology_authority is False
