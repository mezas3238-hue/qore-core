"""Operational reality receipts for QORE Shared Lab cognitive/core lane.

Measures latency/deadline utility, information value, and governed degraded
operation without granting productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DegradedDisposition(StrEnum):
    FULL = "FULL"
    DEGRADED_USABLE = "DEGRADED_USABLE"
    ABSTAIN = "ABSTAIN"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class ResourceLatencyReceipt:
    capability_id: str
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    decision_deadline_ms: float
    peak_memory_mb: float
    cpu_time_ms: float
    io_bytes: int

    def __post_init__(self) -> None:
        values = (
            self.latency_p50_ms,
            self.latency_p95_ms,
            self.latency_p99_ms,
            self.decision_deadline_ms,
            self.peak_memory_mb,
            self.cpu_time_ms,
        )
        if any(value < 0 for value in values) or self.io_bytes < 0:
            raise ValueError("resource/latency metrics cannot be negative")
        if not (
            self.latency_p50_ms <= self.latency_p95_ms <= self.latency_p99_ms
        ):
            raise ValueError("latency percentiles must be monotonic")
        if self.decision_deadline_ms <= 0:
            raise ValueError("decision deadline must be positive")

    @property
    def deadline_pass(self) -> bool:
        return self.latency_p99_ms <= self.decision_deadline_ms


@dataclass(frozen=True, slots=True)
class InformationValueReceipt:
    capability_id: str
    observations: int
    decision_changes: int
    uncertainty_reductions: int
    avoided_false_opportunities: int
    preserved_winners: int
    incremental_information_gain: float
    incremental_value: float
    acquisition_cost_units: float

    def __post_init__(self) -> None:
        counts = (
            self.observations,
            self.decision_changes,
            self.uncertainty_reductions,
            self.avoided_false_opportunities,
            self.preserved_winners,
        )
        if any(value < 0 for value in counts):
            raise ValueError("information-value counts cannot be negative")
        if self.acquisition_cost_units < 0:
            raise ValueError("acquisition cost cannot be negative")

    @property
    def changed_something(self) -> bool:
        return any(
            (
                self.decision_changes,
                self.uncertainty_reductions,
                self.avoided_false_opportunities,
                self.preserved_winners,
            )
        )

    @property
    def useful(self) -> bool:
        return (
            self.observations > 0
            and self.changed_something
            and (
                self.incremental_information_gain > 0
                or self.incremental_value > 0
            )
        )

    @property
    def value_per_cost_unit(self) -> float:
        if self.acquisition_cost_units == 0:
            return self.incremental_value
        return self.incremental_value / self.acquisition_cost_units


@dataclass(frozen=True, slots=True)
class DegradedModeReceipt:
    capability_id: str
    failed_dependency_ids: tuple[str, ...]
    critical_dependency_failed: bool
    uncertainty_increased: bool
    affected_consumers_notified: bool
    disabled_capability_ids: tuple[str, ...]
    disposition: DegradedDisposition

    @property
    def passed(self) -> bool:
        if not self.failed_dependency_ids:
            return self.disposition is DegradedDisposition.FULL
        if not self.uncertainty_increased or not self.affected_consumers_notified:
            return False
        if self.critical_dependency_failed:
            return self.disposition in {
                DegradedDisposition.ABSTAIN,
                DegradedDisposition.FAIL_CLOSED,
            }
        return self.disposition in {
            DegradedDisposition.DEGRADED_USABLE,
            DegradedDisposition.ABSTAIN,
        }


@dataclass(frozen=True, slots=True)
class OperationalRealityAssessment:
    capability_id: str
    latency_pass: bool
    information_value_pass: bool
    degraded_mode_pass: bool
    operationally_usable: bool


def assess_operational_reality(
    *,
    latency: ResourceLatencyReceipt,
    information_value: InformationValueReceipt,
    degraded_mode: DegradedModeReceipt,
) -> OperationalRealityAssessment:
    ids = {
        latency.capability_id,
        information_value.capability_id,
        degraded_mode.capability_id,
    }
    if len(ids) != 1:
        raise ValueError("operational receipts must belong to one capability")
    usable = latency.deadline_pass and information_value.useful and degraded_mode.passed
    return OperationalRealityAssessment(
        capability_id=latency.capability_id,
        latency_pass=latency.deadline_pass,
        information_value_pass=information_value.useful,
        degraded_mode_pass=degraded_mode.passed,
        operationally_usable=usable,
    )
