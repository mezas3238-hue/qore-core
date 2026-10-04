"""Authority-isolation contract for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Authority(StrEnum):
    EXECUTION = "EXECUTION"
    RISK = "RISK"
    SIZING = "SIZING"
    BROKER_MUTATION = "BROKER_MUTATION"
    PRODUCTIVE_PROMOTION = "PRODUCTIVE_PROMOTION"
    PROTECTED_HOLDOUT_OPENING = "PROTECTED_HOLDOUT_OPENING"
    CERTIFICATION = "CERTIFICATION"


@dataclass(frozen=True, slots=True)
class AuthorityIsolationReceipt:
    component_id: str
    requested_authorities: frozenset[Authority]
    granted_authorities: frozenset[Authority]
    read_only: bool
    research_only: bool

    @property
    def passed(self) -> bool:
        return (
            bool(self.component_id.strip())
            and not self.requested_authorities
            and not self.granted_authorities
            and self.read_only
            and self.research_only
        )


@dataclass(frozen=True, slots=True)
class AuthorityIsolationAssessment:
    component_count: int
    failed_component_ids: tuple[str, ...]
    all_components_authority_free: bool


def assess_authority_isolation(
    receipts: tuple[AuthorityIsolationReceipt, ...],
) -> AuthorityIsolationAssessment:
    if not receipts:
        raise ValueError("authority isolation requires component receipts")
    ids = tuple(item.component_id for item in receipts)
    if len(ids) != len(set(ids)):
        raise ValueError("authority component ids must be unique")
    failed = tuple(sorted(item.component_id for item in receipts if not item.passed))
    return AuthorityIsolationAssessment(
        component_count=len(receipts),
        failed_component_ids=failed,
        all_components_authority_free=not failed,
    )
