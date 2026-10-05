"""Redundancy and resilience validation for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResilienceDisposition(StrEnum):
    FULLY_RECONSTRUCTED = "FULLY_RECONSTRUCTED"
    DEGRADED_USABLE = "DEGRADED_USABLE"
    ABSTAIN = "ABSTAIN"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class DependencyFailureReceipt:
    capability_id: str
    failed_dependency_id: str
    critical: bool
    alternate_dependency_ids: tuple[str, ...]
    reconstruction_coverage: float
    uncertainty_increased: bool
    consumers_notified: bool
    disposition: ResilienceDisposition

    def __post_init__(self) -> None:
        if not self.capability_id.strip() or not self.failed_dependency_id.strip():
            raise ValueError("resilience receipt requires identities")
        if not (0.0 <= self.reconstruction_coverage <= 1.0):
            raise ValueError("reconstruction coverage must be in [0,1]")

    @property
    def hidden_single_point_of_failure(self) -> bool:
        return not self.alternate_dependency_ids and not self.critical

    @property
    def passed(self) -> bool:
        if self.hidden_single_point_of_failure:
            return False
        if not self.uncertainty_increased or not self.consumers_notified:
            return False
        if self.critical:
            return self.disposition in {
                ResilienceDisposition.ABSTAIN,
                ResilienceDisposition.FAIL_CLOSED,
            }
        if self.reconstruction_coverage >= 0.95:
            return self.disposition is ResilienceDisposition.FULLY_RECONSTRUCTED
        if self.reconstruction_coverage > 0:
            return self.disposition in {
                ResilienceDisposition.DEGRADED_USABLE,
                ResilienceDisposition.ABSTAIN,
            }
        return self.disposition in {
            ResilienceDisposition.ABSTAIN,
            ResilienceDisposition.FAIL_CLOSED,
        }


@dataclass(frozen=True, slots=True)
class ResilienceAssessment:
    scenario_count: int
    failed_dependency_ids: tuple[str, ...]
    resilience_proven: bool


def assess_resilience(
    receipts: tuple[DependencyFailureReceipt, ...],
) -> ResilienceAssessment:
    if not receipts:
        raise ValueError("resilience assessment requires failure scenarios")
    failed = tuple(
        sorted(
            item.failed_dependency_id
            for item in receipts
            if not item.passed
        )
    )
    return ResilienceAssessment(
        scenario_count=len(receipts),
        failed_dependency_ids=failed,
        resilience_proven=not failed,
    )
