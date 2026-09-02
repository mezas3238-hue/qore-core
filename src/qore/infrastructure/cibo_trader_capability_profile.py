from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.kernel.errors import InfrastructureError
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

_OPAQUE_REF_RE = r"[a-z][a-z0-9._:/-]*"
_CODE_RE = r"[a-z][a-z0-9._-]*"
_MARKET_RE = r"[A-Z0-9][A-Z0-9._/-]*"
_SHA256_HEX_RE = r"[0-9a-f]{64}"


class CiboCapabilityProfileError(InfrastructureError):
    """Base error for immutable CIBO Trader Capability Profile contracts."""

    __slots__ = ()


class CiboCapabilityProfileValidationError(CiboCapabilityProfileError):
    """A Trader Capability Profile violates a provider-neutral CIBO invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CiboCapabilityProfileValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_opaque_ref(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_OPAQUE_REF_RE, value) is None:
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must use canonical lowercase opaque-ref syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


def _validate_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) for value in values
    ):
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must be an immutable tuple of strings"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must not contain duplicates"
        )
    return tuple(sorted(normalized))


def _canonical_decimal(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapabilityProfileValidationError(
            "economic metric value must be a finite Decimal"
        )
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class CiboEvidenceRef:
    """Opaque sanitized reference to certified evidence stored outside the profile."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_opaque_ref(self.value, field_name="CIBO evidence ref"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class CiboLabEvidenceStage(StrEnum):
    REPLAY = "replay"
    FAST_FORWARD = "fast-forward"
    OOS = "oos"
    STRESS = "stress"
    MONTE_CARLO = "monte-carlo"
    ECONOMIC = "economic"
    RISK = "risk"


