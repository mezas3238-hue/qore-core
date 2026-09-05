"""CF-03/CF-04 Market-Trader Suitability + Development/Degradation loop (D3).

This module turns explicit evidence into two governed answers owned by the
Trader Director (CF-03) and Trader Development Review (CF-04) surfaces:

1. ``WHAT DOES THE CURRENT EVIDENCE-BOUND MARKET/REGIME MEAN FOR THIS EXACT
   TRADER VERSION?`` — a ``CiboSuitabilityAssessment`` that binds the exact
   trader version and reduces explicit market/regime evidence, the trader's own
   regime evidence, certification state, and evidence freshness into one
   deterministic suitability disposition.

2. An individualized ``CiboDevelopmentPlan`` with a replay/historical/stress/
   regime/calibration/error-remediation curriculum and required requalification
   evidence, plus a governed recommendation to retrain, reduce participation,
   suspend, respecialize, or return the exact version to the Trader Lab when
   degradation/drift evidence supports it.

Every output is advisory: authority is OBSERVATION/OPINION/RECOMMENDATION at most.
A recommendation here never equals Trader Lab promotion, Risk approval, or DEMO
eligibility (no such members exist on these contracts), and no silent
methodology/config mutation occurs.
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
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboOperatingAction,
    CiboRegimeKind,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
)
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


def _revalidate_profile(profile: CiboTraderCapabilityProfile) -> None:
    try:
        CiboTraderCapabilityProfile.__post_init__(profile)
    except CiboFunctionalError:
        raise
    except (AttributeError, TypeError):
        raise CiboFunctionalValidationError(
            "suitability requires a valid CiboTraderCapabilityProfile"
        ) from None


class CiboSuitabilityDisposition(StrEnum):
    """Deterministic market/regime suitability conclusion for an exact version."""

    SUITABLE = "suitable"
    CONDITIONAL = "conditional"
    UNSUITABLE = "unsuitable"
    DEGRADED = "degraded"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"
    CONTRADICTORY = "contradictory"


_BLOCKING_ACTIONS = frozenset(
    {
        CiboOperatingAction.SUSPEND,
        CiboOperatingAction.RETURN_TO_LAB,
    }
)

_INELIGIBLE_STATES = frozenset(
    {
        CiboCertificationState.SUSPENDED,
        CiboCertificationState.DEGRADED,
    }
)

_STALE_FRESHNESS = frozenset(
    {
        CiboEvidenceFreshnessState.STALE,
        CiboEvidenceFreshnessState.INSUFFICIENT,
        CiboEvidenceFreshnessState.UNKNOWN,
    }
)


def _derive_disposition(
    profile: CiboTraderCapabilityProfile,
    market_evidence: CiboFunctionalEvidence,
    current_regime: CiboRegimeKind,
) -> CiboSuitabilityDisposition:
    # The trader's own blocked/degraded state dominates first: it is a fact about
    # the exact version, independent of the market assessment.
    if any(
        condition.action in _BLOCKING_ACTIONS
        for condition in profile.operating_conditions
    ):
        return CiboSuitabilityDisposition.DEGRADED
    if profile.certification_state in _INELIGIBLE_STATES:
        return CiboSuitabilityDisposition.DEGRADED
    # Contradiction dominates; then any non-SUFFICIENT market evidence fails closed
    # (a CIBO Function is not a market certification authority, so it can never
    # manufacture SUFFICIENT and therefore never positively assert suitability).
    if market_evidence.status is CiboEvidenceStatus.CONTRADICTORY:
        return CiboSuitabilityDisposition.CONTRADICTORY
    if market_evidence.status is not CiboEvidenceStatus.SUFFICIENT:
        return CiboSuitabilityDisposition.INSUFFICIENT_EVIDENCE
    if profile.freshness.state in _STALE_FRESHNESS:
        return CiboSuitabilityDisposition.INSUFFICIENT_EVIDENCE
    # Positive regime matching is reserved for externally injected SUFFICIENT
    # market evidence; CIBO itself can never reach it.
    has_favorable = any(
        item.regime is CiboRegimeKind.FAVORABLE for item in profile.regime_evidence
    )
    has_degraded = any(
        item.regime is CiboRegimeKind.DEGRADED for item in profile.regime_evidence
    )
    if current_regime is CiboRegimeKind.FAVORABLE:
        return (
            CiboSuitabilityDisposition.SUITABLE
            if has_favorable
            else CiboSuitabilityDisposition.CONDITIONAL
        )
    if current_regime is CiboRegimeKind.DEGRADED:
        return (
            CiboSuitabilityDisposition.CONDITIONAL
            if has_degraded
            else CiboSuitabilityDisposition.UNSUITABLE
        )
    return CiboSuitabilityDisposition.CONDITIONAL


@dataclass(frozen=True, slots=True)
class CiboSuitabilityAssessment:
    """Evidence-bound market/regime suitability answer for one exact version.

    ``disposition`` is derived deterministically from the market evidence, the
    trader's own regime evidence, certification state, and evidence freshness. It
    carries explicit provenance, freshness, uncertainty, and unsupported
    dimensions, and never manufactures a positive conclusion from insufficient or
    contradictory evidence.
    """

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    current_regime: CiboRegimeKind
    market_evidence: CiboFunctionalEvidence
    disposition: CiboSuitabilityDisposition
    unsupported_dimensions: tuple[str, ...]
    uncertainty_codes: tuple[str, ...]
    assessed_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboFunctionalValidationError(
                "suitability requires ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboFunctionalValidationError(
                "suitability requires CiboTraderConfigFingerprint"
            )
        if type(self.current_regime) is not CiboRegimeKind:
            raise CiboFunctionalValidationError(
                "suitability requires exact CiboRegimeKind"
            )
        if not isinstance(self.market_evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "suitability requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(self.market_evidence)
        if type(self.disposition) is not CiboSuitabilityDisposition:
            raise CiboFunctionalValidationError(
                "suitability requires exact CiboSuitabilityDisposition"
            )
        object.__setattr__(
            self,
            "unsupported_dimensions",
            _validate_codes(
                self.unsupported_dimensions,
                field_name="unsupported dimensions",
            ),
        )
        object.__setattr__(
            self,
            "uncertainty_codes",
            _validate_codes(self.uncertainty_codes, field_name="uncertainty codes"),
        )
        _validate_timestamp(self.assessed_at, field_name="suitability assessed_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "suitability requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.OBSERVATION:
            raise CiboFunctionalValidationError(
                "suitability authority must be OBSERVATION"
            )
        # No hindsight laundering: the market evidence must not postdate the
        # assessment instant (mirrors the builder's temporal-provenance boundary).
        if self.market_evidence.as_of > self.assessed_at:
            raise CiboFunctionalValidationError(
                "suitability market evidence must not postdate the assessment"
            )
        # Constructor/deriver parity (fail-closed ceiling): a positive suitability
        # outcome is reserved for externally injected SUFFICIENT evidence, and a
        # CONTRADICTORY disposition requires contradictory evidence. Direct
        # construction must not admit a stronger semantic state than the builder
        # ``assess_market_trader_suitability`` can emit.
        if (
            self.disposition
            in (
                CiboSuitabilityDisposition.SUITABLE,
                CiboSuitabilityDisposition.CONDITIONAL,
                CiboSuitabilityDisposition.UNSUITABLE,
            )
            and self.market_evidence.status is not CiboEvidenceStatus.SUFFICIENT
        ):
            raise CiboFunctionalValidationError(
                "positive suitability disposition requires sufficient market evidence"
            )
        if (
            self.disposition is CiboSuitabilityDisposition.CONTRADICTORY
            and self.market_evidence.status is not CiboEvidenceStatus.CONTRADICTORY
        ):
            raise CiboFunctionalValidationError(
                "contradictory suitability disposition requires contradictory market evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.current_regime.value,
            self.market_evidence.logical_values(),
            self.disposition.value,
            self.unsupported_dimensions,
            self.uncertainty_codes,
            self.assessed_at.isoformat(),
            self.authority.value,
        )


def assess_market_trader_suitability(
    profile: CiboTraderCapabilityProfile,
    *,
    current_regime: CiboRegimeKind,
    market_evidence: CiboFunctionalEvidence,
    assessed_at: datetime,
    unsupported_dimensions: tuple[str, ...] = (),
    uncertainty_codes: tuple[str, ...] = (),
) -> Result[CiboSuitabilityAssessment, CiboFunctionalError]:
    """Produce a deterministic evidence-bound market/regime suitability answer."""
    if not isinstance(profile, CiboTraderCapabilityProfile):
        return Failure(
            CiboFunctionalValidationError(
                "suitability requires CiboTraderCapabilityProfile"
            )
        )
    try:
        _revalidate_profile(profile)
        if type(current_regime) is not CiboRegimeKind:
            raise CiboFunctionalValidationError(
                "suitability requires exact CiboRegimeKind"
            )
        if not isinstance(market_evidence, CiboFunctionalEvidence):
            raise CiboFunctionalValidationError(
                "suitability requires CiboFunctionalEvidence"
            )
        CiboFunctionalEvidence.__post_init__(market_evidence)
        _validate_timestamp(assessed_at, field_name="assessed_at")
        if market_evidence.as_of > assessed_at:
            raise CiboFunctionalValidationError(
                "market evidence must not postdate the assessment"
            )
        disposition = _derive_disposition(profile, market_evidence, current_regime)
        return Success(
            CiboSuitabilityAssessment(
                trader_identity=profile.trader_identity,
                config_fingerprint=profile.config_fingerprint,
                current_regime=current_regime,
                market_evidence=market_evidence,
                disposition=disposition,
                unsupported_dimensions=unsupported_dimensions,
                uncertainty_codes=uncertainty_codes,
                assessed_at=assessed_at,
                authority=CiboFunctionalAuthority.OBSERVATION,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


class CiboDevelopmentAction(StrEnum):
    """Governed development/degradation action. No promotion/eligibility member."""

    RETRAIN = "retrain"
    REDUCE_PARTICIPATION = "reduce-participation"
    SUSPEND = "suspend"
    RESPECIALIZE = "respecialize"
    RETURN_TO_LAB = "return-to-lab"


class CiboCurriculumKind(StrEnum):
    """Closed catalog of individualized development curriculum kinds."""

    REPLAY = "replay"
    HISTORICAL = "historical"
    STRESS = "stress"
    REGIME = "regime"
    CALIBRATION = "calibration"
    ERROR_REMEDIATION = "error-remediation"


@dataclass(frozen=True, slots=True)
class CiboCurriculumItem:
    """One curriculum unit with optional required requalification evidence."""

    kind: CiboCurriculumKind
    description_code: str
    evidence_refs: tuple[CiboEvidenceRef, ...]
    requalification_evidence: tuple[CiboEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not CiboCurriculumKind:
            raise CiboFunctionalValidationError(
                "curriculum item requires exact CiboCurriculumKind"
            )
        object.__setattr__(
            self,
            "description_code",
            _validate_code(self.description_code, field_name="curriculum description"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(self.evidence_refs, field_name="curriculum evidence"),
        )
        object.__setattr__(
            self,
            "requalification_evidence",
            _validate_evidence_refs(
                self.requalification_evidence,
                field_name="curriculum requalification evidence",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            self.description_code,
            tuple(item.logical_values() for item in self.evidence_refs),
            tuple(item.logical_values() for item in self.requalification_evidence),
        )


def _normalize_curricula(
    values: tuple[CiboCurriculumItem, ...],
) -> tuple[CiboCurriculumItem, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboCurriculumItem) for item in values
    ):
        raise CiboFunctionalValidationError(
            "curricula must be a tuple of CiboCurriculumItem"
        )
    revalidated = tuple(
        CiboCurriculumItem(
            kind=item.kind,
            description_code=item.description_code,
            evidence_refs=item.evidence_refs,
            requalification_evidence=item.requalification_evidence,
        )
        for item in values
    )
    keys = tuple((item.kind.value, item.description_code) for item in revalidated)
    if len(set(keys)) != len(keys):
        raise CiboFunctionalValidationError(
            "curriculum items must be unique by (kind, description)"
        )
    return tuple(sorted(revalidated, key=lambda item: (item.kind.value, item.description_code)))


_ACTION_REQUIRING_DEGRADATION = frozenset(
    {
        CiboDevelopmentAction.REDUCE_PARTICIPATION,
        CiboDevelopmentAction.SUSPEND,
        CiboDevelopmentAction.RESPECIALIZE,
        CiboDevelopmentAction.RETURN_TO_LAB,
    }
)


@dataclass(frozen=True, slots=True)
class CiboDevelopmentPlan:
    """Individualized development/degradation plan for one exact version.

    Advisory only (RECOMMENDATION authority): it never promotes, never approves
    Risk, never grants DEMO eligibility, and never mutates methodology/config.
    """

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    action: CiboDevelopmentAction
    curricula: tuple[CiboCurriculumItem, ...]
    degradation_evidence: CiboFunctionalEvidence | None
    requalification_evidence: tuple[CiboEvidenceRef, ...]
    reasons: tuple[str, ...]
    planned_at: datetime
    authority: CiboFunctionalAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboFunctionalValidationError(
                "development plan requires ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboFunctionalValidationError(
                "development plan requires CiboTraderConfigFingerprint"
            )
        if type(self.action) is not CiboDevelopmentAction:
            raise CiboFunctionalValidationError(
                "development plan requires exact CiboDevelopmentAction"
            )
        object.__setattr__(self, "curricula", _normalize_curricula(self.curricula))
        if not self.curricula:
            raise CiboFunctionalValidationError(
                "development plan requires at least one curriculum item"
            )
        if self.degradation_evidence is not None:
            if not isinstance(self.degradation_evidence, CiboFunctionalEvidence):
                raise CiboFunctionalValidationError(
                    "degradation evidence must be CiboFunctionalEvidence or None"
                )
            CiboFunctionalEvidence.__post_init__(self.degradation_evidence)
        object.__setattr__(
            self,
            "requalification_evidence",
            _validate_evidence_refs(
                self.requalification_evidence,
                field_name="requalification evidence",
            ),
        )
        object.__setattr__(
            self,
            "reasons",
            _validate_codes(self.reasons, field_name="development plan reasons"),
        )
        if not self.reasons:
            raise CiboFunctionalValidationError(
                "development plan requires at least one reason"
            )
        _validate_timestamp(self.planned_at, field_name="development plan planned_at")
        if type(self.authority) is not CiboFunctionalAuthority:
            raise CiboFunctionalValidationError(
                "development plan requires exact CiboFunctionalAuthority"
            )
        if self.authority is not CiboFunctionalAuthority.RECOMMENDATION:
            raise CiboFunctionalValidationError(
                "development plan authority must be RECOMMENDATION"
            )
        if self.action in _ACTION_REQUIRING_DEGRADATION:
            if self.degradation_evidence is None:
                raise CiboFunctionalValidationError(
                    "this development action requires degradation evidence"
                )
        if self.action in (
            CiboDevelopmentAction.RETRAIN,
            CiboDevelopmentAction.RESPECIALIZE,
            CiboDevelopmentAction.RETURN_TO_LAB,
        ):
            if not self.requalification_evidence:
                raise CiboFunctionalValidationError(
                    "this development action requires requalification evidence"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.action.value,
            tuple(item.logical_values() for item in self.curricula),
            None
            if self.degradation_evidence is None
            else self.degradation_evidence.logical_values(),
            tuple(item.logical_values() for item in self.requalification_evidence),
            self.reasons,
            self.planned_at.isoformat(),
            self.authority.value,
        )


def plan_trader_development(
    profile: CiboTraderCapabilityProfile,
    *,
    action: CiboDevelopmentAction,
    curricula: tuple[CiboCurriculumItem, ...],
    degradation_evidence: CiboFunctionalEvidence | None,
    requalification_evidence: tuple[CiboEvidenceRef, ...],
    reasons: tuple[str, ...],
    planned_at: datetime,
) -> Result[CiboDevelopmentPlan, CiboFunctionalError]:
    """Produce an individualized, advisory development/degradation plan."""
    if not isinstance(profile, CiboTraderCapabilityProfile):
        return Failure(
            CiboFunctionalValidationError(
                "development plan requires CiboTraderCapabilityProfile"
            )
        )
    try:
        _revalidate_profile(profile)
        if type(action) is not CiboDevelopmentAction:
            raise CiboFunctionalValidationError(
                "development plan requires exact CiboDevelopmentAction"
            )
        _validate_timestamp(planned_at, field_name="planned_at")
        if planned_at < profile.freshness.as_of:
            raise CiboFunctionalValidationError(
                "development plan cannot predate profile evidence"
            )
        return Success(
            CiboDevelopmentPlan(
                trader_identity=profile.trader_identity,
                config_fingerprint=profile.config_fingerprint,
                action=action,
                curricula=curricula,
                degradation_evidence=degradation_evidence,
                requalification_evidence=requalification_evidence,
                reasons=reasons,
                planned_at=planned_at,
                authority=CiboFunctionalAuthority.RECOMMENDATION,
            )
        )
    except CiboFunctionalError as error:
        return Failure(error)


__all__ = [
    "CiboSuitabilityDisposition",
    "CiboSuitabilityAssessment",
    "assess_market_trader_suitability",
    "CiboDevelopmentAction",
    "CiboCurriculumKind",
    "CiboCurriculumItem",
    "CiboDevelopmentPlan",
    "plan_trader_development",
]
