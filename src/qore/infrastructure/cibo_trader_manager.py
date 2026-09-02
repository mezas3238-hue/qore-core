"""CIBO Trader Manager MVP (DEMO/research scope).

Deterministic, fail-closed participation manager over concrete trader
evidence. It selects / reduces / suspends / blocks / recommends bounded
participation and NEVER executes orders or grants Risk authorization.

The manager consumes exact trader version bindings plus immutable, typed,
freshness-aware, sample-count-aware performance and risk evidence, applies
ordered fail-closed stages, ranks deterministically, and returns an immutable
result with full provenance.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_lineage_canonical import _cjson, _sha256
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import ResearchSoftwareRevision

_MANAGER_SCHEMA_VERSION = "v1"
_MANAGER_SOFTWARE_REVISION = "qore.cibo.trader-manager.v1"
_CONFIG_FINGERPRINT_RE = r"[0-9a-f]{64}"
_PUBLIC_CODE_RE = r"[a-z][a-z0-9._-]*"

_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password=",
    "secret=",
    "token=",
)


def _validate_public_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_PUBLIC_CODE_RE, value) is None:
        raise ResearchLineageValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise ResearchLineageValidationError(
            f"{field_name} must not contain sensitive material"
        )
    return value


def _validate_fingerprint(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CONFIG_FINGERPRINT_RE, value) is None:
        raise ResearchLineageValidationError(
            f"{field_name} must be 64 lowercase hex characters"
        )
    return value


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchLineageValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchLineageValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ResearchLineageValidationError(f"{field_name} must be UUID")


def _validate_non_negative_int(
    value: int,
    *,
    field_name: str,
    minimum: int = 0,
) -> int:
    if isinstance(value, bool) or type(value) is not int or value < minimum:
        raise ResearchLineageValidationError(
            f"{field_name} must be an int >= {minimum}; bool rejected"
        )
    return value


def _canonical_decimal(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchLineageValidationError("Decimal value must be finite")
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


class CiboManagerMode(StrEnum):
    """Closed A/B benchmark modes; identity must never be relabeled."""

    TRADERS_RISK_ONLY = "TRADERS_RISK_ONLY"
    CIBO_MANAGED_TRADERS_RISK = "CIBO_MANAGED_TRADERS_RISK"


class CiboTraderParticipation(StrEnum):
    """Closed per-trader participation decision."""

    ELIGIBLE = "eligible"
    SELECTED = "selected"
    REDUCED = "reduced"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"


class CiboRiskClassification(StrEnum):
    """Closed risk evidence classification."""

    CLEAR = "clear"
    FLAGGED = "flagged"
    VIOLATION = "violation"


@dataclass(frozen=True, slots=True)
class CiboTraderId:
    value: str

    def __post_init__(self) -> None:
        _validate_public_code(self.value, field_name="trader id")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CiboTraderVersionBinding:
    """Exact immutable trader identity/version/configuration binding."""

    trader_id: CiboTraderId
    evaluator_family: ResearchDecisionEvaluatorFamily
    schema_version: ResearchDecisionEvaluatorSchemaVersion
    software_revision: ResearchSoftwareRevision
    config_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.trader_id, CiboTraderId):
            raise ResearchLineageValidationError("trader_id must be CiboTraderId")
        if not isinstance(
            self.evaluator_family,
            ResearchDecisionEvaluatorFamily,
        ):
            raise ResearchLineageValidationError(
                "evaluator_family must be ResearchDecisionEvaluatorFamily"
            )
        if not isinstance(
            self.schema_version,
            ResearchDecisionEvaluatorSchemaVersion,
        ):
            raise ResearchLineageValidationError(
                "schema_version must be ResearchDecisionEvaluatorSchemaVersion"
            )
        if not isinstance(self.software_revision, ResearchSoftwareRevision):
            raise ResearchLineageValidationError(
                "software_revision must be ResearchSoftwareRevision"
            )
        _validate_fingerprint(
            self.config_fingerprint,
            field_name="config_fingerprint",
        )

    def logical_values(self) -> Mapping[str, str]:
        return {
            "trader_id": self.trader_id.value,
            "evaluator_family": self.evaluator_family.value,
            "schema_version": self.schema_version.value,
            "software_revision": self.software_revision.value,
            "config_fingerprint": self.config_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class CiboPerformanceEvidence:
    """Immutable typed performance evidence with exact reference."""

    metric_code: str
    metric_value: Decimal
    sample_count: int
    as_of: datetime
    evidence_ref: UUID

    def __post_init__(self) -> None:
        _validate_public_code(self.metric_code, field_name="metric code")
        if not isinstance(self.metric_value, Decimal) or not self.metric_value.is_finite():
            raise ResearchLineageValidationError(
                "metric_value must be a finite Decimal"
            )
        _validate_non_negative_int(self.sample_count, field_name="sample_count")
        _validate_aware_datetime(self.as_of, field_name="performance as_of")
        _validate_uuid(self.evidence_ref, field_name="performance evidence_ref")


@dataclass(frozen=True, slots=True)
class CiboRiskEvidence:
    """Immutable typed risk evidence with closed classification."""

    classification: CiboRiskClassification
    violation_count: int
    as_of: datetime
    evidence_ref: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.classification, CiboRiskClassification):
            raise ResearchLineageValidationError(
                "classification must be CiboRiskClassification"
            )
        _validate_non_negative_int(self.violation_count, field_name="violation_count")
        _validate_aware_datetime(self.as_of, field_name="risk as_of")
        _validate_uuid(self.evidence_ref, field_name="risk evidence_ref")


@dataclass(frozen=True, slots=True)
class CiboTraderCandidate:
    """One trader's exact bound evidence for a manager evaluation."""

    version_binding: CiboTraderVersionBinding
    performance: CiboPerformanceEvidence
    risk: CiboRiskEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.version_binding, CiboTraderVersionBinding):
            raise ResearchLineageValidationError(
                "version_binding must be CiboTraderVersionBinding"
            )
        if not isinstance(self.performance, CiboPerformanceEvidence):
            raise ResearchLineageValidationError(
                "performance must be CiboPerformanceEvidence"
            )
        if not isinstance(self.risk, CiboRiskEvidence):
            raise ResearchLineageValidationError("risk must be CiboRiskEvidence")


