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


_FINGERPRINT_IDENTITY_CACHE: dict[
    tuple[int, int],
    tuple[
        ResearchEvaluationFreezeEvidence,
        ResearchOosPerformanceEvidence,
        ResearchFrozenOosFingerprint,
    ],
] = {}
_FINGERPRINT_CACHE_LIMIT = 16


def _cached_identity_fingerprint(
    evaluation_freeze: ResearchEvaluationFreezeEvidence,
    oos_performance: ResearchOosPerformanceEvidence,
) -> ResearchFrozenOosFingerprint | None:
    cached = _FINGERPRINT_IDENTITY_CACHE.get(
        (id(evaluation_freeze), id(oos_performance))
    )
    if (
        cached is not None
        and cached[0] is evaluation_freeze
        and cached[1] is oos_performance
    ):
        return cached[2]
    return None


def _remember_identity_fingerprint(
    evaluation_freeze: ResearchEvaluationFreezeEvidence,
    oos_performance: ResearchOosPerformanceEvidence,
    fingerprint: ResearchFrozenOosFingerprint,
) -> ResearchFrozenOosFingerprint:
    if len(_FINGERPRINT_IDENTITY_CACHE) >= _FINGERPRINT_CACHE_LIMIT:
        _FINGERPRINT_IDENTITY_CACHE.clear()
    _FINGERPRINT_IDENTITY_CACHE[
        (id(evaluation_freeze), id(oos_performance))
    ] = (evaluation_freeze, oos_performance, fingerprint)
    return fingerprint


def _canonical_json_value(value: object) -> object:
    """Project logical evidence values into strict deterministic JSON values."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, tuple):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ResearchFrozenOosEvidenceValidationError(
                "frozen OOS canonical JSON mapping keys must be strings"
            )
        return {
            key: _canonical_json_value(value[key])
            for key in sorted(value)
        }
    raise ResearchFrozenOosEvidenceValidationError(
        "frozen OOS logical evidence contains unsupported canonical JSON type: "
        f"{type(value).__name__}"
    )


def _component_bytes(label: str, value: object) -> bytes:
    """Encode one canonical fingerprint component with unambiguous framing."""

    label_bytes = label.encode("utf-8")
    encoded = json.dumps(
        _canonical_json_value(value),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return (
        len(label_bytes).to_bytes(4, "big")
        + label_bytes
        + len(encoded).to_bytes(8, "big")
        + encoded
    )


def _stream_valid_oos_fingerprint(
    *,
    evaluation_freeze: ResearchEvaluationFreezeEvidence,
    oos_performance: ResearchOosPerformanceEvidence,
) -> ResearchFrozenOosFingerprint:
    """Hash valid OOS evidence incrementally to keep peak memory bounded."""

    digest = sha256()
    digest.update(
        _component_bytes(
            "schema",
            "qore.research-frozen-oos.streaming-fingerprint.v2",
        )
    )
    digest.update(
        _component_bytes(
            "evaluation_freeze",
            evaluation_freeze.logical_values(),
        )
    )
    digest.update(
        _component_bytes(
            "oos.evidence_id",
            oos_performance.evidence_id.logical_values(),
        )
    )
    digest.update(
        _component_bytes(
            "oos.plan",
            oos_performance.plan.logical_values(),
        )
    )
    digest.update(_component_bytes("oos.basis", oos_performance.basis.value))
    digest.update(
        _component_bytes(
            "oos.fold_count",
            len(oos_performance.fold_performance),
        )
    )

    for fold_index, fold_performance in enumerate(
        oos_performance.fold_performance
    ):
        statistics = fold_performance.statistics
        prefix = f"oos.fold.{fold_index}"
        digest.update(
            _component_bytes(
                f"{prefix}.fold",
                fold_performance.fold.logical_values(),
            )
        )
        digest.update(
            _component_bytes(
                f"{prefix}.statistics_header",
                (
                    statistics.snapshot_id.logical_values(),
                    statistics.run.logical_values(),
                    statistics.basis.value,
                    statistics.sample_size,
                    statistics.positive_count,
                    statistics.negative_count,
                    statistics.flat_count,
                    format(statistics.mean_return, "f"),
                    format(statistics.minimum_return, "f"),
                    format(statistics.maximum_return, "f"),
                    format(statistics.win_rate, "f"),
                    format(statistics.population_variance, "f"),
                    statistics.observed_at.isoformat(),
                ),
            )
        )
        digest.update(
            _component_bytes(
                f"{prefix}.observation_count",
                len(statistics.observations),
            )
        )
        for observation_index, observation in enumerate(
            statistics.observations
        ):
            digest.update(
                _component_bytes(
                    f"{prefix}.observation.{observation_index}",
                    observation.logical_values(),
                )
            )

    digest.update(
        _component_bytes(
            "oos.observed_at",
            oos_performance.observed_at.isoformat(),
        )
    )
    return ResearchFrozenOosFingerprint(digest.hexdigest())


def compute_research_frozen_oos_fingerprint(
    *,
    evaluation_freeze: ResearchEvaluationFreezeEvidence,
    oos_performance: ResearchOosPerformanceEvidence,
) -> ResearchFrozenOosFingerprint:
    """Hash the exact frozen-plan/OOS chain with bounded peak memory.

    Valid OOS evidence is streamed one retained observation at a time instead of
    materializing the complete nested logical-value tree in one JSON object.
    """

    if not isinstance(evaluation_freeze, ResearchEvaluationFreezeEvidence):
        raise ResearchFrozenOosEvidenceValidationError(
            "evaluation_freeze must be ResearchEvaluationFreezeEvidence"
        )
    if not isinstance(oos_performance, ResearchOosPerformanceEvidence):
        raise ResearchFrozenOosEvidenceValidationError(
            "oos_performance must be ResearchOosPerformanceEvidence"
        )
    cached = _cached_identity_fingerprint(evaluation_freeze, oos_performance)
    if cached is not None:
        return cached

    # Legacy unit-test fixtures intentionally bypass OOS validation and can carry
    # no fold records. Real ResearchOosPerformanceEvidence is non-empty; retain a
    # deterministic compatibility path only for those synthetic fixtures.
    if not oos_performance.fold_performance:
        canonical = {
            "evaluation_freeze": evaluation_freeze.logical_values(),
            "oos_performance": oos_performance.logical_values(),
        }
        encoded = json.dumps(
            _canonical_json_value(canonical),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return _remember_identity_fingerprint(
            evaluation_freeze,
            oos_performance,
            ResearchFrozenOosFingerprint(sha256(encoded).hexdigest()),
        )

    return _remember_identity_fingerprint(
        evaluation_freeze,
        oos_performance,
        _stream_valid_oos_fingerprint(
            evaluation_freeze=evaluation_freeze,
            oos_performance=oos_performance,
        ),
    )


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
