"""CF-06 — Portfolio / Allocation Intelligence.

CIBO assesses a portfolio allocation and emits an immutable, recommendation-only
conclusion. The authority ceiling is ``RECOMMENDATION``; when evidence is not
sufficient the output is ``INSUFFICIENT_EVIDENCE`` with ``ABSTENTION`` authority,
never a fabricated conclusion and never a Risk decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    _validate_code,
    _validate_evidence_refs,
    _validate_timestamp,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Result, Success


class CiboAllocationConclusion(StrEnum):
    """Portfolio allocation conclusion produced only from explicit evidence."""

    DIVERSIFIED = "diversified"
    CONCENTRATED = "concentrated"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


def _revalidate_evidence(evidence: CiboFunctionalEvidence) -> None:
    """Re-enter functional-evidence invariants at the recommendation trust boundary."""
    try:
        CiboFunctionalEvidence.__post_init__(evidence)
    except CiboFunctionalError:
        raise
    except (AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "evidence must be a valid CiboFunctionalEvidence"
        ) from None


@dataclass(frozen=True, slots=True)
class CiboAllocationRecommendation:
    """Immutable recommendation-only allocation conclusion with no Risk authority."""

    allocation_code: str
    participation_refs: tuple[CiboEvidenceRef, ...]
    conclusion: CiboAllocationConclusion
    evidence: CiboFunctionalEvidence
    authority: CiboFunctionalAuthority
    recommended_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "allocation_code",
            _validate_code(self.allocation_code, field_name="allocation code"),
        )
        object.__setattr__(
            self,
            "participation_refs",
            _validate_evidence_refs(self.participation_refs, field_name="participation refs"),
        )
        if type(self.conclusion) is not CiboAllocationConclusion:
            raise CiboFunctionalValidationError(
                "allocation recommendation requires CiboAllocationConclusion"
            )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "allocation recommendation requires CiboFunctionalEvidence"
            )
        _revalidate_evidence(self.evidence)
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "allocation recommendation requires CiboFunctionalAuthority"
            )
        _validate_timestamp(self.recommended_at, field_name="allocation recommended_at")
        if self.conclusion is CiboAllocationConclusion.INSUFFICIENT_EVIDENCE:
            if self.authority is not CiboFunctionalAuthority.ABSTENTION:
                raise CiboFunctionalValidationError(
                    "insufficient-evidence conclusion requires abstention authority"
                )
            return
        if self.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
            raise CiboFunctionalValidationError(
                "allocation conclusion requires sufficient evidence"
            )
        if self.authority is not CiboFunctionalAuthority.RECOMMENDATION:
            raise CiboFunctionalValidationError(
                "concluded allocation requires recommendation authority"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.allocation_code,
            tuple(item.logical_values() for item in self.participation_refs),
            self.conclusion.value,
            self.evidence.logical_values(),
            self.authority.value,
            self.recommended_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboPortfolioIntelligence:
    """Deterministic, stateless portfolio allocation intelligence."""

    def recommend(
        self,
        evidence: CiboFunctionalEvidence,
        *,
        participation_refs: tuple[CiboEvidenceRef, ...],
        allocation_code: str,
        recommended_at: datetime,
    ) -> Result[CiboAllocationRecommendation, CiboFunctionalError]:
        """Produce a recommendation-only allocation conclusion.

        Sufficient evidence yields the safe diversified-allocation recommendation;
        any other evidence status yields ``INSUFFICIENT_EVIDENCE`` with abstention.
        A ``CONCENTRATED`` conclusion is expressible through direct construction of
        ``CiboAllocationRecommendation`` and is validated identically.
        """
        if not isinstance(evidence, CiboFunctionalEvidence):
            return Failure(
                CiboFunctionalValidationError("evidence must be CiboFunctionalEvidence")
            )
        try:
            _revalidate_evidence(evidence)
            normalized_refs = _validate_evidence_refs(
                participation_refs,
                field_name="participation refs",
            )
            normalized_code = _validate_code(allocation_code, field_name="allocation code")
            _validate_timestamp(recommended_at, field_name="recommended_at")
        except CiboFunctionalError as error:
            return Failure(error)
        if evidence.status is CiboEvidenceStatus.SUFFICIENT:
            conclusion = CiboAllocationConclusion.DIVERSIFIED
            authority = CiboFunctionalAuthority.RECOMMENDATION
        else:
            conclusion = CiboAllocationConclusion.INSUFFICIENT_EVIDENCE
            authority = CiboFunctionalAuthority.ABSTENTION
        try:
            return Success(
                CiboAllocationRecommendation(
                    allocation_code=normalized_code,
                    participation_refs=normalized_refs,
                    conclusion=conclusion,
                    evidence=evidence,
                    authority=authority,
                    recommended_at=recommended_at,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
