from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.infrastructure.research_temporal_evaluation import ResearchTemporalEvaluationPlan
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchEvaluationFreezeError(InfrastructureError):
    """Base error for frozen temporal research-evaluation evidence."""

    __slots__ = ()


class ResearchEvaluationFreezeValidationError(ResearchEvaluationFreezeError):
    """Violation of a frozen evaluation evidence invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchEvaluationFreezeValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchEvaluationFreezeValidationError(
            f"{field_name} must be timezone-aware"
        )


def _utc_iso(value: datetime) -> str:
    _validate_timestamp(value, field_name="evaluation freeze timestamp")
    return value.astimezone(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class ResearchEvaluationFreezeEvidenceId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchEvaluationFreezeValidationError(
                "evaluation freeze evidence id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchEvaluationFreezeFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchEvaluationFreezeValidationError(
                "evaluation freeze fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_evaluation_freeze_fingerprint(
    *,
    strategy_binding: ResearchRunStrategyBinding,
    plan: ResearchTemporalEvaluationPlan,
) -> ResearchEvaluationFreezeFingerprint:
    if not isinstance(strategy_binding, ResearchRunStrategyBinding):
        raise ResearchEvaluationFreezeValidationError(
            "strategy_binding must be ResearchRunStrategyBinding"
        )
    if not isinstance(plan, ResearchTemporalEvaluationPlan):
        raise ResearchEvaluationFreezeValidationError(
            "plan must be ResearchTemporalEvaluationPlan"
        )
    canonical = {
        "run_input_fingerprint": strategy_binding.run.input_fingerprint.value,
        "strategy_binding_fingerprint": strategy_binding.binding_fingerprint.value,
        "strategy_content_digest": strategy_binding.manifest.content_digest.value,
        "temporal_plan_id": str(plan.plan_id.value),
        "temporal_plan_created_at": _utc_iso(plan.created_at),
        "folds": [
            {
                "fold_number": fold.fold_number,
                "in_sample": list(fold.in_sample.logical_values()),
                "out_of_sample": list(fold.out_of_sample.logical_values()),
            }
            for fold in plan.folds
        ],
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchEvaluationFreezeFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchEvaluationFreezeEvidence:
    """Evidence that exact strategy content preceded one temporal evaluation plan.

    All ordering below is on the research/process evidence axis:
    strategy freeze -> research run record -> temporal evaluation plan -> this record.
    None of these timestamps are compared with historical simulated market time.

    This proves configuration/plan chronology and exact content binding only. It
    does not prove analyst blindness, pre-registration before data access, absence
    of repeated experimentation, statistical significance, or production fitness.
    """

    evidence_id: ResearchEvaluationFreezeEvidenceId
    strategy_binding: ResearchRunStrategyBinding
    plan: ResearchTemporalEvaluationPlan
    established_at: datetime
    fingerprint: ResearchEvaluationFreezeFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, ResearchEvaluationFreezeEvidenceId):
            raise ResearchEvaluationFreezeValidationError(
                "evidence_id must be ResearchEvaluationFreezeEvidenceId"
            )
        if not isinstance(self.strategy_binding, ResearchRunStrategyBinding):
            raise ResearchEvaluationFreezeValidationError(
                "evaluation freeze requires ResearchRunStrategyBinding"
            )
        if not isinstance(self.plan, ResearchTemporalEvaluationPlan):
            raise ResearchEvaluationFreezeValidationError(
                "evaluation freeze requires ResearchTemporalEvaluationPlan"
            )
        run = self.strategy_binding.run
        manifest = self.strategy_binding.manifest
        if self.plan.run != run:
            raise ResearchEvaluationFreezeValidationError(
                "temporal evaluation plan must bind the strategy research run"
            )
        if manifest.frozen_at > run.created_at:
            raise ResearchEvaluationFreezeValidationError(
                "strategy freeze must not postdate research run creation"
            )
        if run.created_at > self.plan.created_at:
            raise ResearchEvaluationFreezeValidationError(
                "temporal evaluation plan must not predate research run creation"
            )
        _validate_timestamp(self.established_at, field_name="evaluation established_at")
        if self.established_at < self.plan.created_at:
            raise ResearchEvaluationFreezeValidationError(
                "evaluation freeze evidence must not predate temporal plan creation"
            )
        if not isinstance(self.fingerprint, ResearchEvaluationFreezeFingerprint):
            raise ResearchEvaluationFreezeValidationError(
                "fingerprint must be ResearchEvaluationFreezeFingerprint"
            )
        expected = compute_research_evaluation_freeze_fingerprint(
            strategy_binding=self.strategy_binding,
            plan=self.plan,
        )
        if self.fingerprint != expected:
            raise ResearchEvaluationFreezeValidationError(
                "evaluation freeze fingerprint must match strategy and temporal plan"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.strategy_binding.logical_values(),
            self.plan.logical_values(),
            self.established_at.isoformat(),
            self.fingerprint.logical_values(),
        )


def build_research_evaluation_freeze_evidence(
    *,
    evidence_id: ResearchEvaluationFreezeEvidenceId,
    strategy_binding: ResearchRunStrategyBinding,
    plan: ResearchTemporalEvaluationPlan,
    established_at: datetime,
) -> Result[ResearchEvaluationFreezeEvidence, ResearchEvaluationFreezeError]:
    """Compose strategy freeze and temporal partition evidence without evaluation."""

    try:
        fingerprint = compute_research_evaluation_freeze_fingerprint(
            strategy_binding=strategy_binding,
            plan=plan,
        )
        return Success(
            ResearchEvaluationFreezeEvidence(
                evidence_id=evidence_id,
                strategy_binding=strategy_binding,
                plan=plan,
                established_at=established_at,
                fingerprint=fingerprint,
            )
        )
    except ResearchEvaluationFreezeError as error:
        return Failure(error)
