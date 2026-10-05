"""Causal intervention and confounder validation for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CausalInterventionReceipt:
    capability_id: str
    intervention_id: str
    cause_changed: bool
    expected_effect_direction: int
    observed_effect_direction: int
    confounders_held_or_adjusted: bool
    predecision_only: bool
    downstream_effect_observed: bool

    def __post_init__(self) -> None:
        allowed = {-1, 0, 1}
        if self.expected_effect_direction not in allowed:
            raise ValueError("expected effect direction must be -1, 0 or 1")
        if self.observed_effect_direction not in allowed:
            raise ValueError("observed effect direction must be -1, 0 or 1")

    @property
    def passed(self) -> bool:
        return (
            self.cause_changed
            and self.expected_effect_direction == self.observed_effect_direction
            and self.confounders_held_or_adjusted
            and self.predecision_only
            and self.downstream_effect_observed
        )


@dataclass(frozen=True, slots=True)
class ConfounderStressReceipt:
    capability_id: str
    confounder_id: str
    baseline_effect: float
    adjusted_effect: float
    max_allowed_effect_drift: float
    sign_preserved: bool

    @property
    def effect_drift(self) -> float:
        return abs(self.adjusted_effect - self.baseline_effect)

    @property
    def passed(self) -> bool:
        return self.sign_preserved and self.effect_drift <= self.max_allowed_effect_drift
