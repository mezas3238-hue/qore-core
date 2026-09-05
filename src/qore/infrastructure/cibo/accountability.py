"""CF-07/08/09/17/18/19/20 Counterfactual Review + Economic Accountability (D6).

Two governed, deterministic contracts:

1. ``CiboCounterfactualAssessment`` — evidence-bound counterfactual questions
   (abstain-vs-act, alternate trader/version, alternate timing/execution,
   cost/slippage/liquidity sensitivity, regime-luck-vs-skill, lower-risk
   alternatives, comparable historical/replay regimes, and explicit unknowable
   outcomes). A counterfactual is never fabricated and never uses hindsight:
   SUPPORTED requires explicit evidence plus a conclusion, and the cited evidence
   horizon can never postdate the assessment.

2. ``CiboInterventionAttribution`` — an auditable intervention lineage
   (market/situation -> evidence -> Traders/functions -> opinions/hypotheses ->
   CIBO synthesis -> recommendation -> external/governed decision -> outcome ->
   attribution -> learning disposition) with exact intervention/version binding,
   pre-intervention evidence, prescribed development/research, post-intervention
   evidence, and a governed attribution state. A profitable outcome is never
   sufficient proof of CIBO causation: ATTRIBUTED requires explicit causal
   isolation evidence.

The resulting evidence feeds #469 DEMO A/B evaluation (A = Traders + Risk, B =
same Traders + CIBO + Risk) via the existing CF-18 ``CiboAbEvaluation`` arms
without granting any DEMO execution authority here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo.contracts import (
    CiboFunctionalAuthority,
    CiboFunctionalError,
    CiboFunctionalValidationError,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
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


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboFunctionalValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
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


def _validate_identities(
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
    if len(set(values)) != len(values):
        raise CiboFunctionalValidationError(f"{field_name} must not contain duplicates")
    return tuple(
        sorted(
            values,
            key=lambda identity: (
                identity.family.value,
                identity.schema_version.value,
                identity.software_revision.value,
            ),
        )
    )


class CiboCounterfactualKind(StrEnum):
    """Closed catalog of supported counterfactual question kinds."""

    ABSTAIN_VS_ACT = "abstain-vs-act"
    ALTERNATE_TRADER = "alternate-trader"
    ALTERNATE_TIMING = "alternate-timing"
    COST_SLIPPAGE_LIQUIDITY = "cost-slippage-liquidity"
    REGIME_LUCK_VS_SKILL = "regime-luck-vs-skill"
    LOWER_RISK_ALTERNATIVE = "lower-risk-alternative"
    COMPARABLE_REGIME = "comparable-regime"
    UNKNOWABLE = "unknowable"


class CiboCounterfactualStatus(StrEnum):
    """Fail-closed counterfactual conclusion status."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWABLE = "unknowable"


@dataclass(frozen=True, slots=True)
class CiboCounterfactualAssessment:
    """Evidence-bound counterfactual answer (OPINION authority, no hindsight)."""

    kind: CiboCounterfactualKind
    question_code: str
    status: CiboCounterfactualStatus
    evidence_refs: tuple[CiboEvidenceRef, ...]
    conclusion_code: str | None
    evidence_horizon: datetime
    assessed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if type(self.kind) is not CiboCounterfactualKind:
            raise CiboFunctionalValidationError(
                "counterfactual requires exact CiboCounterfactualKind"
            )
        object.__setattr__(
            self,
            "question_code",
            _validate_code(self.question_code, field_name="counterfactual question"),
        )
        if type(self.status) is not CiboCounterfactualStatus:
            raise CiboFunctionalValidationError(
                "counterfactual requires exact CiboCounterfactualStatus"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="counterfactual evidence"),
        )
        if self.conclusion_code is not None:
            object.__setattr__(
                self,
                "conclusion_code",
                _validate_code(self.conclusion_code, field_name="counterfactual conclusion"),
            )
        _validate_timestamp(self.evidence_horizon, field_name="counterfactual evidence horizon")
        _validate_timestamp(self.assessed_at, field_name="counterfactual assessed_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "counterfactual requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "counterfactual authority must be OPINION"
            )
        # No fabricated counterfactuals: SUPPORTED requires evidence and a
        # conclusion; UNSUPPORTED/UNKNOWABLE carry no conclusion.
        if self.status is CiboCounterfactualStatus.SUPPORTED:
            if not self.evidence_refs:
                raise CiboFunctionalValidationError(
                    "supported counterfactual requires evidence refs"
                )
            if self.conclusion_code is None:
                raise CiboFunctionalValidationError(
                    "supported counterfactual requires a conclusion code"
                )
        elif self.conclusion_code is not None:
            raise CiboFunctionalValidationError(
                "unsupported/unknowable counterfactual must not carry a conclusion"
            )
        if self.kind is CiboCounterfactualKind.UNKNOWABLE:
            if self.status is not CiboCounterfactualStatus.UNKNOWABLE:
                raise CiboFunctionalValidationError(
                    "unknowable counterfactual must be UNKNOWABLE"
                )
        # No hindsight laundering: the evidence horizon must not postdate the
        # assessment instant.
        if self.evidence_horizon > self.assessed_at:
            raise CiboFunctionalValidationError(
                "counterfactual evidence must not postdate the assessment"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.question_code,
            self.status.value,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.conclusion_code,
            self.evidence_horizon.isoformat(),
            self.assessed_at.isoformat(),
            self.authority.value,
        )


