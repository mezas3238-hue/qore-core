from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCapabilityProfileError,
    CiboCertificationState,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboOperatingAction,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class CiboManagerError(InfrastructureError):
    """Base error for the deterministic CIBO Trader Manager DEMO-team contracts."""

    __slots__ = ()


class CiboManagerValidationError(CiboManagerError):
    """A management input violates a deterministic DEMO-team invariant."""

    __slots__ = ()


class CiboManagerBlockedError(CiboManagerError):
    """Fail-closed result when a management action cannot be performed safely."""

    __slots__ = ()


class CiboDemoManagementState(StrEnum):
    ELIGIBLE = "eligible"
    SELECTED = "selected"
    REDUCED = "reduced"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"


class CiboManagementAction(StrEnum):
    SELECT = "select"
    REDUCE = "reduce"
    SUSPEND = "suspend"
    BLOCK = "block"


class CiboRiskMode(StrEnum):
    TRADERS_RISK_ONLY = "traders-risk-only"
    CIBO_MANAGED_TRADERS_RISK = "cibo-managed-traders-risk"


class CiboExperimentArm(StrEnum):
    A = "a"
    B = "b"


class CiboConcentrationConclusion(StrEnum):
    DIVERSIFIED = "diversified"
    CONCENTRATED = "concentrated"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboManagerValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboManagerValidationError(f"{field_name} must be timezone-aware")


def _validate_reason_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise CiboManagerValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


