"""Capability-nature-specific gate policy for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab import SharedLabLevel


class CapabilityNature(StrEnum):
    SENSOR = "SENSOR"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    REPRESENTATION = "REPRESENTATION"
    PRIMITIVE_COGNITION = "PRIMITIVE_COGNITION"
    TRADER_FACING_INTELLIGENCE = "TRADER_FACING_INTELLIGENCE"
    FULL_ORGANISM = "FULL_ORGANISM"


@dataclass(frozen=True, slots=True)
class GateDecision:
    level: SharedLabLevel
    required: bool
    justification: str

    def __post_init__(self) -> None:
        if not self.justification.strip():
            raise ValueError("gate decision requires justification")


@dataclass(frozen=True, slots=True)
class CapabilityGatePolicy:
    nature: CapabilityNature
    gates: tuple[GateDecision, ...]

    def __post_init__(self) -> None:
        levels = tuple(item.level for item in self.gates)
        if set(levels) != set(SharedLabLevel):
            raise ValueError("gate policy must explicitly classify every L0-L10 level")
        if len(levels) != len(set(levels)):
            raise ValueError("gate policy cannot duplicate levels")

    @property
    def required_levels(self) -> tuple[SharedLabLevel, ...]:
        return tuple(item.level for item in self.gates if item.required)

    def decision_for(self, level: SharedLabLevel) -> GateDecision:
        return next(item for item in self.gates if item.level is level)


_REQUIRED_BY_NATURE: dict[CapabilityNature, frozenset[SharedLabLevel]] = {
    CapabilityNature.SENSOR: frozenset(
        {
            SharedLabLevel.L0_STRUCTURAL_REALITY,
            SharedLabLevel.L1_SENSOR_REALITY,
            SharedLabLevel.L2_REPRESENTATION_REALITY,
            SharedLabLevel.L7_ADVERSARIAL_LAB,
            SharedLabLevel.L9_FULL_ORGANISM_END_TO_END,
            SharedLabLevel.L10_LABORATORY_INTEGRITY,
        }
    ),
    CapabilityNature.INFRASTRUCTURE: frozenset(
        {
            SharedLabLevel.L0_STRUCTURAL_REALITY,
            SharedLabLevel.L1_SENSOR_REALITY,
            SharedLabLevel.L7_ADVERSARIAL_LAB,
            SharedLabLevel.L9_FULL_ORGANISM_END_TO_END,
            SharedLabLevel.L10_LABORATORY_INTEGRITY,
        }
    ),
    CapabilityNature.REPRESENTATION: frozenset(
        {
            SharedLabLevel.L0_STRUCTURAL_REALITY,
            SharedLabLevel.L2_REPRESENTATION_REALITY,
            SharedLabLevel.L5_CAUSAL_CONTRIBUTION,
            SharedLabLevel.L6_SCIENTIFIC_REALITY,
            SharedLabLevel.L7_ADVERSARIAL_LAB,
            SharedLabLevel.L9_FULL_ORGANISM_END_TO_END,
            SharedLabLevel.L10_LABORATORY_INTEGRITY,
        }
    ),
    CapabilityNature.PRIMITIVE_COGNITION: frozenset(
        {
            SharedLabLevel.L0_STRUCTURAL_REALITY,
            SharedLabLevel.L3_COGNITIVE_REALITY,
            SharedLabLevel.L4_COGNITIVE_INTERACTION,
            SharedLabLevel.L5_CAUSAL_CONTRIBUTION,
            SharedLabLevel.L6_SCIENTIFIC_REALITY,
            SharedLabLevel.L7_ADVERSARIAL_LAB,
            SharedLabLevel.L9_FULL_ORGANISM_END_TO_END,
            SharedLabLevel.L10_LABORATORY_INTEGRITY,
        }
    ),
    CapabilityNature.TRADER_FACING_INTELLIGENCE: frozenset(
        {
            SharedLabLevel.L0_STRUCTURAL_REALITY,
            SharedLabLevel.L3_COGNITIVE_REALITY,
            SharedLabLevel.L4_COGNITIVE_INTERACTION,
            SharedLabLevel.L5_CAUSAL_CONTRIBUTION,
            SharedLabLevel.L6_SCIENTIFIC_REALITY,
            SharedLabLevel.L7_ADVERSARIAL_LAB,
            SharedLabLevel.L8_SEVEN_TRADER_REALITY,
            SharedLabLevel.L9_FULL_ORGANISM_END_TO_END,
            SharedLabLevel.L10_LABORATORY_INTEGRITY,
        }
    ),
    CapabilityNature.FULL_ORGANISM: frozenset(SharedLabLevel),
}


def default_gate_policy(nature: CapabilityNature) -> CapabilityGatePolicy:
    required = _REQUIRED_BY_NATURE[nature]
    gates = tuple(
        GateDecision(
            level=level,
            required=level in required,
            justification=(
                f"{nature.value} requires {level.value}"
                if level in required
                else f"{level.value} is not intrinsically required for {nature.value}; "
                "N/A is explicit and must not be treated as PASS"
            ),
        )
        for level in SharedLabLevel
    )
    return CapabilityGatePolicy(nature=nature, gates=gates)
