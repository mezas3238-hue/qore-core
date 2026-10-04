"""Counterfactual truth validation for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CounterfactualWorldReceipt:
    capability_id: str
    actual_world_fingerprint_before: str
    actual_world_fingerprint_after: str
    counterfactual_world_fingerprint: str
    assumptions_explicit: bool
    interventions_explicit: bool
    causal_interventions_valid: bool
    transition_coherent: bool
    future_outcome_consumed: bool
    actual_world_mutated: bool

    @property
    def actual_world_isolated(self) -> bool:
        return (
            not self.actual_world_mutated
            and self.actual_world_fingerprint_before == self.actual_world_fingerprint_after
        )

    @property
    def no_outcome_leakage(self) -> bool:
        return not self.future_outcome_consumed

    @property
    def passed(self) -> bool:
        return (
            bool(self.capability_id.strip())
            and self.actual_world_isolated
            and self.assumptions_explicit
            and self.interventions_explicit
            and self.causal_interventions_valid
            and self.transition_coherent
            and self.no_outcome_leakage
            and self.counterfactual_world_fingerprint != self.actual_world_fingerprint_before
        )


@dataclass(frozen=True, slots=True)
class CounterfactualLabAssessment:
    capability_id: str
    world_count: int
    failed_world_indexes: tuple[int, ...]
    all_worlds_truth_valid: bool


def assess_counterfactual_worlds(
    capability_id: str,
    worlds: tuple[CounterfactualWorldReceipt, ...],
) -> CounterfactualLabAssessment:
    if not capability_id.strip() or not worlds:
        raise ValueError("counterfactual assessment requires identity and worlds")
    if any(world.capability_id != capability_id for world in worlds):
        raise ValueError("all counterfactual receipts must belong to capability")
    failed = tuple(index for index, world in enumerate(worlds) if not world.passed)
    return CounterfactualLabAssessment(
        capability_id=capability_id,
        world_count=len(worlds),
        failed_world_indexes=failed,
        all_worlds_truth_valid=not failed,
    )
