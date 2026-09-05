"""CF-05 Opportunity / Profit Search.

A hypothesis is an idea, never an edge. VALIDATED/RECOMMENDED states require
SUFFICIENT evidence, RECOMMENDED requires RECOMMENDATION authority, HYPOTHESIS
requires OPINION authority, and REJECTED/EVIDENCE_INSUFFICIENT carry ABSTENTION.
``evaluate`` revalidates nested material and never elevates state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Failure, Result, Success

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboOpportunityState(StrEnum):
    """Closed lifecycle of an opportunity hypothesis."""

    HYPOTHESIS = "hypothesis"
    EVIDENCE_INSUFFICIENT = "evidence-insufficient"
    VALIDATED = "validated"
    RECOMMENDED = "recommended"
    REJECTED = "rejected"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboFunctionalValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboFunctionalValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboFunctionalValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_market_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboOpportunityHypothesis:
    """Immutable opportunity hypothesis with a strictly bounded authority ladder."""

    opportunity_code: str
    market_refs: tuple[CiboEvidenceRef, ...]
    evidence: CiboFunctionalEvidence
    state: CiboOpportunityState
    authority: CiboFunctionalAuthority
    declared_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "opportunity_code",
            _validate_code(self.opportunity_code, field_name="opportunity code"),
        )
        object.__setattr__(
            self,
            "market_refs",
            _validate_market_refs(self.market_refs, field_name="market refs"),
        )
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "opportunity requires CiboFunctionalEvidence"
            )
        # Recursive revalidation: a reflectively corrupted SUFFICIENT evidence
        # (e.g. no governed material) must not mint VALIDATED/RECOMMENDED by
        # direct construction; re-enter child validation before trusting status.
        CiboFunctionalEvidence.__post_init__(self.evidence)
        if type(self.state) is not CiboOpportunityState:
            raise CiboFunctionalValidationError(
                "opportunity requires exact CiboOpportunityState"
            )
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "opportunity requires exact CiboFunctionalAuthority"
            )
        _validate_timestamp(self.declared_at, field_name="opportunity declared_at")

        if self.state is CiboOpportunityState.HYPOTHESIS:
            if self.authority is not CiboFunctionalAuthority.OPINION:
                raise CiboFunctionalValidationError(
                    "hypothesis authority must be OPINION"
                )
        elif self.state in (
            CiboOpportunityState.EVIDENCE_INSUFFICIENT,
            CiboOpportunityState.REJECTED,
        ):
            if self.authority is not CiboFunctionalAuthority.ABSTENTION:
                raise CiboFunctionalValidationError(
                    f"{self.state.value} authority must be ABSTENTION"
                )
        elif self.state in (
            CiboOpportunityState.VALIDATED,
            CiboOpportunityState.RECOMMENDED,
        ):
            if self.evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    f"{self.state.value} opportunity requires sufficient evidence"
                )
            if self.authority is not CiboFunctionalAuthority.RECOMMENDATION:
                raise CiboFunctionalValidationError(
                    f"{self.state.value} opportunity authority must be RECOMMENDATION"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.opportunity_code,
            tuple(ref.logical_values() for ref in self.market_refs),
            self.evidence.logical_values(),
            self.state.value,
            self.authority.value,
            self.declared_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboOpportunitySearch:
    """Stateless deterministic evaluator of opportunity hypotheses."""

    def evaluate(
        self,
        hypothesis: CiboOpportunityHypothesis,
    ) -> Result[CiboOpportunityHypothesis, CiboFunctionalError]:
        """Revalidate nested material and return it unchanged; never elevate state."""
        try:
            if not isinstance(hypothesis, CiboOpportunityHypothesis):
                raise CiboFunctionalValidationError(
                    "hypothesis must be CiboOpportunityHypothesis"
                )
            if not isinstance(hypothesis.evidence, CiboFunctionalEvidence):
                raise CiboFunctionalValidationError(
                    "hypothesis evidence must be CiboFunctionalEvidence"
                )
            evidence = CiboFunctionalEvidence(
                status=hypothesis.evidence.status,
                evidence_refs=hypothesis.evidence.evidence_refs,
                as_of=hypothesis.evidence.as_of,
                dependency_kind=hypothesis.evidence.dependency_kind,
                reasons=hypothesis.evidence.reasons,
            )
            revalidated = CiboOpportunityHypothesis(
                opportunity_code=hypothesis.opportunity_code,
                market_refs=hypothesis.market_refs,
                evidence=evidence,
                state=hypothesis.state,
                authority=hypothesis.authority,
                declared_at=hypothesis.declared_at,
            )
            return Success(revalidated)
        except CiboFunctionalError as error:
            return Failure(error)