def _validate_reasons(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise CiboManagerValidationError(f"{field_name} must be a non-empty tuple")
    normalized = tuple(
        _validate_reason_code(value, field_name=field_name) for value in values
    )
    if len(set(normalized)) != len(normalized):
        raise CiboManagerValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validate_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboManagerValidationError(
            f"{field_name} must be a tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboManagerValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class CiboDemoEligibilityEvidence:
    """Certified DEMO_ELIGIBLE evidence bound to one exact Trader version/arm/risk mode.

    This is the ONLY thing that makes an exact version selectable. It grants no
    execution authority and carries no provider-native order fields.
    """

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    experiment_arm: CiboExperimentArm
    risk_mode: CiboRiskMode
    evidence_ref: CiboEvidenceRef
    certified_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboManagerValidationError(
                "demo eligibility requires ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboManagerValidationError(
                "demo eligibility requires CiboTraderConfigFingerprint"
            )
        if not isinstance(self.experiment_arm, CiboExperimentArm):
            raise CiboManagerValidationError(
                "demo eligibility requires CiboExperimentArm"
            )
        if not isinstance(self.risk_mode, CiboRiskMode):
            raise CiboManagerValidationError("demo eligibility requires CiboRiskMode")
        if not isinstance(self.evidence_ref, CiboEvidenceRef):
            raise CiboManagerValidationError(
                "demo eligibility requires CiboEvidenceRef"
            )
        _validate_timestamp(self.certified_at, field_name="demo eligibility certified_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.experiment_arm.value,
            self.risk_mode.value,
            self.evidence_ref.logical_values(),
            self.certified_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CiboConcentrationRecord:
    """A concentration conclusion made ONLY from explicit certified evidence."""

    conclusion: CiboConcentrationConclusion
    evidence_refs: tuple[CiboEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conclusion, CiboConcentrationConclusion):
            raise CiboManagerValidationError(
                "concentration record requires CiboConcentrationConclusion"
            )
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs:
            raise CiboManagerValidationError(
                "concentration record requires non-empty certified evidence refs"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise CiboManagerValidationError(
                "concentration evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.conclusion.value,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class CiboManagementDecision:
    """Immutable DEMO-team management decision with no execution authority."""

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    state: CiboDemoManagementState
    reasons: tuple[str, ...]
    evidence_refs: tuple[CiboEvidenceRef, ...]
    decided_at: datetime
    experiment_arm: CiboExperimentArm | None = None
    risk_mode: CiboRiskMode | None = None
    concentration: CiboConcentrationRecord | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboManagerValidationError(
                "management decision requires ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboManagerValidationError(
                "management decision requires CiboTraderConfigFingerprint"
            )
        if not isinstance(self.state, CiboDemoManagementState):
            raise CiboManagerValidationError(
                "management decision requires CiboDemoManagementState"
            )
        object.__setattr__(
            self,
            "reasons",
            _validate_reasons(self.reasons, field_name="management reasons"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validate_evidence_refs(
                self.evidence_refs,
                field_name="management evidence refs",
            ),
        )
        _validate_timestamp(self.decided_at, field_name="management decided_at")
        if self.experiment_arm is not None and not isinstance(
            self.experiment_arm,
            CiboExperimentArm,
        ):
            raise CiboManagerValidationError(
                "management experiment_arm must be CiboExperimentArm or None"
            )
        if self.risk_mode is not None and not isinstance(self.risk_mode, CiboRiskMode):
            raise CiboManagerValidationError(
                "management risk_mode must be CiboRiskMode or None"
            )
        if self.concentration is not None and not isinstance(
            self.concentration,
            CiboConcentrationRecord,
        ):
            raise CiboManagerValidationError(
                "management concentration must be CiboConcentrationRecord or None"
            )
        if (self.experiment_arm is None) != (self.risk_mode is None):
            raise CiboManagerValidationError(
                "management decision must bind arm and risk mode together"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.state.value,
            self.reasons,
            tuple(item.logical_values() for item in self.evidence_refs),
            self.decided_at.isoformat(),
            None if self.experiment_arm is None else self.experiment_arm.value,
            None if self.risk_mode is None else self.risk_mode.value,
            None if self.concentration is None else self.concentration.logical_values(),
        )


_INELIGIBLE_STATES = frozenset(
    {
        CiboCertificationState.UNQUALIFIED,
        CiboCertificationState.IN_CURRICULUM,
        CiboCertificationState.REJECTED,
        CiboCertificationState.SUSPENDED,
        CiboCertificationState.DEGRADED,
    }
)

_INELIGIBLE_FRESHNESS = frozenset(
    {
        CiboEvidenceFreshnessState.STALE,
        CiboEvidenceFreshnessState.INSUFFICIENT,
        CiboEvidenceFreshnessState.UNKNOWN,
    }
)

# Operating actions that block or return a Trader to Lab. A profile carrying any
# of these is not a selectable DEMO management state; REDUCE/ABSTAIN constrain
# operation but do not remove selection eligibility.
_BLOCKING_OPERATING_ACTIONS = frozenset(
    {
        CiboOperatingAction.SUSPEND,
        CiboOperatingAction.RETURN_TO_LAB,
    }
)


def _revalidate_eligibility(
    eligibility: CiboDemoEligibilityEvidence,
) -> Result[None, CiboManagerError]:
    """Re-enter DEMO eligibility invariants at the decision trust boundary.

    Successful construction is not permanent validity: a frozen/slots value can be
    reflectively corrupted, so exact field types and the certified timestamp are
    re-validated before the value is bound or retained as attribution evidence.
    """
    try:
        CiboDemoEligibilityEvidence.__post_init__(eligibility)
    except CiboManagerError as error:
        return Failure(error)
    return Success(None)


def _resolve_retained_attribution(
    profile: CiboTraderCapabilityProfile,
    eligibility: CiboDemoEligibilityEvidence | None,
    *,
    decided_at: datetime,
) -> Result[tuple[CiboExperimentArm | None, CiboRiskMode | None], CiboManagerError]:
    """Resolve the arm/risk mode a non-SELECT action may retain from eligibility.

    Absence of eligibility yields no attribution; a present eligibility must be
    exact-type validated and bound to the same identity/config fingerprint, and the
    decision may not predate its certification.
    """
    if eligibility is None:
        return Success((None, None))
    binding = _bind_eligibility(profile, eligibility)
    if isinstance(binding, Failure):
        return binding
    if decided_at < eligibility.certified_at:
        return Failure(
            CiboManagerBlockedError(
                "management decision cannot predate DEMO_ELIGIBLE certification"
            )
        )
    return Success((eligibility.experiment_arm, eligibility.risk_mode))


def _bind_eligibility(
    profile: CiboTraderCapabilityProfile,
    eligibility: CiboDemoEligibilityEvidence,
) -> Result[None, CiboManagerError]:
    if eligibility.trader_identity != profile.trader_identity:
        return Failure(
            CiboManagerBlockedError(
                "demo eligibility identity/version mismatch; selection blocked"
            )
        )
    if eligibility.config_fingerprint != profile.config_fingerprint:
        return Failure(
            CiboManagerBlockedError(
                "demo eligibility config fingerprint mismatch; selection blocked"
            )
        )
    return Success(None)


@dataclass(frozen=True, slots=True)
class CiboTraderManager:
    """Deterministic, stateless DEMO-team management policy foundation.

    Generic over any Trader catalog (VT-01..VT-31 and beyond): it hard-codes no
    trader identity, no methodology family, and no provider.
    """

    def decide(
        self,
        action: CiboManagementAction,
        profile: CiboTraderCapabilityProfile,
        *,
        decided_at: datetime,
        reasons: tuple[str, ...],
        eligibility: CiboDemoEligibilityEvidence | None = None,
        evidence_refs: tuple[CiboEvidenceRef, ...] = (),
        concentration: CiboConcentrationRecord | None = None,
    ) -> Result[CiboManagementDecision, CiboManagerError]:
        """Produce an immutable management decision; it issues no order and bypasses no Risk."""
        if not isinstance(action, CiboManagementAction):
            return Failure(
                CiboManagerValidationError("management action must be CiboManagementAction")
            )
        if not isinstance(profile, CiboTraderCapabilityProfile):
            return Failure(
                CiboManagerValidationError(
                    "management decision requires CiboTraderCapabilityProfile"
                )
            )
        try:
            CiboTraderCapabilityProfile.__post_init__(profile)
        except CiboCapabilityProfileError:
            return Failure(
                CiboManagerBlockedError(
                    "retained trader profile failed revalidation; management blocked"
                )
            )
        try:
            _validate_timestamp(decided_at, field_name="decided_at")
            normalized_reasons = _validate_reasons(reasons, field_name="reasons")
            normalized_refs = _validate_evidence_refs(
                evidence_refs,
                field_name="evidence refs",
            )
        except CiboManagerError as error:
            return Failure(error)

        # Fail closed: any retained eligibility must be an exact, uncorrupted value.
        if eligibility is not None:
            if type(eligibility) is not CiboDemoEligibilityEvidence:
                return Failure(
                    CiboManagerValidationError(
                        "eligibility must be CiboDemoEligibilityEvidence"
                    )
                )
            revalidated = _revalidate_eligibility(eligibility)
            if isinstance(revalidated, Failure):
                return revalidated

        # Fail closed: concentration is only ever consumed as a CiboConcentrationRecord.
        if concentration is not None and not isinstance(
            concentration,
            CiboConcentrationRecord,
        ):
            return Failure(
                CiboManagerValidationError(
                    "concentration must be CiboConcentrationRecord"
                )
            )

        # Fail closed: a decision may not predate the profile evidence it acts on.
        if decided_at < profile.freshness.as_of:
            return Failure(
                CiboManagerValidationError(
                    "management decision cannot predate profile evidence"
                )
            )

        state: CiboDemoManagementState
        arm: CiboExperimentArm | None
        risk_mode: CiboRiskMode | None
        decision_refs: tuple[CiboEvidenceRef, ...]

        if action is CiboManagementAction.SELECT:
            if eligibility is None:
                return Failure(
                    CiboManagerBlockedError(
                        "selection requires valid DEMO_ELIGIBLE evidence"
                    )
                )
            binding = _bind_eligibility(profile, eligibility)
            if isinstance(binding, Failure):
                return binding
            if decided_at < eligibility.certified_at:
                return Failure(
                    CiboManagerBlockedError(
                        "selection cannot predate DEMO_ELIGIBLE certification"
                    )
                )
            if any(
                condition.action in _BLOCKING_OPERATING_ACTIONS
                for condition in profile.operating_conditions
            ):
                return Failure(
                    CiboManagerBlockedError(
                        "blocking operating condition prevents selection"
                    )
                )
            if profile.certification_state in _INELIGIBLE_STATES:
                return Failure(
                    CiboManagerBlockedError(
                        "suspended/blocked/ineligible trader cannot be selected"
                    )
                )
            if profile.freshness.state in _INELIGIBLE_FRESHNESS:
                return Failure(
                    CiboManagerBlockedError(
                        "stale/insufficient evidence trader cannot be selected"
                    )
                )
            if (
                eligibility.risk_mode is CiboRiskMode.CIBO_MANAGED_TRADERS_RISK
                and not profile.risk_envelope
            ):
                return Failure(
                    CiboManagerBlockedError(
                        "CIBO-managed risk requires risk envelope evidence; "
                        "Risk bypass is not permitted"
                    )
                )
            state = CiboDemoManagementState.SELECTED
            arm = eligibility.experiment_arm
            risk_mode = eligibility.risk_mode
            if concentration is None:
                decision_refs = normalized_refs
            else:
                try:
                    concentration_refs = _validate_evidence_refs(
                        concentration.evidence_refs,
                        field_name="concentration evidence refs",
                    )
                except CiboManagerError as error:
                    return Failure(error)
                decision_refs = tuple(
                    sorted(
                        {
                            *normalized_refs,
                            *concentration_refs,
                        },
                        key=lambda item: item.value,
                    )
                )
        elif action in (
            CiboManagementAction.REDUCE,
            CiboManagementAction.SUSPEND,
            CiboManagementAction.BLOCK,
        ):
            attribution = _resolve_retained_attribution(
                profile,
                eligibility,
                decided_at=decided_at,
            )
            if isinstance(attribution, Failure):
                return attribution
            arm, risk_mode = attribution.value
            if action is CiboManagementAction.REDUCE:
                state = CiboDemoManagementState.REDUCED
            elif action is CiboManagementAction.SUSPEND:
                state = CiboDemoManagementState.SUSPENDED
            else:
                state = CiboDemoManagementState.BLOCKED
            decision_refs = normalized_refs
        else:
            return Failure(
                CiboManagerValidationError("unsupported management action")
            )

        try:
            return Success(
                CiboManagementDecision(
                    trader_identity=profile.trader_identity,
                    config_fingerprint=profile.config_fingerprint,
                    state=state,
                    reasons=normalized_reasons,
                    evidence_refs=decision_refs,
                    decided_at=decided_at,
                    experiment_arm=arm,
                    risk_mode=risk_mode,
                    concentration=concentration,
                )
            )
        except CiboManagerError as error:
            return Failure(error)


def evaluate_team_concentration(
    selected: tuple[CiboTraderCapabilityProfile, ...],
    *,
    correlation_evidence: tuple[CiboEvidenceRef, ...],
) -> CiboConcentrationRecord | None:
    """Conclude market concentration only from explicit certified evidence.

    Returns None (insufficient -> no conclusion) when no correlation evidence is
    supplied, so concentration is never invented.
    """
    if not isinstance(correlation_evidence, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in correlation_evidence
    ):
        raise CiboManagerValidationError(
            "correlation evidence must be a tuple of CiboEvidenceRef"
        )
    if not isinstance(selected, tuple) or any(
        not isinstance(item, CiboTraderCapabilityProfile) for item in selected
    ):
        raise CiboManagerValidationError(
            "selected must be a tuple of CiboTraderCapabilityProfile"
        )
    if not correlation_evidence:
        return None
    if not selected:
        return None
    ordered_evidence = tuple(
        sorted(set(correlation_evidence), key=lambda item: item.value)
    )
    markets = tuple(
        {market.value for market in profile.qualified_markets} for profile in selected
    )
    common = set.intersection(*markets)
    if common:
        return CiboConcentrationRecord(
            conclusion=CiboConcentrationConclusion.CONCENTRATED,
            evidence_refs=ordered_evidence,
        )
    return CiboConcentrationRecord(
        conclusion=CiboConcentrationConclusion.DIVERSIFIED,
        evidence_refs=ordered_evidence,
    )
