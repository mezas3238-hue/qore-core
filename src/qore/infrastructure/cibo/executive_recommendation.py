"""CF-12 Risk-aware executive recommendation.

The composer deterministically maps explicit functional evidence and explicit Risk
context onto RECOMMEND / ESCALATE / ABSTAIN. It carries Risk evidence/context only:
it never constructs, mutates, or reproduces a Risk decision, and it grants no
execution authority. Risk remains the sole authority for Risk decisions.
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
    CiboGovernedEvidenceKind,
)
from qore.kernel.result import Failure, Result, Success

_CODE_RE = r"[a-z][a-z0-9._-]*"
_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "private_key",
    "secret=",
    "token=",
)


class CiboRecommendationDisposition(StrEnum):
    """Deterministic recommendation dispositions. No Risk decision is represented."""

    RECOMMEND = "recommend"
    ABSTAIN = "abstain"
    ESCALATE = "escalate"


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
    if any(part in value for part in _SENSITIVE_PARTS):
        raise CiboFunctionalValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


@dataclass(frozen=True, slots=True)
class CiboRiskContext:
    """Explicit Risk evidence/context carried by a recommendation.

    It binds an explicit *external-authority-dependent* RISK evidence assessment
    (status=EVIDENCE_DEPENDENT, dependency kind=RISK) plus a descriptive assessment
    code. It does NOT contain a Risk decision or outcome; Risk remains the sole
    decision authority, and a bare opaque ref or a code label can never stand in
    for externally certified Risk evidence. Because CIBO is not a Risk
    certification authority, Risk evidence is always carried through the explicit
    fail-closed dependency seam, never as a manufactured SUFFICIENT assessment.
    """

    risk_evidence: CiboFunctionalEvidence
    risk_assessment_code: str
    assessed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.risk_evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "risk context requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.risk_evidence)
        if self.risk_evidence.status is not CiboEvidenceStatus.EVIDENCE_DEPENDENT:
            raise CiboFunctionalValidationError(
                "risk context requires external-evidence-dependent risk evidence"
            )
        if self.risk_evidence.dependency_kind is not CiboGovernedEvidenceKind.RISK:
            raise CiboFunctionalValidationError(
                "risk context requires a RISK authority dependency"
            )
        object.__setattr__(
            self,
            "risk_assessment_code",
            _validate_code(self.risk_assessment_code, field_name="risk assessment code"),
        )
        _validate_timestamp(self.assessed_at, field_name="risk assessed_at")
        if self.risk_evidence.as_of > self.assessed_at:
            raise CiboFunctionalValidationError(
                "risk evidence must not postdate the risk assessment"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.risk_evidence.logical_values(),
            self.risk_assessment_code,
            self.assessed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboExecutiveRecommendation:
    """An immutable executive recommendation; it carries no Risk decision field."""

    recommendation_code: str
    disposition: CiboRecommendationDisposition
    functional_evidence: CiboFunctionalEvidence
    risk_context: CiboRiskContext | None
    composed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recommendation_code",
            _validate_code(self.recommendation_code, field_name="recommendation code"),
        )
        if type(self.disposition) is not CiboRecommendationDisposition:
            raise CiboFunctionalValidationError(
                "recommendation requires exact CiboRecommendationDisposition"
            )
        if not isinstance(self.functional_evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "recommendation requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.functional_evidence)
        if self.risk_context is not None:
            if not isinstance(self.risk_context, CiboRiskContext):
                raise CiboFunctionalValidationError(
                    "recommendation risk_context must be CiboRiskContext or None"
                )
            CiboRiskContext.__post_init__(self.risk_context)
        _validate_timestamp(self.composed_at, field_name="recommendation composed_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "recommendation requires exact CiboFunctionalAuthority"
            )
        if self.disposition is CiboRecommendationDisposition.RECOMMEND:
            if self.functional_evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "recommend disposition requires sufficient functional evidence"
                )
            if self.risk_context is None:
                raise CiboFunctionalValidationError(
                    "recommend disposition requires risk context"
                )
            if self.authority is not CiboFunctionalAuthority.RECOMMENDATION:
                raise CiboFunctionalValidationError(
                    "recommend disposition requires recommendation authority"
                )
        elif self.disposition is CiboRecommendationDisposition.ABSTAIN:
            if self.functional_evidence.status is CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "abstain disposition must not carry sufficient functional evidence"
                )
            if self.authority is not CiboFunctionalAuthority.ABSTENTION:
                raise CiboFunctionalValidationError(
                    "abstain disposition requires abstention authority"
                )
        else:
            # Parity with the composer: ESCALATE is only reachable from SUFFICIENT
            # functional evidence with no Risk context. A stronger semantic state
            # must not be admitted by direct construction.
            if self.functional_evidence.status is not CiboEvidenceStatus.SUFFICIENT:
                raise CiboFunctionalValidationError(
                    "escalate disposition requires sufficient functional evidence"
                )
            if self.risk_context is not None:
                raise CiboFunctionalValidationError(
                    "escalate disposition must not carry risk context"
                )
            if self.authority is not CiboFunctionalAuthority.ESCALATION:
                raise CiboFunctionalValidationError(
                    "escalate disposition requires escalation authority"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.recommendation_code,
            self.disposition.value,
            self.functional_evidence.logical_values(),
            None if self.risk_context is None else self.risk_context.logical_values(),
            self.composed_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboRiskAwareComposer:
    """Deterministic, stateless risk-aware recommendation composer.

    RECOMMEND when functional evidence is SUFFICIENT and Risk context is present;
    ESCALATE when functional evidence is SUFFICIENT but Risk context is absent;
    ABSTAIN otherwise. It can never produce a Risk decision.
    """

    def compose(
        self,
        *,
        recommendation_code: str,
        functional_evidence: CiboFunctionalEvidence,
        risk_context: CiboRiskContext | None,
        composed_at: datetime,
    ) -> Result[CiboExecutiveRecommendation, CiboFunctionalError]:
        """Choose a disposition deterministically from explicit evidence/context."""
        try:
            normalized_code = _validate_code(
                recommendation_code,
                field_name="recommendation code",
            )
            if not isinstance(functional_evidence, CiboFunctionalEvidence):
                raise CiboFunctionalValidationError(
                    "composer requires CiboFunctionalEvidence"
                )
            CiboFunctionalEvidence.__post_init__(functional_evidence)
            if risk_context is not None:
                if not isinstance(risk_context, CiboRiskContext):
                    raise CiboFunctionalValidationError(
                        "composer risk_context must be CiboRiskContext or None"
                    )
                CiboRiskContext.__post_init__(risk_context)
            _validate_timestamp(composed_at, field_name="recommendation composed_at")

            if functional_evidence.status is CiboEvidenceStatus.SUFFICIENT:
                if risk_context is not None:
                    disposition = CiboRecommendationDisposition.RECOMMEND
                    authority = CiboFunctionalAuthority.RECOMMENDATION
                else:
                    disposition = CiboRecommendationDisposition.ESCALATE
                    authority = CiboFunctionalAuthority.ESCALATION
            else:
                disposition = CiboRecommendationDisposition.ABSTAIN
                authority = CiboFunctionalAuthority.ABSTENTION

            return Success(
                CiboExecutiveRecommendation(
                    recommendation_code=normalized_code,
                    disposition=disposition,
                    functional_evidence=functional_evidence,
                    risk_context=risk_context,
                    composed_at=composed_at,
                    authority=authority,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)

    def logical_values(self) -> tuple[object, ...]:
        return ()
