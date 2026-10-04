from qore.infrastructure.core_stack_v2.shared_lab_data_assessment import (
    REQUIRED_DATA_REALITY_GATES,
    DataRealityGate,
    GateEvidence,
    assess_data_reality,
)


def _evidence(gate: DataRealityGate, passed: bool = True) -> GateEvidence:
    return GateEvidence(gate, passed, f"run::{gate.value}", "a" * 64)


def test_all_required_gates_are_individually_required() -> None:
    evidence = tuple(_evidence(g) for g in REQUIRED_DATA_REALITY_GATES)
    assessment = assess_data_reality(evidence)
    assert assessment.functional_complete
    assert assessment.failed_gates == ()
    assert assessment.missing_gates == ()
    assert not assessment.productive_authority
    assert not assessment.certification_authority


def test_one_failed_gate_cannot_be_rescued_by_thirteen_passes() -> None:
    evidence = tuple(
        _evidence(g, passed=g is not DataRealityGate.PROVENANCE)
        for g in REQUIRED_DATA_REALITY_GATES
    )
    assessment = assess_data_reality(evidence)
    assert not assessment.functional_complete
    assert assessment.failed_gates == (DataRealityGate.PROVENANCE,)


def test_missing_gate_is_not_implicitly_green() -> None:
    evidence = tuple(
        _evidence(g)
        for g in REQUIRED_DATA_REALITY_GATES
        if g is not DataRealityGate.L10_KNOWN_FAILURE_DETECTION
    )
    assessment = assess_data_reality(evidence)
    assert not assessment.functional_complete
    assert assessment.missing_gates == (DataRealityGate.L10_KNOWN_FAILURE_DETECTION,)
