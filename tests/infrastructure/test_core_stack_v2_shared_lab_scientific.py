from qore.infrastructure.core_stack_v2.shared_lab_scientific import (
    ScientificGateKind,
    ScientificGateReceipt,
    assess_scientific_reality,
)


def gate(kind: ScientificGateKind, passed: bool = True, tuned: bool = False):
    return ScientificGateReceipt(
        gate_id=f"{kind.value}-1",
        kind=kind,
        passed=passed,
        evidence_ref=f"evidence:{kind.value}",
        preregistered=True,
        outcome_aware_tuning_used=tuned,
    )


def test_one_failed_era_cannot_be_pooled_away():
    gates = (
        gate(ScientificGateKind.WALK_FORWARD),
        gate(ScientificGateKind.OOS),
        gate(ScientificGateKind.ERA, passed=False),
        gate(ScientificGateKind.TEMPORAL_REPLICATION),
        gate(ScientificGateKind.STRESS),
        gate(ScientificGateKind.MONTE_CARLO),
    )
    result = assess_scientific_reality(
        gates,
        required_kinds=frozenset(ScientificGateKind),
    )
    assert result.failed_gate_ids == ("ERA-1",)
    assert result.scientifically_proven is False


def test_outcome_aware_tuning_invalidates_science():
    gates = tuple(gate(kind, tuned=kind is ScientificGateKind.OOS) for kind in ScientificGateKind)
    result = assess_scientific_reality(gates, required_kinds=frozenset(ScientificGateKind))
    assert result.no_outcome_aware_tuning is False
    assert result.scientifically_proven is False


def test_all_required_scientific_gates_pass_individually():
    gates = tuple(gate(kind) for kind in ScientificGateKind)
    result = assess_scientific_reality(gates, required_kinds=frozenset(ScientificGateKind))
    assert result.scientifically_proven is True
