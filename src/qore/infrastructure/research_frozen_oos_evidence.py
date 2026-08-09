from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidence,
)
from qore.infrastructure.research_oos_performance import (
    ResearchOosPerformanceEvidence,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchFrozenOosEvidenceError(InfrastructureError):
    """Base error for frozen-strategy OOS evidence composition."""

    __slots__ = ()


class ResearchFrozenOosEvidenceValidationError(ResearchFrozenOosEvidenceError):
    """Violation of a frozen OOS evidence invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchFrozenOosEvidenceValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchFrozenOosEvidenceValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class ResearchFrozenOosEvidenceId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS evidence id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchFrozenOosFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_frozen_oos_fingerprint(
    *,
    evaluation_freeze: ResearchEvaluationFreezeEvidence,
    oos_performance: ResearchOosPerformanceEvidence,
) -> ResearchFrozenOosFingerprint:
    """Hash the complete logical frozen-plan and OOS-performance evidence chain."""

    if not isinstance(evaluation_freeze, ResearchEvaluationFreezeEvidence):
        raise ResearchFrozenOosEvidenceValidationError(
            "evaluation_freeze must be ResearchEvaluationFreezeEvidence"
        )
    if not isinstance(oos_performance, ResearchOosPerformanceEvidence):
        raise ResearchFrozenOosEvidenceValidationError(
            "oos_performance must be ResearchOosPerformanceEvidence"
        )
    canonical = {
        "evaluation_freeze": evaluation_freeze.logical_values(),
        "oos_performance": oos_performance.logical_values(),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchFrozenOosFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchFrozenOosEvidence:
    """Exact frozen-strategy OOS performance evidence composition.

    This contract proves that the exact strategy configuration was frozen into
    the exact temporal evaluation plan before the attached OOS performance
    evidence was recorded, and that both evidence chains refer to the same plan.

    It does not prove analyst blindness, absence of prior OOS inspection,
    pre-registration with an independent authority, statistical significance,
    robustness to repeated model selection, or production readiness.
    """

    evidence_id: ResearchFrozenOosEvidenceId
    evaluation_freeze: ResearchEvaluationFreezeEvidence
    oos_performance: ResearchOosPerformanceEvidence
    certified_at: datetime
    fingerprint: ResearchFrozenOosFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, ResearchFrozenOosEvidenceId):
            raise ResearchFrozenOosEvidenceValidationError(
                "evidence_id must be ResearchFrozenOosEvidenceId"
            )
        if not isinstance(self.evaluation_freeze, ResearchEvaluationFreezeEvidence):
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS evidence requires ResearchEvaluationFreezeEvidence"
            )
        if not isinstance(self.oos_performance, ResearchOosPerformanceEvidence):
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS evidence requires ResearchOosPerformanceEvidence"
            )
        if self.oos_performance.plan != self.evaluation_freeze.plan:
            raise ResearchFrozenOosEvidenceValidationError(
                "OOS performance must use the exact frozen temporal evaluation plan"
            )
        if self.oos_performance.plan.run != self.evaluation_freeze.strategy_binding.run:
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS evidence must remain within one research run"
            )
        if self.oos_performance.observed_at < self.evaluation_freeze.established_at:
            raise ResearchFrozenOosEvidenceValidationError(
                "OOS performance evidence must not predate evaluation freeze establishment"
            )
        _validate_timestamp(self.certified_at, field_name="frozen OOS certified_at")
        if self.certified_at < self.oos_performance.observed_at:
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS certification cannot predate OOS performance evidence"
            )
        if not isinstance(self.fingerprint, ResearchFrozenOosFingerprint):
            raise ResearchFrozenOosEvidenceValidationError(
                "fingerprint must be ResearchFrozenOosFingerprint"
            )
        expected = compute_research_frozen_oos_fingerprint(
            evaluation_freeze=self.evaluation_freeze,
            oos_performance=self.oos_performance,
        )
        if self.fingerprint != expected:
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS fingerprint must match exact composed evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.evidence_id.logical_values(),
            self.evaluation_freeze.logical_values(),
            self.oos_performance.logical_values(),
            self.certified_at.isoformat(),
            self.fingerprint.logical_values(),
        )


def build_research_frozen_oos_evidence(
    *,
    evidence_id: ResearchFrozenOosEvidenceId,
    evaluation_freeze: ResearchEvaluationFreezeEvidence,
    oos_performance: ResearchOosPerformanceEvidence,
    certified_at: datetime,
) -> Result[ResearchFrozenOosEvidence, ResearchFrozenOosEvidenceError]:
    """Compose frozen-plan and OOS performance evidence without overclaiming validity."""

    try:
        fingerprint = compute_research_frozen_oos_fingerprint(
            evaluation_freeze=evaluation_freeze,
            oos_performance=oos_performance,
        )
        return Success(
            ResearchFrozenOosEvidence(
                evidence_id=evidence_id,
                evaluation_freeze=evaluation_freeze,
                oos_performance=oos_performance,
                certified_at=certified_at,
                fingerprint=fingerprint,
            )
        )
    except ResearchFrozenOosEvidenceError as error:
        return Failure(error)
