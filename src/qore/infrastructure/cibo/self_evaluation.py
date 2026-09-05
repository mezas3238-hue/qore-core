"""CF-18 — Self-Evaluation / A-B Contribution.

A fair A/B evaluation compares the SAME exact trader versions/configs across the
two risk-mode arms over the SAME window. No cherry-picking, no retroactive
version substitution, no authority beyond ``OPINION``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalEvidence,
    CiboFunctionalValidationError,
    _validate_code,
    _validate_timestamp,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchRunValidationError
from qore.kernel.result import Failure, Result, Success


class CiboAbArm(StrEnum):
    """A/B experiment arms expressed as the two exact risk-mode assignments."""

    TRADERS_RISK_ONLY = "traders-risk-only"
    CIBO_MANAGED_TRADERS_RISK = "cibo-managed-traders-risk"


def _revalidate_evidence(evidence: CiboFunctionalEvidence) -> None:
    try:
        CiboFunctionalEvidence.__post_init__(evidence)
    except CiboFunctionalError:
        raise
    except (AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "evidence must be a valid CiboFunctionalEvidence"
        ) from None


def _revalidate_identity(identity: ResearchDecisionEvaluatorIdentity) -> None:
    try:
        ResearchDecisionEvaluatorIdentity.__post_init__(identity)
        identity.family.__post_init__()
        identity.schema_version.__post_init__()
        identity.software_revision.__post_init__()
    except (
        ResearchLineageValidationError,
        ResearchRunValidationError,
        AttributeError,
        TypeError,
    ):
        raise CiboFunctionalValidationError(
            "trader version must be a valid ResearchDecisionEvaluatorIdentity"
        ) from None


def _validate_version_tuple(
    values: tuple[ResearchDecisionEvaluatorIdentity, ...],
    *,
    field_name: str,
) -> tuple[ResearchDecisionEvaluatorIdentity, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, ResearchDecisionEvaluatorIdentity) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of ResearchDecisionEvaluatorIdentity"
        )
    for item in values:
        _revalidate_identity(item)
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return values


@dataclass(frozen=True, slots=True)
class CiboAbEvaluation:
    """Fair, opinion-only A/B evaluation with identical versions and window."""

    arm_a: CiboAbArm
    arm_b: CiboAbArm
    trader_versions_a: tuple[ResearchDecisionEvaluatorIdentity, ...]
    trader_versions_b: tuple[ResearchDecisionEvaluatorIdentity, ...]
    window_start: datetime
    window_end: datetime
    evidence: CiboFunctionalEvidence
    conclusion_code: str
    assessed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if type(self.arm_a) is not CiboAbArm:
            raise CiboFunctionalValidationError("A/B arm_a must be CiboAbArm")
        if type(self.arm_b) is not CiboAbArm:
            raise CiboFunctionalValidationError("A/B arm_b must be CiboAbArm")
        object.__setattr__(
            self,
            "trader_versions_a",
            _validate_version_tuple(self.trader_versions_a, field_name="trader versions a"),
        )
        object.__setattr__(
            self,
            "trader_versions_b",
            _validate_version_tuple(self.trader_versions_b, field_name="trader versions b"),
        )
        _validate_timestamp(self.window_start, field_name="A/B window start")
        _validate_timestamp(self.window_end, field_name="A/B window end")
        if not isinstance(self.evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "A/B evaluation requires CiboFunctionalEvidence"
            )
        _revalidate_evidence(self.evidence)
        object.__setattr__(
            self,
            "conclusion_code",
            _validate_code(self.conclusion_code, field_name="conclusion code"),
        )
        _validate_timestamp(self.assessed_at, field_name="A/B assessed_at")
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError("A/B evaluation authority must be opinion")
        if self.arm_a is not CiboAbArm.TRADERS_RISK_ONLY:
            raise CiboFunctionalValidationError(
                "fair A/B requires arm A to be traders-risk-only"
            )
        if self.arm_b is not CiboAbArm.CIBO_MANAGED_TRADERS_RISK:
            raise CiboFunctionalValidationError(
                "fair A/B requires arm B to be cibo-managed-traders-risk"
            )
        if self.trader_versions_a != self.trader_versions_b:
            raise CiboFunctionalValidationError(
                "fair A/B requires identical trader versions across arms"
            )
        if self.window_start >= self.window_end:
            raise CiboFunctionalValidationError(
                "fair A/B requires a window that starts before it ends"
            )
        if self.assessed_at < self.window_end:
            raise CiboFunctionalValidationError(
                "fair A/B assessment cannot predate the window end"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.arm_a.value,
            self.arm_b.value,
            tuple(item.logical_values() for item in self.trader_versions_a),
            tuple(item.logical_values() for item in self.trader_versions_b),
            self.window_start.isoformat(),
            self.window_end.isoformat(),
            self.evidence.logical_values(),
            self.conclusion_code,
            self.assessed_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboSelfEvaluation:
    """Deterministic, stateless self-evaluation / A-B contribution."""

    def evaluate(
        self,
        *,
        arm_a: CiboAbArm,
        arm_b: CiboAbArm,
        trader_versions_a: tuple[ResearchDecisionEvaluatorIdentity, ...],
        trader_versions_b: tuple[ResearchDecisionEvaluatorIdentity, ...],
        window_start: datetime,
        window_end: datetime,
        evidence: CiboFunctionalEvidence,
        conclusion_code: str,
        assessed_at: datetime,
    ) -> Result[CiboAbEvaluation, CiboFunctionalError]:
        """Produce a fair, opinion-only A/B evaluation."""
        if not isinstance(evidence, CiboFunctionalEvidence):
            return Failure(
                CiboFunctionalValidationError("evidence must be CiboFunctionalEvidence")
            )
        try:
            return Success(
                CiboAbEvaluation(
                    arm_a=arm_a,
                    arm_b=arm_b,
                    trader_versions_a=trader_versions_a,
                    trader_versions_b=trader_versions_b,
                    window_start=window_start,
                    window_end=window_end,
                    evidence=evidence,
                    conclusion_code=conclusion_code,
                    assessed_at=assessed_at,
                    authority=CiboFunctionalAuthority.OPINION,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)
