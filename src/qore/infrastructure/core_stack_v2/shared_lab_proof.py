"""Canonical multi-dimensional proof bundle for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab_gate_policy import CapabilityNature


class ProofDimension(StrEnum):
    ENGINEERING = "ENGINEERING"
    FUNCTIONAL = "FUNCTIONAL"
    CAUSAL = "CAUSAL"
    SCIENTIFIC = "SCIENTIFIC"
    ECONOMIC = "ECONOMIC"
    INTEGRATION = "INTEGRATION"


class DimensionState(StrEnum):
    OPEN = "OPEN"
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True, slots=True)
class DimensionEvidence:
    dimension: ProofDimension
    state: DimensionState
    evidence_refs: tuple[str, ...]
    not_required_justification: str | None = None

    def __post_init__(self) -> None:
        if self.state is DimensionState.NOT_REQUIRED:
            if not self.not_required_justification:
                raise ValueError("NOT_REQUIRED proof dimension needs justification")
            if self.evidence_refs:
                raise ValueError("NOT_REQUIRED dimension must not carry pass evidence")
        elif not self.evidence_refs:
            raise ValueError("required proof dimension needs evidence refs")


_REQUIRED_DIMENSIONS: dict[CapabilityNature, frozenset[ProofDimension]] = {
    CapabilityNature.SENSOR: frozenset(
        {
            ProofDimension.ENGINEERING,
            ProofDimension.FUNCTIONAL,
            ProofDimension.CAUSAL,
            ProofDimension.SCIENTIFIC,
            ProofDimension.INTEGRATION,
        }
    ),
    CapabilityNature.INFRASTRUCTURE: frozenset(
        {
            ProofDimension.ENGINEERING,
            ProofDimension.FUNCTIONAL,
            ProofDimension.CAUSAL,
            ProofDimension.INTEGRATION,
        }
    ),
    CapabilityNature.REPRESENTATION: frozenset(
        {
            ProofDimension.ENGINEERING,
            ProofDimension.FUNCTIONAL,
            ProofDimension.CAUSAL,
            ProofDimension.SCIENTIFIC,
            ProofDimension.INTEGRATION,
        }
    ),
    CapabilityNature.PRIMITIVE_COGNITION: frozenset(
        {
            ProofDimension.ENGINEERING,
            ProofDimension.FUNCTIONAL,
            ProofDimension.CAUSAL,
            ProofDimension.SCIENTIFIC,
            ProofDimension.INTEGRATION,
        }
    ),
    CapabilityNature.TRADER_FACING_INTELLIGENCE: frozenset(ProofDimension),
    CapabilityNature.FULL_ORGANISM: frozenset(ProofDimension),
}


@dataclass(frozen=True, slots=True)
class CapabilityProofBundle:
    capability_id: str
    nature: CapabilityNature
    dimensions: tuple[DimensionEvidence, ...]

    def __post_init__(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("proof bundle capability identity is required")
        kinds = tuple(item.dimension for item in self.dimensions)
        if set(kinds) != set(ProofDimension):
            raise ValueError("proof bundle must explicitly classify every dimension")
        if len(kinds) != len(set(kinds)):
            raise ValueError("proof bundle cannot duplicate dimensions")

    @property
    def required_dimensions(self) -> frozenset[ProofDimension]:
        return _REQUIRED_DIMENSIONS[self.nature]

    @property
    def blocker_dimensions(self) -> tuple[ProofDimension, ...]:
        state_by_dimension = {
            item.dimension: item.state
            for item in self.dimensions
        }
        return tuple(
            dimension
            for dimension in ProofDimension
            if (
                dimension in self.required_dimensions
                and state_by_dimension[dimension] is not DimensionState.PASS
            )
        )

    @property
    def phase_proven(self) -> bool:
        return not self.blocker_dimensions


def build_dimension_evidence(
    *,
    nature: CapabilityNature,
    states: dict[ProofDimension, DimensionState],
    evidence_refs: dict[ProofDimension, tuple[str, ...]],
) -> tuple[DimensionEvidence, ...]:
    required = _REQUIRED_DIMENSIONS[nature]
    result: list[DimensionEvidence] = []
    for dimension in ProofDimension:
        state = states[dimension]
        if dimension not in required:
            if state is not DimensionState.NOT_REQUIRED:
                raise ValueError(
                    f"{dimension.value} must be NOT_REQUIRED for {nature.value}"
                )
            result.append(
                DimensionEvidence(
                    dimension=dimension,
                    state=state,
                    evidence_refs=(),
                    not_required_justification=(
                        f"{dimension.value} is not intrinsic to {nature.value}"
                    ),
                )
            )
            continue
        if state is DimensionState.NOT_REQUIRED:
            raise ValueError(
                f"required dimension {dimension.value} cannot be NOT_REQUIRED"
            )
        result.append(
            DimensionEvidence(
                dimension=dimension,
                state=state,
                evidence_refs=evidence_refs.get(dimension, ()),
            )
        )
    return tuple(result)
