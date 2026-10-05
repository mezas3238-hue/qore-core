"""Scientific gate aggregation for QORE Shared Lab.

Encodes no pooled rescue across walk-forward, OOS, eras, stress and Monte Carlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ScientificGateKind(StrEnum):
    WALK_FORWARD = "WALK_FORWARD"
    OOS = "OOS"
    ERA = "ERA"
    TEMPORAL_REPLICATION = "TEMPORAL_REPLICATION"
    STRESS = "STRESS"
    MONTE_CARLO = "MONTE_CARLO"


@dataclass(frozen=True, slots=True)
class ScientificGateReceipt:
    gate_id: str
    kind: ScientificGateKind
    passed: bool
    evidence_ref: str
    preregistered: bool
    outcome_aware_tuning_used: bool = False

    def __post_init__(self) -> None:
        if not self.gate_id.strip() or not self.evidence_ref.strip():
            raise ValueError("scientific gate requires identity and evidence")


@dataclass(frozen=True, slots=True)
class ScientificRealityAssessment:
    gate_count: int
    failed_gate_ids: tuple[str, ...]
    missing_kinds: tuple[ScientificGateKind, ...]
    preregistration_pass: bool
    no_outcome_aware_tuning: bool
    scientifically_proven: bool


def assess_scientific_reality(
    gates: tuple[ScientificGateReceipt, ...],
    *,
    required_kinds: frozenset[ScientificGateKind],
) -> ScientificRealityAssessment:
    if not gates:
        raise ValueError("scientific reality requires gates")
    ids = tuple(gate.gate_id for gate in gates)
    if len(ids) != len(set(ids)):
        raise ValueError("scientific gate ids must be unique")
    present = {gate.kind for gate in gates}
    missing = tuple(sorted(required_kinds - present, key=lambda item: item.value))
    failed = tuple(sorted(gate.gate_id for gate in gates if not gate.passed))
    prereg = all(gate.preregistered for gate in gates)
    no_tuning = not any(gate.outcome_aware_tuning_used for gate in gates)
    proven = not missing and not failed and prereg and no_tuning
    return ScientificRealityAssessment(
        gate_count=len(gates),
        failed_gate_ids=failed,
        missing_kinds=missing,
        preregistration_pass=prereg,
        no_outcome_aware_tuning=no_tuning,
        scientifically_proven=proven,
    )