@dataclass(frozen=True, slots=True)
class CiboManagerPolicy:
    """Exact immutable manager policy with deterministic invariants."""

    mode: CiboManagerMode
    selection_count: int
    ranking_metric_code: str
    freshness_bound: timedelta
    minimum_samples: int
    violation_floor: int
    selection_threshold: Decimal
    reduced_weight: Decimal
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CiboManagerMode):
            raise ResearchLineageValidationError("mode must be CiboManagerMode")
        _validate_non_negative_int(
            self.selection_count,
            field_name="selection_count",
            minimum=1,
        )
        _validate_public_code(self.ranking_metric_code, field_name="ranking metric code")
        if not isinstance(self.freshness_bound, timedelta):
            raise ResearchLineageValidationError(
                "freshness_bound must be timedelta"
            )
        if self.freshness_bound <= timedelta(0):
            raise ResearchLineageValidationError(
                "freshness_bound must be positive"
            )
        _validate_non_negative_int(
            self.minimum_samples,
            field_name="minimum_samples",
            minimum=1,
        )
        _validate_non_negative_int(
            self.violation_floor,
            field_name="violation_floor",
            minimum=1,
        )
        if not isinstance(self.selection_threshold, Decimal) or not (
            self.selection_threshold.is_finite()
        ):
            raise ResearchLineageValidationError(
                "selection_threshold must be a finite Decimal"
            )
        if (
            not isinstance(self.reduced_weight, Decimal)
            or not self.reduced_weight.is_finite()
            or not Decimal(0) < self.reduced_weight < Decimal(1)
        ):
            raise ResearchLineageValidationError(
                "reduced_weight must be a finite Decimal in (0, 1)"
            )
        object.__setattr__(
            self,
            "fingerprint",
            _sha256(
                _cjson(
                    {
                        "schema": "qore.cibo.trader-manager-policy.v1",
                        "mode": self.mode.value,
                        "selection_count": self.selection_count,
                        "ranking_metric_code": self.ranking_metric_code,
                        "freshness_bound_seconds": str(
                            int(self.freshness_bound.total_seconds())
                        ),
                        "minimum_samples": self.minimum_samples,
                        "violation_floor": self.violation_floor,
                        "selection_threshold": _canonical_decimal(
                            self.selection_threshold
                        ),
                        "reduced_weight": _canonical_decimal(self.reduced_weight),
                    }
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class CiboTraderRecommendation:
    """Deterministic per-trader participation recommendation."""

    trader_id: CiboTraderId
    participation: CiboTraderParticipation
    weight: Decimal
    reason: str
    evidence_refs: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.trader_id, CiboTraderId):
            raise ResearchLineageValidationError("trader_id must be CiboTraderId")
        if not isinstance(self.participation, CiboTraderParticipation):
            raise ResearchLineageValidationError(
                "participation must be CiboTraderParticipation"
            )
        if not isinstance(self.weight, Decimal) or not self.weight.is_finite():
            raise ResearchLineageValidationError("weight must be a finite Decimal")
        if not 0 <= self.weight <= 1:
            raise ResearchLineageValidationError("weight must be within [0, 1]")
        _validate_public_code(self.reason, field_name="recommendation reason")
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(item, UUID) for item in self.evidence_refs
        ):
            raise ResearchLineageValidationError(
                "evidence_refs must be an immutable UUID tuple"
            )


@dataclass(frozen=True, slots=True)
class CiboManagerProvenance:
    """Immutable provenance of one manager evaluation."""

    mode: CiboManagerMode
    policy_fingerprint: str
    manager_schema_version: str
    manager_software_revision: str
    evaluated_at: datetime
    candidate_count: int
    selected_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CiboManagerMode):
            raise ResearchLineageValidationError("mode must be CiboManagerMode")
        _validate_fingerprint(self.policy_fingerprint, field_name="policy_fingerprint")
        if not isinstance(self.manager_schema_version, str):
            raise ResearchLineageValidationError(
                "manager_schema_version must be str"
            )
        _validate_public_code(
            self.manager_software_revision,
            field_name="manager_software_revision",
        )
        _validate_aware_datetime(self.evaluated_at, field_name="evaluated_at")
        _validate_non_negative_int(self.candidate_count, field_name="candidate_count")
        _validate_non_negative_int(self.selected_count, field_name="selected_count")


