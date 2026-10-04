"""Mutation, metamorphic and ablation experiment primitives for Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExperimentKind(StrEnum):
    MUTATION = "MUTATION"
    METAMORPHIC = "METAMORPHIC"
    ABLATION = "ABLATION"


@dataclass(frozen=True, slots=True)
class ExperimentObservation:
    experiment_id: str
    capability_id: str
    kind: ExperimentKind
    baseline_fingerprint: str
    treatment_fingerprint: str
    baseline_downstream_fingerprint: str
    treatment_downstream_fingerprint: str
    material_intervention: bool
    expected_downstream_change: bool
    actual_downstream_change: bool
    invariant_expected: bool = False
    invariant_preserved: bool = False

    def __post_init__(self) -> None:
        if not self.experiment_id.strip() or not self.capability_id.strip():
            raise ValueError("experiment and capability identities are required")
        if self.kind is ExperimentKind.METAMORPHIC and self.expected_downstream_change:
            raise ValueError("metamorphic invariant test cannot require downstream change")

    @property
    def passed(self) -> bool:
        if self.kind is ExperimentKind.MUTATION:
            return (
                self.material_intervention
                and self.baseline_fingerprint != self.treatment_fingerprint
                and self.expected_downstream_change
                and self.actual_downstream_change
                and self.baseline_downstream_fingerprint != self.treatment_downstream_fingerprint
            )
        if self.kind is ExperimentKind.METAMORPHIC:
            return (
                self.material_intervention
                and self.invariant_expected
                and self.invariant_preserved
                and self.baseline_downstream_fingerprint == self.treatment_downstream_fingerprint
            )
        return (
            self.material_intervention
            and self.baseline_fingerprint != self.treatment_fingerprint
            and self.expected_downstream_change
            and self.actual_downstream_change
        )


@dataclass(frozen=True, slots=True)
class CapabilityExperimentAssessment:
    capability_id: str
    mutation_pass: bool
    metamorphic_pass: bool
    ablation_pass: bool
    all_required_experiments_pass: bool


def assess_capability_experiments(
    capability_id: str,
    observations: tuple[ExperimentObservation, ...],
) -> CapabilityExperimentAssessment:
    if not observations:
        raise ValueError("capability experiment assessment requires observations")
    if any(item.capability_id != capability_id for item in observations):
        raise ValueError("all experiment observations must belong to capability")

    by_kind = {
        kind: tuple(item for item in observations if item.kind is kind)
        for kind in ExperimentKind
    }
    results = {
        kind: bool(items) and all(item.passed for item in items)
        for kind, items in by_kind.items()
    }
    all_pass = all(results.values())
    return CapabilityExperimentAssessment(
        capability_id=capability_id,
        mutation_pass=results[ExperimentKind.MUTATION],
        metamorphic_pass=results[ExperimentKind.METAMORPHIC],
        ablation_pass=results[ExperimentKind.ABLATION],
        all_required_experiments_pass=all_pass,
    )