def assess_counterfactual(
    *,
    kind: CiboCounterfactualKind,
    question_code: str,
    status: CiboCounterfactualStatus,
    evidence_refs: tuple[CiboEvidenceRef, ...],
    conclusion_code: str | None,
    evidence_horizon: datetime,
    assessed_at: datetime,
) -> Result[CiboCounterfactualAssessment, CiboFunctionalError]:
    """Produce a deterministic, fail-closed counterfactual assessment."""
    try:
        return Success(
            CiboCounterfactualAssessment(
                kind=kind,
                question_code=question_code,
                status=status,
                evidence_refs=evidence_refs,
                conclusion_code=conclusion_code,
                evidence_horizon=evidence_horizon,
                assessed_at=assessed_at,
                authority=CiboFunctionalAuthority.OPINION,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class CiboInterventionLineage:
    """Auditable lineage of a material CIBO recommendation/intervention."""

    situation_code: str
    evidence_refs: tuple[CiboEvidenceRef, ...]
    trader_identities: tuple[ResearchDecisionEvaluatorIdentity, ...]
    function_codes: tuple[str, ...]
    opinion_codes: tuple[str, ...]
    synthesis_code: str
    recommendation_code: str
    decision_code: str | None
    outcome_ref: CiboEvidenceRef | None
    learning_disposition_code: str | None
    recorded_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "situation_code",
            _validate_code(self.situation_code, field_name="situation code"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="lineage evidence"),
        )
        object.__setattr__(
            self,
            "trader_identities",
            _validate_identities(self.trader_identities, field_name="lineage traders"),
        )
        object.__setattr__(
            self,
            "function_codes",
            _validate_codes(self.function_codes, field_name="lineage functions"),
        )
        object.__setattr__(
            self,
            "opinion_codes",
            _validate_codes(self.opinion_codes, field_name="lineage opinions"),
        )
        object.__setattr__(
            self,
            "synthesis_code",
            _validate_code(self.synthesis_code, field_name="lineage synthesis"),
        )
        object.__setattr__(
            self,
            "recommendation_code",
            _validate_code(self.recommendation_code, field_name="lineage recommendation"),
        )
        if self.decision_code is not None:
            object.__setattr__(
                self,
                "decision_code",
                _validate_code(self.decision_code, field_name="lineage decision"),
            )
        if self.outcome_ref is not None and not isinstance(
            self.outcome_ref,
            CiboEvidenceRef,
        ):
            raise CiboFunctionalValidationError(
                "lineage outcome_ref must be CiboEvidenceRef or None"
            )
        if self.learning_disposition_code is not None:
            object.__setattr__(
                self,
                "learning_disposition_code",
                _validate_code(
                    self.learning_disposition_code,
                    field_name="learning disposition",
                ),
            )
        _validate_timestamp(self.recorded_at, field_name="lineage recorded_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.situation_code,
            tuple(item.logical_values() for item in self.evidence_refs),
            tuple(item.logical_values() for item in self.trader_identities),
            self.function_codes,
            self.opinion_codes,
            self.synthesis_code,
            self.recommendation_code,
            self.decision_code,
            None if self.outcome_ref is None else self.outcome_ref.logical_values(),
            self.learning_disposition_code,
            self.recorded_at.isoformat(),
        )


class CiboAttributionState(StrEnum):
    """Governed intervention attribution state. Profit never implies ATTRIBUTED."""

    ATTRIBUTED = "attributed"
    UNATTRIBUTED = "unattributed"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    CONFOUNDED = "confounded"


def _derive_attribution(
    *,
    post_intervention_evidence: tuple[CiboEvidenceRef, ...],
    causal_isolation_evidence: tuple[CiboEvidenceRef, ...],
    confounded: bool,
) -> CiboAttributionState:
    if confounded:
        return CiboAttributionState.CONFOUNDED
    if not post_intervention_evidence:
        return CiboAttributionState.INSUFFICIENT_EVIDENCE
    if causal_isolation_evidence:
        return CiboAttributionState.ATTRIBUTED
    return CiboAttributionState.UNATTRIBUTED


@dataclass(frozen=True, slots=True)
class CiboInterventionAttribution:
    """Exact intervention/version attribution; profitable outcome != causation."""

    intervention_id: str
    intervention_version: str
    lineage: CiboInterventionLineage
    pre_intervention_evidence: tuple[CiboEvidenceRef, ...]
    prescribed_development: tuple[str, ...]
    prescribed_research: tuple[str, ...]
    post_intervention_evidence: tuple[CiboEvidenceRef, ...]
    causal_isolation_evidence: tuple[CiboEvidenceRef, ...]
    confounded: bool
    attribution_state: CiboAttributionState
    assessed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "intervention_id",
            _validate_code(self.intervention_id, field_name="intervention id"),
        )
        object.__setattr__(
            self,
            "intervention_version",
            _validate_code(self.intervention_version, field_name="intervention version"),
        )
        if not isinstance(self.lineage, CiboInterventionLineage):
            raise CiboFunctionalValidationError(
                "attribution requires CiboInterventionLineage"
            )
        CiboInterventionLineage.__post_init__(self.lineage)
        object.__setattr__(
            self,
            "pre_intervention_evidence",
            _validate_evidence_refs(
                self.pre_intervention_evidence,
                field_name="pre-intervention evidence",
            ),
        )
        object.__setattr__(
            self,
            "prescribed_development",
            _validate_codes(
                self.prescribed_development,
                field_name="prescribed development",
            ),
        )
        object.__setattr__(
            self,
            "prescribed_research",
            _validate_codes(self.prescribed_research, field_name="prescribed research"),
        )
        object.__setattr__(
            self,
            "post_intervention_evidence",
            _validate_evidence_refs(
                self.post_intervention_evidence,
                field_name="post-intervention evidence",
            ),
        )
        object.__setattr__(
            self,
            "causal_isolation_evidence",
            _validate_evidence_refs(
                self.causal_isolation_evidence,
                field_name="causal isolation evidence",
            ),
        )
        if type(self.confounded) is not bool:
            raise CiboFunctionalValidationError(
                "attribution confounded flag must be an exact bool"
            )
        if type(self.attribution_state) is not CiboAttributionState:
            raise CiboFunctionalValidationError(
                "attribution requires exact CiboAttributionState"
            )
        _validate_timestamp(self.assessed_at, field_name="attribution assessed_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "attribution requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.OPINION:
            raise CiboFunctionalValidationError(
                "attribution authority must be OPINION"
            )
        expected = _derive_attribution(
            post_intervention_evidence=self.post_intervention_evidence,
            causal_isolation_evidence=self.causal_isolation_evidence,
            confounded=self.confounded,
        )
        if self.attribution_state is not expected:
            raise CiboFunctionalValidationError(
                "attribution state must equal the evidence-bound derivation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.intervention_id,
            self.intervention_version,
            self.lineage.logical_values(),
            tuple(item.logical_values() for item in self.pre_intervention_evidence),
            self.prescribed_development,
            self.prescribed_research,
            tuple(item.logical_values() for item in self.post_intervention_evidence),
            tuple(item.logical_values() for item in self.causal_isolation_evidence),
            self.confounded,
            self.attribution_state.value,
            self.assessed_at.isoformat(),
            self.authority.value,
        )


def attribute_intervention(
    *,
    intervention_id: str,
    intervention_version: str,
    lineage: CiboInterventionLineage,
    pre_intervention_evidence: tuple[CiboEvidenceRef, ...],
    prescribed_development: tuple[str, ...],
    prescribed_research: tuple[str, ...],
    post_intervention_evidence: tuple[CiboEvidenceRef, ...],
    causal_isolation_evidence: tuple[CiboEvidenceRef, ...],
    confounded: bool,
    assessed_at: datetime,
) -> Result[CiboInterventionAttribution, CiboFunctionalError]:
    """Derive a governed, fail-closed intervention attribution."""
    try:
        state = _derive_attribution(
            post_intervention_evidence=post_intervention_evidence,
            causal_isolation_evidence=causal_isolation_evidence,
            confounded=confounded,
        )
        return Success(
            CiboInterventionAttribution(
                intervention_id=intervention_id,
                intervention_version=intervention_version,
                lineage=lineage,
                pre_intervention_evidence=pre_intervention_evidence,
                prescribed_development=prescribed_development,
                prescribed_research=prescribed_research,
                post_intervention_evidence=post_intervention_evidence,
                causal_isolation_evidence=causal_isolation_evidence,
                confounded=confounded,
                attribution_state=state,
                assessed_at=assessed_at,
                authority=CiboFunctionalAuthority.OPINION,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


__all__ = [
    "CiboCounterfactualKind",
    "CiboCounterfactualStatus",
    "CiboCounterfactualAssessment",
    "assess_counterfactual",
    "CiboInterventionLineage",
    "CiboAttributionState",
    "CiboInterventionAttribution",
    "attribute_intervention",
]
