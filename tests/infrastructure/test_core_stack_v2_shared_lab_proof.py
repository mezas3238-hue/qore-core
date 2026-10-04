import pytest

from qore.infrastructure.core_stack_v2.shared_lab_gate_policy import CapabilityNature
from qore.infrastructure.core_stack_v2.shared_lab_proof import (
    CapabilityProofBundle,
    DimensionState,
    ProofDimension,
    build_dimension_evidence,
)


def test_sensor_economic_dimension_is_explicit_na_not_fake_pass():
    states = {
        dimension: (
            DimensionState.NOT_REQUIRED
            if dimension is ProofDimension.ECONOMIC
            else DimensionState.PASS
        )
        for dimension in ProofDimension
    }
    refs = {
        dimension: (f"evidence:{dimension.value}",)
        for dimension in ProofDimension
        if dimension is not ProofDimension.ECONOMIC
    }
    dimensions = build_dimension_evidence(
        nature=CapabilityNature.SENSOR,
        states=states,
        evidence_refs=refs,
    )
    bundle = CapabilityProofBundle("SENSOR_001", CapabilityNature.SENSOR, dimensions)
    assert bundle.phase_proven is True


def test_trader_facing_capability_cannot_skip_economic_proof():
    states = {dimension: DimensionState.PASS for dimension in ProofDimension}
    states[ProofDimension.ECONOMIC] = DimensionState.OPEN
    refs = {
        dimension: (f"evidence:{dimension.value}",)
        for dimension in ProofDimension
    }
    dimensions = build_dimension_evidence(
        nature=CapabilityNature.TRADER_FACING_INTELLIGENCE,
        states=states,
        evidence_refs=refs,
    )
    bundle = CapabilityProofBundle(
        "STI_001",
        CapabilityNature.TRADER_FACING_INTELLIGENCE,
        dimensions,
    )
    assert bundle.blocker_dimensions == (ProofDimension.ECONOMIC,)
    assert bundle.phase_proven is False


def test_required_dimension_cannot_be_declared_not_required():
    states = {dimension: DimensionState.PASS for dimension in ProofDimension}
    states[ProofDimension.CAUSAL] = DimensionState.NOT_REQUIRED
    refs = {
        dimension: (f"evidence:{dimension.value}",)
        for dimension in ProofDimension
    }
    with pytest.raises(ValueError, match="required dimension"):
        build_dimension_evidence(
            nature=CapabilityNature.PRIMITIVE_COGNITION,
            states=states,
            evidence_refs=refs,
        )