@dataclass(frozen=True, slots=True)
class CiboManagerResult:
    """Immutable manager result: recommendations plus provenance."""

    recommendations: tuple[CiboTraderRecommendation, ...]
    provenance: CiboManagerProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.recommendations, tuple) or any(
            not isinstance(item, CiboTraderRecommendation)
            for item in self.recommendations
        ):
            raise ResearchLineageValidationError(
                "recommendations must be an immutable CiboTraderRecommendation tuple"
            )
        if not isinstance(self.provenance, CiboManagerProvenance):
            raise ResearchLineageValidationError(
                "provenance must be CiboManagerProvenance"
            )
        trader_ids = tuple(item.trader_id.value for item in self.recommendations)
        if len(set(trader_ids)) != len(trader_ids):
            raise ResearchLineageValidationError(
                "manager recommendations must reference each trader exactly once"
            )


def _ranking_key(
    metric_value: Decimal,
    binding: CiboTraderVersionBinding,
) -> tuple[Decimal, str, str, str, str]:
    return (
        -metric_value,
        binding.evaluator_family.value,
        binding.schema_version.value,
        binding.software_revision.value,
        binding.trader_id.value,
    )


class CiboTraderManager:
    """Pure deterministic CIBO trader participation manager."""

    def evaluate(
        self,
        *,
        policy: CiboManagerPolicy,
        candidates: tuple[CiboTraderCandidate, ...],
        evaluated_at: datetime,
    ) -> CiboManagerResult:
        if not isinstance(policy, CiboManagerPolicy):
            raise ResearchLineageValidationError("policy must be CiboManagerPolicy")
        if not isinstance(candidates, tuple) or any(
            not isinstance(item, CiboTraderCandidate) for item in candidates
        ):
            raise ResearchLineageValidationError(
                "candidates must be an immutable CiboTraderCandidate tuple"
            )
        _validate_aware_datetime(evaluated_at, field_name="evaluated_at")

        ordered = tuple(sorted(candidates, key=_candidate_order_key))
        recommendations: list[CiboTraderRecommendation] = []
        eligible: list[tuple[CiboTraderCandidate, Decimal]] = []

        for candidate in ordered:
            binding = candidate.version_binding
            performance = candidate.performance
            risk = candidate.risk
            evidence_refs = (performance.evidence_ref, risk.evidence_ref)

            block_reason = self._block_reason(
                policy=policy,
                candidate=candidate,
                evaluated_at=evaluated_at,
            )
            if block_reason is not None:
                recommendations.append(
                    CiboTraderRecommendation(
                        trader_id=binding.trader_id,
                        participation=CiboTraderParticipation.BLOCKED,
                        weight=Decimal(0),
                        reason=block_reason,
                        evidence_refs=evidence_refs,
                    )
                )
                continue

            if risk.classification is CiboRiskClassification.FLAGGED:
                recommendations.append(
                    CiboTraderRecommendation(
                        trader_id=binding.trader_id,
                        participation=CiboTraderParticipation.SUSPENDED,
                        weight=Decimal(0),
                        reason="risk.flagged",
                        evidence_refs=evidence_refs,
                    )
                )
                continue

            if performance.metric_value < policy.selection_threshold:
                recommendations.append(
                    CiboTraderRecommendation(
                        trader_id=binding.trader_id,
                        participation=CiboTraderParticipation.REDUCED,
                        weight=policy.reduced_weight,
                        reason="metric.below-threshold",
                        evidence_refs=evidence_refs,
                    )
                )
                continue

            eligible.append((candidate, performance.metric_value))

        eligible.sort(key=lambda item: _ranking_key(item[1], item[0].version_binding))
        for index, (candidate, _metric_value) in enumerate(eligible):
            binding = candidate.version_binding
            evidence_refs = (
                candidate.performance.evidence_ref,
                candidate.risk.evidence_ref,
            )
            if index < policy.selection_count:
                recommendations.append(
                    CiboTraderRecommendation(
                        trader_id=binding.trader_id,
                        participation=CiboTraderParticipation.SELECTED,
                        weight=Decimal(1),
                        reason="selected",
                        evidence_refs=evidence_refs,
                    )
                )
            else:
                recommendations.append(
                    CiboTraderRecommendation(
                        trader_id=binding.trader_id,
                        participation=CiboTraderParticipation.ELIGIBLE,
                        weight=policy.reduced_weight,
                        reason="eligible.not-selected",
                        evidence_refs=evidence_refs,
                    )
                )

        recommendations.sort(key=lambda item: _recommendation_order_key(item))
        selected_count = sum(
            1
            for item in recommendations
            if item.participation is CiboTraderParticipation.SELECTED
        )
        provenance = CiboManagerProvenance(
            mode=policy.mode,
            policy_fingerprint=policy.fingerprint,
            manager_schema_version=_MANAGER_SCHEMA_VERSION,
            manager_software_revision=_MANAGER_SOFTWARE_REVISION,
            evaluated_at=evaluated_at,
            candidate_count=len(candidates),
            selected_count=selected_count,
        )
        return CiboManagerResult(
            recommendations=tuple(recommendations),
            provenance=provenance,
        )

    @staticmethod
    def _block_reason(
        *,
        policy: CiboManagerPolicy,
        candidate: CiboTraderCandidate,
        evaluated_at: datetime,
    ) -> str | None:
        performance = candidate.performance
        risk = candidate.risk

        if risk.classification is CiboRiskClassification.VIOLATION:
            return "risk.violation"
        if risk.violation_count >= policy.violation_floor:
            return "risk.violation-floor"
        if performance.as_of > evaluated_at or risk.as_of > evaluated_at:
            return "evidence.contradictory"
        freshness_cutoff = evaluated_at - policy.freshness_bound
        if performance.as_of < freshness_cutoff:
            return "performance.stale"
        if risk.as_of < freshness_cutoff:
            return "risk.stale"
        if performance.sample_count < policy.minimum_samples:
            return "performance.insufficient-samples"
        if performance.metric_code != policy.ranking_metric_code:
            return "metric.code-mismatch"
        return None


def _candidate_order_key(
    candidate: CiboTraderCandidate,
) -> tuple[str, str, str, str, str]:
    binding = candidate.version_binding
    return (
        binding.evaluator_family.value,
        binding.schema_version.value,
        binding.software_revision.value,
        binding.trader_id.value,
        binding.config_fingerprint,
    )


def _recommendation_order_key(
    recommendation: CiboTraderRecommendation,
) -> tuple[str, str]:
    return (recommendation.trader_id.value, recommendation.reason)
