"""Fail-degraded dependency notification and abstention receipts."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import (
    DegradationClass,
    classify_resilience,
)


@dataclass(frozen=True, slots=True)
class ResilienceReceipt:
    required_sensor_count: int
    available_required_sensor_count: int
    alternative_sensor_count: int
    observability_ratio: float
    classification: DegradationClass
    base_uncertainty: float
    resulting_uncertainty: float
    affected_dependencies: tuple[str, ...]
    data_plane_continues: bool
    abstention_required: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.productive_authority:
            raise ValueError("resilience lab grants no productive authority")

    @property
    def passed(self) -> bool:
        if self.classification is DegradationClass.ABSTENTION_REQUIRED:
            return self.abstention_required and not self.data_plane_continues
        if self.classification is DegradationClass.CRITICAL_SENSOR_FAILURE:
            return bool(self.affected_dependencies) and not self.data_plane_continues
        return self.data_plane_continues and self.resulting_uncertainty >= self.base_uncertainty


def assess_resilience(
    *,
    required_sensor_count: int,
    available_required_sensor_count: int,
    alternative_sensor_count: int,
    observability_ratio: float,
    base_uncertainty: float,
    affected_dependencies: tuple[str, ...],
) -> ResilienceReceipt:
    if not 0 <= base_uncertainty <= 1:
        raise ValueError("base_uncertainty must be in [0,1]")
    classification = classify_resilience(
        required_sensor_count,
        available_required_sensor_count,
        alternative_sensor_count,
        observability_ratio,
    )
    missing_fraction = (
        required_sensor_count - available_required_sensor_count
    ) / required_sensor_count
    uplift = min(1.0, base_uncertainty + 0.5 * missing_fraction)
    continues = classification in {
        DegradationClass.SAFE_DEGRADATION,
        DegradationClass.DEGRADED_BUT_USABLE,
    }
    abstain = classification is DegradationClass.ABSTENTION_REQUIRED
    return ResilienceReceipt(
        required_sensor_count=required_sensor_count,
        available_required_sensor_count=available_required_sensor_count,
        alternative_sensor_count=alternative_sensor_count,
        observability_ratio=observability_ratio,
        classification=classification,
        base_uncertainty=base_uncertainty,
        resulting_uncertainty=uplift,
        affected_dependencies=affected_dependencies,
        data_plane_continues=continues,
        abstention_required=abstain,
    )
