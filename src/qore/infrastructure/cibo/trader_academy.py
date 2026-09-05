"""CF-04 Trader Academy: curriculum stages, experiment-request seam, and loop.

The Academy governs *how a Trader learns and evolves*. Every output here is a
non-authoritative recommendation/request: it never mutates a certified Trader
version, never self-promotes, and never manufactures a new exact version
identity without an explicit new fingerprint/identity supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalBlockedError,
    CiboFunctionalError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.cibo_trader_development_review import (
    CiboDevelopmentReason,
    CiboDevelopmentRecommendation,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
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

# Canonical reason codes that encode the ACCEPT_REJECT_LESSON branch. The reject
# path loops back to DESIGN_EXPERIMENT; the accept path proceeds to a new exact
# version. These are the ONLY two reason codes that may leave ACCEPT_REJECT_LESSON.
_ACCEPT_REASON_CODE = "lesson-accepted"
_REJECT_REASON_CODE = "lesson-rejected-redesign"


class CiboAcademyStage(StrEnum):
    """Deterministic curriculum loop for evolving one Trader version."""

    OBSERVE = "observe"
    DIAGNOSE = "diagnose"
    HYPOTHESIS = "hypothesis"
    DESIGN_EXPERIMENT = "design-experiment"
    TRADER_LAB = "trader-lab"
    MEASURE = "measure"
    ACCEPT_REJECT_LESSON = "accept-reject-lesson"
    NEW_EXACT_VERSION = "new-exact-version"
    REQUALIFY = "requalify"


_STAGE_ORDER: dict[CiboAcademyStage, int] = {
    stage: index for index, stage in enumerate(CiboAcademyStage)
}

# Stages that produce a NEW exact version identity. Reaching either one requires an
# explicit new identity + config fingerprint from the caller: the Academy never
# derives a successor version from the previous one.
_NEW_VERSION_STAGES = frozenset(
    {CiboAcademyStage.NEW_EXACT_VERSION, CiboAcademyStage.REQUALIFY}
)

# Deterministic reason allow-list per development recommendation (mirrors the
# (recommendation, reasons) pairs the review_capability_profile emits).
_REASON_BY_DECISION: dict[
    CiboDevelopmentRecommendation,
    frozenset[CiboDevelopmentReason],
] = {
    CiboDevelopmentRecommendation.CONTINUE_CURRICULUM: frozenset(
        {
            CiboDevelopmentReason.CURRICULUM_INCOMPLETE,
            CiboDevelopmentReason.MISSING_LAB_STAGE,
        }
    ),
    CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED: frozenset(
        {
            CiboDevelopmentReason.EVIDENCE_INSUFFICIENT,
            CiboDevelopmentReason.MISSING_LAB_STAGE,
        }
    ),
    CiboDevelopmentRecommendation.RETRAIN_RETURN_TO_LAB: frozenset(
        {CiboDevelopmentReason.EVIDENCE_STALE}
    ),
    CiboDevelopmentRecommendation.RECOMMEND_PROMOTION: frozenset(
        {CiboDevelopmentReason.EVIDENCE_COMPLETE}
    ),
    CiboDevelopmentRecommendation.RECOMMEND_REJECTION: frozenset(
        {CiboDevelopmentReason.REJECTED_STATE}
    ),
    CiboDevelopmentRecommendation.RECOMMEND_SUSPENSION_REVIEW: frozenset(
        {CiboDevelopmentReason.SUSPENDED_OR_DEGRADED}
    ),
}


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


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
    non_empty: bool = False,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if non_empty and not values:
        raise CiboFunctionalValidationError(f"{field_name} must be non-empty")
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


def _validate_stage_transition(
    from_stage: CiboAcademyStage,
    to_stage: CiboAcademyStage,
    reason_code: str,
) -> None:
    """Enforce the deterministic loop: forward only, except the reject redesign path."""
    if from_stage is to_stage:
        raise CiboFunctionalValidationError("academy transition must change stage")
    if from_stage is CiboAcademyStage.ACCEPT_REJECT_LESSON:
        if to_stage is CiboAcademyStage.NEW_EXACT_VERSION:
            if reason_code != _ACCEPT_REASON_CODE:
                raise CiboFunctionalValidationError(
                    "accept path requires reason 'lesson-accepted'"
                )
            return
        if to_stage is CiboAcademyStage.DESIGN_EXPERIMENT:
            if reason_code != _REJECT_REASON_CODE:
                raise CiboFunctionalValidationError(
                    "reject redesign requires reason 'lesson-rejected-redesign'"
                )
            return
        raise CiboFunctionalValidationError(
            "accept/reject lesson must lead to NEW_EXACT_VERSION or DESIGN_EXPERIMENT"
        )
    if _STAGE_ORDER[to_stage] > _STAGE_ORDER[from_stage]:
        return
    raise CiboFunctionalValidationError(
        "academy transition must move forward in stage order"
    )


def _next_forward_stage(current: CiboAcademyStage) -> CiboAcademyStage:
    order = tuple(CiboAcademyStage)
    index = order.index(current)
    if index == len(order) - 1:
        raise CiboFunctionalValidationError("no forward stage after REQUALIFY")
    return order[index + 1]


def _target_stage(
    current: CiboAcademyStage,
    decision: CiboDevelopmentRecommendation,
) -> CiboAcademyStage:
    if decision is CiboDevelopmentRecommendation.RECOMMEND_PROMOTION:
        return CiboAcademyStage.NEW_EXACT_VERSION
    if decision is CiboDevelopmentRecommendation.RECOMMEND_REJECTION:
        return CiboAcademyStage.DESIGN_EXPERIMENT
    if decision in (
        CiboDevelopmentRecommendation.MORE_EVIDENCE_REQUIRED,
        CiboDevelopmentRecommendation.RETRAIN_RETURN_TO_LAB,
    ):
        return CiboAcademyStage.TRADER_LAB
    if decision is CiboDevelopmentRecommendation.RECOMMEND_SUSPENSION_REVIEW:
        return CiboAcademyStage.DIAGNOSE
    return _next_forward_stage(current)


@dataclass(frozen=True, slots=True)
class CiboExperimentRequest:
    """Typed seam requesting a Trader Lab experiment; it claims no Lab result.

    Authority is fixed to REQUEST: this value requests work, it does not execute
    any experiment, does not implement Trader Lab, and cannot author a Lab outcome.
    """

    request_code: str
    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    hypothesis_code: str
    evidence_refs: tuple[CiboEvidenceRef, ...]
    requested_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_code",
            _validate_code(self.request_code, field_name="request code"),
        )
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboFunctionalValidationError(
                "trader identity must be ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboFunctionalValidationError(
                "config fingerprint must be CiboTraderConfigFingerprint"
            )
        object.__setattr__(
            self,
            "hypothesis_code",
            _validate_code(self.hypothesis_code, field_name="hypothesis code"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(
                self.evidence_refs,
                field_name="evidence refs",
                non_empty=True,
            ),
        )
        _validate_timestamp(self.requested_at, field_name="requested_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "authority must be CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.REQUEST:
            raise CiboFunctionalValidationError(
                "experiment request authority must be REQUEST"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_code,
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.hypothesis_code,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.requested_at.isoformat(),
            self.authority.value,
        )


@dataclass(frozen=True, slots=True)
class CiboAcademyTransition:
    """An immutable, forward-moving record of one academy loop step."""

    from_stage: CiboAcademyStage
    to_stage: CiboAcademyStage
    reason_code: str
    evidence_refs: tuple[CiboEvidenceRef, ...]

    def __post_init__(self) -> None:
        if type(self.from_stage) is not CiboAcademyStage:
            raise CiboFunctionalValidationError("from_stage must be CiboAcademyStage")
        if type(self.to_stage) is not CiboAcademyStage:
            raise CiboFunctionalValidationError("to_stage must be CiboAcademyStage")
        object.__setattr__(
            self,
            "reason_code",
            _validate_code(self.reason_code, field_name="reason code"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="evidence refs"),
        )
        _validate_stage_transition(self.from_stage, self.to_stage, self.reason_code)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.from_stage.value,
            self.to_stage.value,
            self.reason_code,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboAcademy:
    """Deterministic, stateless Trader Academy policy foundation.

    It requests experiments and maps development-review recommendations onto the
    curriculum loop. It never mutates a certified Trader version and never grants
    promotion or execution authority.
    """

    def request_experiment(
        self,
        *,
        request_code: str,
        trader_identity: ResearchDecisionEvaluatorIdentity,
        config_fingerprint: CiboTraderConfigFingerprint,
        hypothesis_code: str,
        evidence_refs: tuple[CiboEvidenceRef, ...],
        requested_at: datetime,
    ) -> Result[CiboExperimentRequest, CiboFunctionalError]:
        """Request a Trader Lab experiment for an exact Trader version."""
        try:
            return Success(
                CiboExperimentRequest(
                    request_code=request_code,
                    trader_identity=trader_identity,
                    config_fingerprint=config_fingerprint,
                    hypothesis_code=hypothesis_code,
                    evidence_refs=evidence_refs,
                    requested_at=requested_at,
                    authority=CiboFunctionalAuthority.REQUEST,
                )
            )
        except CiboFunctionalError as error:
            return Failure(error)

    def advance(
        self,
        current: CiboAcademyStage,
        *,
        decision: CiboDevelopmentRecommendation,
        reason: CiboDevelopmentReason,
        new_identity: ResearchDecisionEvaluatorIdentity | None = None,
        new_fingerprint: CiboTraderConfigFingerprint | None = None,
    ) -> Result[CiboAcademyStage, CiboFunctionalError]:
        """Deterministically map a development review recommendation to a next stage.

        Producing NEW_EXACT_VERSION or REQUALIFY requires an explicit new identity
        and config fingerprint: the Academy never derives a successor version from
        the previous one and never self-promotes.
        """
        if type(current) is not CiboAcademyStage:
            return Failure(CiboFunctionalValidationError("current must be CiboAcademyStage"))
        if type(decision) is not CiboDevelopmentRecommendation:
            return Failure(
                CiboFunctionalValidationError(
                    "decision must be CiboDevelopmentRecommendation"
                )
            )
        if type(reason) is not CiboDevelopmentReason:
            return Failure(
                CiboFunctionalValidationError("reason must be CiboDevelopmentReason")
            )
        if new_identity is not None and not isinstance(
            new_identity,
            ResearchDecisionEvaluatorIdentity,
        ):
            return Failure(
                CiboFunctionalValidationError(
                    "new_identity must be ResearchDecisionEvaluatorIdentity or None"
                )
            )
        if new_fingerprint is not None and not isinstance(
            new_fingerprint,
            CiboTraderConfigFingerprint,
        ):
            return Failure(
                CiboFunctionalValidationError(
                    "new_fingerprint must be CiboTraderConfigFingerprint or None"
                )
            )

        if reason not in _REASON_BY_DECISION[decision]:
            return Failure(
                CiboFunctionalValidationError(
                    "development reason is inconsistent with the recommendation"
                )
            )

        target = _target_stage(current, decision)
        if target in _NEW_VERSION_STAGES:
            if new_identity is None or new_fingerprint is None:
                return Failure(
                    CiboFunctionalBlockedError(
                        f"{target.value} requires an explicit new identity "
                        "and config fingerprint"
                    )
                )
        elif new_identity is not None or new_fingerprint is not None:
            return Failure(
                CiboFunctionalValidationError(
                    "explicit new identity/fingerprint only valid for a new version stage"
                )
            )
        return Success(target)