@dataclass(frozen=True, slots=True)
class CiboLabEvidenceRef:
    """A certified Lab evidence reference tagged with its exact evidence stage."""

    stage: CiboLabEvidenceStage
    ref: CiboEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.stage, CiboLabEvidenceStage):
            raise CiboCapabilityProfileValidationError(
                "lab evidence ref requires CiboLabEvidenceStage"
            )
        if not isinstance(self.ref, CiboEvidenceRef):
            raise CiboCapabilityProfileValidationError(
                "lab evidence ref requires CiboEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.stage.value, self.ref.logical_values())


class CiboRegimeKind(StrEnum):
    FAVORABLE = "favorable"
    WEAK = "weak"
    DEGRADED = "degraded"


@dataclass(frozen=True, slots=True)
class CiboRegimeEvidenceRef:
    """A regime evidence reference tagged as favorable, weak, or degraded."""

    regime: CiboRegimeKind
    ref: CiboEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.regime, CiboRegimeKind):
            raise CiboCapabilityProfileValidationError(
                "regime evidence ref requires CiboRegimeKind"
            )
        if not isinstance(self.ref, CiboEvidenceRef):
            raise CiboCapabilityProfileValidationError(
                "regime evidence ref requires CiboEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.regime.value, self.ref.logical_values())


@dataclass(frozen=True, slots=True)
class CiboTradeableMarketRef:
    """Canonical instrument/market symbol a trader is qualified to operate."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(_MARKET_RE, self.value) is None:
            raise CiboCapabilityProfileValidationError(
                "qualified market must use canonical uppercase market syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboTimeframeCode:
    """Canonical qualified timeframe code."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="qualified timeframe code"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboSpecialtyCode:
    """Canonical intended-role / specialty code."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="trader specialty code"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboTraderConfigFingerprint:
    """Canonical SHA-256 fingerprint of the exact trader methodology/config."""

    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or fullmatch(_SHA256_HEX_RE, self.value) is None
        ):
            raise CiboCapabilityProfileValidationError(
                "trader config fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class CiboCertificationState(StrEnum):
    """Current promotion/certification state. It can never be DEMO_ELIGIBLE."""

    UNQUALIFIED = "unqualified"
    IN_CURRICULUM = "in-curriculum"
    EVIDENCE_COLLECTED = "evidence-collected"
    PROMOTION_RECOMMENDED = "promotion-recommended"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    DEGRADED = "degraded"


class CiboEvidenceFreshnessState(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CiboEvidenceFreshness:
    """Explicit evidence freshness/provenance; no hidden clock is ever consulted."""

    state: CiboEvidenceFreshnessState
    as_of: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.state, CiboEvidenceFreshnessState):
            raise CiboCapabilityProfileValidationError(
                "evidence freshness requires CiboEvidenceFreshnessState"
            )
        _validate_timestamp(self.as_of, field_name="evidence freshness as_of")

    def logical_values(self) -> tuple[object, ...]:
        return (self.state.value, self.as_of.isoformat())


@dataclass(frozen=True, slots=True)
class CiboEconomicMetric:
    """A quantitative economic/risk metric bound to exact certified evidence."""

    metric_code: str
    value: Decimal
    evidence_ref: CiboEvidenceRef

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metric_code",
            _validate_code(self.metric_code, field_name="economic metric code"),
        )
        _canonical_decimal(self.value)
        if not isinstance(self.evidence_ref, CiboEvidenceRef):
            raise CiboCapabilityProfileValidationError(
                "economic metric requires a backing CiboEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metric_code,
            _canonical_decimal(self.value),
            self.evidence_ref.logical_values(),
        )


class CiboOperatingAction(StrEnum):
    ABSTAIN = "abstain"
    REDUCE = "reduce"
    SUSPEND = "suspend"
    RETURN_TO_LAB = "return-to-lab"


@dataclass(frozen=True, slots=True)
class CiboOperatingCondition:
    """An abstain/reduce/suspend/return-to-Lab condition bound to evidence."""

    action: CiboOperatingAction
    reason_code: str
    evidence_ref: CiboEvidenceRef | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, CiboOperatingAction):
            raise CiboCapabilityProfileValidationError(
                "operating condition requires CiboOperatingAction"
            )
        object.__setattr__(
            self,
            "reason_code",
            _validate_code(self.reason_code, field_name="operating condition reason"),
        )
        if self.evidence_ref is not None and not isinstance(
            self.evidence_ref,
            CiboEvidenceRef,
        ):
            raise CiboCapabilityProfileValidationError(
                "operating condition evidence must be CiboEvidenceRef or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.action.value,
            self.reason_code,
            None if self.evidence_ref is None else self.evidence_ref.logical_values(),
        )


def _sorted_evidence_refs(
    values: tuple[CiboEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[CiboEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboEvidenceRef) for item in values
    ):
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must be an immutable tuple of CiboEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise CiboCapabilityProfileValidationError(
            f"{field_name} must not contain duplicates"
        )
    return tuple(sorted(values, key=lambda item: item.value))


_LAB_STAGE_ORDER = {
    stage: index for index, stage in enumerate(CiboLabEvidenceStage)
}
_REGIME_ORDER = {
    regime: index for index, regime in enumerate(CiboRegimeKind)
}
_ACTION_ORDER = {
    action: index for index, action in enumerate(CiboOperatingAction)
}


def _sorted_lab_evidence_refs(
    values: tuple[CiboLabEvidenceRef, ...],
) -> tuple[CiboLabEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboLabEvidenceRef) for item in values
    ):
        raise CiboCapabilityProfileValidationError(
            "certified lab evidence must be a tuple of CiboLabEvidenceRef"
        )
    keys = tuple((item.stage.value, item.ref.value) for item in values)
    if len(set(keys)) != len(keys):
        raise CiboCapabilityProfileValidationError(
            "certified lab evidence must not contain duplicate stage/ref pairs"
        )
    return tuple(
        sorted(
            values,
            key=lambda item: (_LAB_STAGE_ORDER[item.stage], item.ref.value),
        )
    )


def _sorted_regime_refs(
    values: tuple[CiboRegimeEvidenceRef, ...],
) -> tuple[CiboRegimeEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboRegimeEvidenceRef) for item in values
    ):
        raise CiboCapabilityProfileValidationError(
            "regime evidence must be a tuple of CiboRegimeEvidenceRef"
        )
    keys = tuple((item.regime.value, item.ref.value) for item in values)
    if len(set(keys)) != len(keys):
        raise CiboCapabilityProfileValidationError(
            "regime evidence must not contain duplicate regime/ref pairs"
        )
    return tuple(
        sorted(
            values,
            key=lambda item: (_REGIME_ORDER[item.regime], item.ref.value),
        )
    )


def _sorted_markets(
    values: tuple[CiboTradeableMarketRef, ...],
) -> tuple[CiboTradeableMarketRef, ...]:
    if not isinstance(values, tuple) or not values or any(
        not isinstance(item, CiboTradeableMarketRef) for item in values
    ):
        raise CiboCapabilityProfileValidationError(
            "qualified markets must be a non-empty tuple of CiboTradeableMarketRef"
        )
    if len(set(values)) != len(values):
        raise CiboCapabilityProfileValidationError(
            "qualified markets must not contain duplicates"
        )
    return tuple(sorted(values, key=lambda item: item.value))


def _sorted_timeframes(
    values: tuple[CiboTimeframeCode, ...],
) -> tuple[CiboTimeframeCode, ...]:
    if not isinstance(values, tuple) or not values or any(
        not isinstance(item, CiboTimeframeCode) for item in values
    ):
        raise CiboCapabilityProfileValidationError(
            "qualified timeframes must be a non-empty tuple of CiboTimeframeCode"
        )
    if len(set(values)) != len(values):
        raise CiboCapabilityProfileValidationError(
            "qualified timeframes must not contain duplicates"
        )
    return tuple(sorted(values, key=lambda item: item.value))


def _sorted_operating_conditions(
    values: tuple[CiboOperatingCondition, ...],
) -> tuple[CiboOperatingCondition, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CiboOperatingCondition) for item in values
    ):
        raise CiboCapabilityProfileValidationError(
            "operating conditions must be a tuple of CiboOperatingCondition"
        )
    keys = tuple((item.action.value, item.reason_code) for item in values)
    if len(set(keys)) != len(keys):
        raise CiboCapabilityProfileValidationError(
            "operating conditions must not contain duplicate action/reason pairs"
        )
    return tuple(
        sorted(
            values,
            key=lambda item: (_ACTION_ORDER[item.action], item.reason_code),
        )
    )


@dataclass(frozen=True, slots=True)
class CiboTraderCapabilityProfile:
    """Immutable, provider-neutral capability profile for one exact Trader version.

    The profile retains exact identity/version/config plus certified evidence
    references; it owns no Lab evidence, produces no recommendation, and can
    never manufacture DEMO_ELIGIBLE (that state does not exist on this contract).
    """

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    specialty: CiboSpecialtyCode
    qualified_markets: tuple[CiboTradeableMarketRef, ...]
    qualified_timeframes: tuple[CiboTimeframeCode, ...]
    required_inputs: tuple[CiboEvidenceRef, ...]
    formal_action_semantics: tuple[CiboEvidenceRef, ...]
    lifecycle_characteristics: tuple[CiboEvidenceRef, ...]
    certified_lab_evidence: tuple[CiboLabEvidenceRef, ...]
    regime_evidence: tuple[CiboRegimeEvidenceRef, ...]
    economic_metrics: tuple[CiboEconomicMetric, ...]
    cost_sensitivity: tuple[CiboEvidenceRef, ...]
    correlation_evidence: tuple[CiboEvidenceRef, ...]
    risk_envelope: tuple[CiboEvidenceRef, ...]
    operating_conditions: tuple[CiboOperatingCondition, ...]
    certification_state: CiboCertificationState
    freshness: CiboEvidenceFreshness
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboCapabilityProfileValidationError(
                "trader_identity must be ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboCapabilityProfileValidationError(
                "config_fingerprint must be CiboTraderConfigFingerprint"
            )
        if not isinstance(self.specialty, CiboSpecialtyCode):
            raise CiboCapabilityProfileValidationError(
                "specialty must be CiboSpecialtyCode"
            )
        object.__setattr__(self, "qualified_markets", _sorted_markets(self.qualified_markets))
        object.__setattr__(
            self,
            "qualified_timeframes",
            _sorted_timeframes(self.qualified_timeframes),
        )
        object.__setattr__(
            self,
            "required_inputs",
            _sorted_evidence_refs(self.required_inputs, field_name="required inputs"),
        )
        object.__setattr__(
            self,
            "formal_action_semantics",
            _sorted_evidence_refs(
                self.formal_action_semantics,
                field_name="formal action semantics",
            ),
        )
        object.__setattr__(
            self,
            "lifecycle_characteristics",
            _sorted_evidence_refs(
                self.lifecycle_characteristics,
                field_name="lifecycle characteristics",
            ),
        )
        object.__setattr__(
            self,
            "certified_lab_evidence",
            _sorted_lab_evidence_refs(self.certified_lab_evidence),
        )
        object.__setattr__(
            self,
            "regime_evidence",
            _sorted_regime_refs(self.regime_evidence),
        )
        if not isinstance(self.economic_metrics, tuple) or any(
            not isinstance(item, CiboEconomicMetric) for item in self.economic_metrics
        ):
            raise CiboCapabilityProfileValidationError(
                "economic metrics must be a tuple of CiboEconomicMetric"
            )
        metric_codes = tuple(item.metric_code for item in self.economic_metrics)
        if len(set(metric_codes)) != len(metric_codes):
            raise CiboCapabilityProfileValidationError(
                "economic metric codes must be unique"
            )
        certified_refs = {
            item.ref.value for item in self.certified_lab_evidence
        }
        for metric in self.economic_metrics:
            if metric.evidence_ref.value not in certified_refs:
                raise CiboCapabilityProfileValidationError(
                    "economic metric must be backed by certified lab evidence"
                )
        object.__setattr__(
            self,
            "economic_metrics",
            tuple(sorted(self.economic_metrics, key=lambda item: item.metric_code)),
        )
        object.__setattr__(
            self,
            "cost_sensitivity",
            _sorted_evidence_refs(self.cost_sensitivity, field_name="cost sensitivity"),
        )
        object.__setattr__(
            self,
            "correlation_evidence",
            _sorted_evidence_refs(
                self.correlation_evidence,
                field_name="correlation evidence",
            ),
        )
        object.__setattr__(
            self,
            "risk_envelope",
            _sorted_evidence_refs(self.risk_envelope, field_name="risk envelope"),
        )
        object.__setattr__(
            self,
            "operating_conditions",
            _sorted_operating_conditions(self.operating_conditions),
        )
        if not isinstance(self.certification_state, CiboCertificationState):
            raise CiboCapabilityProfileValidationError(
                "certification_state must be CiboCertificationState"
            )
        if not isinstance(self.freshness, CiboEvidenceFreshness):
            raise CiboCapabilityProfileValidationError(
                "freshness must be CiboEvidenceFreshness"
            )
        object.__setattr__(
            self,
            "limitations",
            _validate_codes(self.limitations, field_name="profile limitations"),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.config_fingerprint.logical_values(),
            self.specialty.logical_values(),
            tuple(item.logical_values() for item in self.qualified_markets),
            tuple(item.logical_values() for item in self.qualified_timeframes),
            tuple(item.logical_values() for item in self.required_inputs),
            tuple(item.logical_values() for item in self.formal_action_semantics),
            tuple(item.logical_values() for item in self.lifecycle_characteristics),
            tuple(item.logical_values() for item in self.certified_lab_evidence),
            tuple(item.logical_values() for item in self.regime_evidence),
            tuple(item.logical_values() for item in self.economic_metrics),
            tuple(item.logical_values() for item in self.cost_sensitivity),
            tuple(item.logical_values() for item in self.correlation_evidence),
            tuple(item.logical_values() for item in self.risk_envelope),
            tuple(item.logical_values() for item in self.operating_conditions),
            self.certification_state.value,
            self.freshness.logical_values(),
            self.limitations,
        )


def build_cibo_trader_capability_profile(
    *,
    trader_identity: ResearchDecisionEvaluatorIdentity,
    config_fingerprint: CiboTraderConfigFingerprint,
    specialty: CiboSpecialtyCode,
    qualified_markets: tuple[CiboTradeableMarketRef, ...],
    qualified_timeframes: tuple[CiboTimeframeCode, ...],
    required_inputs: tuple[CiboEvidenceRef, ...] = (),
    formal_action_semantics: tuple[CiboEvidenceRef, ...] = (),
    lifecycle_characteristics: tuple[CiboEvidenceRef, ...] = (),
    certified_lab_evidence: tuple[CiboLabEvidenceRef, ...] = (),
    regime_evidence: tuple[CiboRegimeEvidenceRef, ...] = (),
    economic_metrics: tuple[CiboEconomicMetric, ...] = (),
    cost_sensitivity: tuple[CiboEvidenceRef, ...] = (),
    correlation_evidence: tuple[CiboEvidenceRef, ...] = (),
    risk_envelope: tuple[CiboEvidenceRef, ...] = (),
    operating_conditions: tuple[CiboOperatingCondition, ...] = (),
    certification_state: CiboCertificationState,
    freshness: CiboEvidenceFreshness,
    limitations: tuple[str, ...] = (),
) -> Result[CiboTraderCapabilityProfile, CiboCapabilityProfileError]:
    """Build an exact immutable capability profile without evaluating or executing."""
    try:
        return Success(
            CiboTraderCapabilityProfile(
                trader_identity=trader_identity,
                config_fingerprint=config_fingerprint,
                specialty=specialty,
                qualified_markets=qualified_markets,
                qualified_timeframes=qualified_timeframes,
                required_inputs=required_inputs,
                formal_action_semantics=formal_action_semantics,
                lifecycle_characteristics=lifecycle_characteristics,
                certified_lab_evidence=certified_lab_evidence,
                regime_evidence=regime_evidence,
                economic_metrics=economic_metrics,
                cost_sensitivity=cost_sensitivity,
                correlation_evidence=correlation_evidence,
                risk_envelope=risk_envelope,
                operating_conditions=operating_conditions,
                certification_state=certification_state,
                freshness=freshness,
                limitations=limitations,
            )
        )
    except CiboCapabilityProfileError as error:
        return Failure(error)
