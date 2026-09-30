"""Architect-B Active Perception acquisition and VOI prerequisite contracts.

Architect B may describe whether requested information exists, can be acquired
causally, how expensive/slow/redundant/degraded it is, and what immutable
evidence was produced. It must not decide scientific value, predictive value,
trade priority, capital priority, or economic utility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SharedBAcquisitionStatus(StrEnum):
    REQUESTED = "REQUESTED"
    AVAILABLE = "AVAILABLE"
    ACQUIRED = "ACQUIRED"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"
    REJECTED_BY_GOVERNANCE = "REJECTED_BY_GOVERNANCE"
    TECHNICAL_ERROR = "TECHNICAL_ERROR"
    UNKNOWN = "UNKNOWN"


class SharedBAcquisitionFeasibility(StrEnum):
    FEASIBLE = "FEASIBLE"
    FEASIBLE_DEGRADED = "FEASIBLE_DEGRADED"
    NOT_FEASIBLE = "NOT_FEASIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SharedBInformationGap:
    gap_id: str
    sensor_family: str
    market_scope: str
    horizon: str
    required_by_at: datetime
    causal_cutoff_at: datetime
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("gap_id", "sensor_family", "market_scope", "horizon"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in ("required_by_at", "causal_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.causal_cutoff_at > self.required_by_at:
            raise ValueError("gap causal cutoff cannot follow required_by_at")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError(
                "gap provenance must be non-empty, unique and canonical"
            )


@dataclass(frozen=True, slots=True)
class SharedBSensorAcquisitionCandidate:
    gap_id: str
    sensor_id: str
    provider_or_source_id: str
    canonical_observation_key: str | None
    available: bool | None
    causally_available_by_cutoff: bool | None
    expected_latency_ms: int | None
    acquisition_cost_units: int | None
    redundancy_bps: int | None
    health_bps: int | None
    deterministic_replay_supported: bool
    exact_provenance_supported: bool
    raw_evidence_retention_supported: bool
    provider_revision_policy_known: bool
    status: SharedBAcquisitionStatus
    evidence_cutoff_at: datetime
    assessed_at: datetime
    provenance_refs: tuple[str, ...]
    target_or_outcome_used: bool = False
    pnl_used: bool = False
    trade_priority_authority: bool = False
    capital_priority_authority: bool = False
    sensor_admission_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("gap_id", "sensor_id", "provider_or_source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.canonical_observation_key is not None and not (
            isinstance(self.canonical_observation_key, str)
            and self.canonical_observation_key.strip()
        ):
            raise ValueError(
                "canonical_observation_key must be non-empty when present"
            )
        for name in ("available", "causally_available_by_cutoff"):
            value = getattr(self, name)
            if value not in (True, False, None):
                raise ValueError(f"{name} must be bool or None")
        for name in ("expected_latency_ms", "acquisition_cost_units"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be non-negative int or None")
        for name in ("redundancy_bps", "health_bps"):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not int or not 0 <= value <= 10_000
            ):
                raise ValueError(f"{name} outside 0..10000")
        for name in ("evidence_cutoff_at", "assessed_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.assessed_at:
            raise ValueError("candidate assessment cannot use future evidence")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError(
                "candidate provenance must be non-empty, unique and canonical"
            )
        if (
            self.target_or_outcome_used
            or self.pnl_used
            or self.trade_priority_authority
            or self.capital_priority_authority
            or self.sensor_admission_authority
            or self.execution_authority
            or self.risk_authority
        ):
            raise ValueError(
                "sensor-side acquisition candidate carries forbidden evidence "
                "or authority"
            )


@dataclass(frozen=True, slots=True)
class SharedBAcquisitionFeasibilityAssessment:
    gap_id: str
    sensor_id: str
    feasibility: SharedBAcquisitionFeasibility
    acquisition_cost_units: int | None
    expected_latency_ms: int | None
    redundancy_bps: int | None
    health_bps: int | None
    reason_codes: tuple[str, ...]
    cognitive_value_decided: bool = False
    predictive_value_decided: bool = False
    economic_value_decided: bool = False
    trade_priority_authority: bool = False
    capital_priority_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("reason_codes must be non-empty and canonical")
        if (
            self.cognitive_value_decided
            or self.predictive_value_decided
            or self.economic_value_decided
            or self.trade_priority_authority
            or self.capital_priority_authority
        ):
            raise ValueError(
                "B feasibility assessment cannot decide downstream value"
            )


@dataclass(frozen=True, slots=True)
class SharedBActivePerceptionAcquisitionResult:
    gap_id: str
    sensor_id: str
    status: SharedBAcquisitionStatus
    provider_or_source_id: str
    canonical_observation_key: str | None
    provider_event_min_at: datetime | None
    provider_event_max_at: datetime | None
    retrieved_at: datetime | None
    raw_evidence_sha256: str | None
    replay_manifest_sha256: str | None
    artifact_id: int | None
    record_count: int
    missing_count: int
    degraded_count: int
    deterministic_replay_verified: bool
    exact_provenance_verified: bool
    broker_mutation: bool = False
    target_or_outcome_read: bool = False
    pnl_read: bool = False
    methodology_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("gap_id", "sensor_id", "provider_or_source_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        for name in (
            "provider_event_min_at",
            "provider_event_max_at",
            "retrieved_at",
        ):
            value = getattr(self, name)
            if value is not None and (
                value.tzinfo is None or value.utcoffset() is None
            ):
                raise ValueError(f"{name} must be timezone-aware")
        if (
            self.provider_event_min_at is not None
            and self.provider_event_max_at is not None
            and self.provider_event_max_at < self.provider_event_min_at
        ):
            raise ValueError("provider event range is reversed")
        if self.retrieved_at is not None:
            for event_time in (
                self.provider_event_min_at,
                self.provider_event_max_at,
            ):
                if event_time is not None and self.retrieved_at < event_time:
                    raise ValueError(
                        "retrieved_at cannot predate provider event time"
                    )
        for name in ("record_count", "missing_count", "degraded_count"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative int")
        if self.artifact_id is not None and (
            type(self.artifact_id) is not int or self.artifact_id <= 0
        ):
            raise ValueError("artifact_id must be positive int when present")
        for name in ("raw_evidence_sha256", "replay_manifest_sha256"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, str) or len(value) != 64:
                    raise ValueError(f"{name} must be sha256 hex")
                try:
                    int(value, 16)
                except ValueError as exc:
                    raise ValueError(f"{name} must be sha256 hex") from exc
        if self.status is SharedBAcquisitionStatus.ACQUIRED:
            if (
                self.raw_evidence_sha256 is None
                or self.replay_manifest_sha256 is None
                or self.artifact_id is None
                or not self.deterministic_replay_verified
                or not self.exact_provenance_verified
            ):
                raise ValueError(
                    "ACQUIRED requires sealed replayable provenance evidence"
                )
        if (
            self.broker_mutation
            or self.target_or_outcome_read
            or self.pnl_read
            or self.methodology_authority
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise ValueError(
                "sensor acquisition result carries forbidden evidence/authority"
            )

    def fingerprint(self) -> str:
        def iso(value: datetime | None) -> str | None:
            return (
                None
                if value is None
                else value.astimezone(UTC).isoformat(timespec="microseconds")
            )

        payload = {
            "gap_id": self.gap_id,
            "sensor_id": self.sensor_id,
            "status": self.status.value,
            "provider_or_source_id": self.provider_or_source_id,
            "canonical_observation_key": self.canonical_observation_key,
            "provider_event_min_at": iso(self.provider_event_min_at),
            "provider_event_max_at": iso(self.provider_event_max_at),
            "retrieved_at": iso(self.retrieved_at),
            "raw_evidence_sha256": self.raw_evidence_sha256,
            "replay_manifest_sha256": self.replay_manifest_sha256,
            "artifact_id": self.artifact_id,
            "record_count": self.record_count,
            "missing_count": self.missing_count,
            "degraded_count": self.degraded_count,
            "deterministic_replay_verified": self.deterministic_replay_verified,
            "exact_provenance_verified": self.exact_provenance_verified,
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()


def assess_acquisition_feasibility(
    *,
    gap: SharedBInformationGap,
    candidate: SharedBSensorAcquisitionCandidate,
    maximum_latency_ms: int,
    maximum_acquisition_cost_units: int,
    minimum_health_bps: int,
) -> SharedBAcquisitionFeasibilityAssessment:
    """Assess only whether information can be observed lawfully and on time."""

    if candidate.gap_id != gap.gap_id:
        raise ValueError("candidate/gap identity mismatch")
    if type(maximum_latency_ms) is not int or maximum_latency_ms < 0:
        raise ValueError("maximum_latency_ms must be non-negative int")
    if (
        type(maximum_acquisition_cost_units) is not int
        or maximum_acquisition_cost_units < 0
    ):
        raise ValueError(
            "maximum_acquisition_cost_units must be non-negative int"
        )
    if (
        type(minimum_health_bps) is not int
        or not 0 <= minimum_health_bps <= 10_000
    ):
        raise ValueError("minimum_health_bps outside 0..10000")

    reasons: list[str] = []
    if candidate.status in {
        SharedBAcquisitionStatus.REJECTED_BY_GOVERNANCE,
        SharedBAcquisitionStatus.UNAVAILABLE,
        SharedBAcquisitionStatus.TECHNICAL_ERROR,
    }:
        feasibility = SharedBAcquisitionFeasibility.NOT_FEASIBLE
        reasons.append(f"STATUS_{candidate.status.value}")
    elif candidate.available is None or candidate.causally_available_by_cutoff is None:
        feasibility = SharedBAcquisitionFeasibility.UNKNOWN
        reasons.append("AVAILABILITY_OR_CAUSALITY_UNKNOWN")
    elif not candidate.available:
        feasibility = SharedBAcquisitionFeasibility.NOT_FEASIBLE
        reasons.append("SENSOR_UNAVAILABLE")
    elif not candidate.causally_available_by_cutoff:
        feasibility = SharedBAcquisitionFeasibility.NOT_FEASIBLE
        reasons.append("NOT_AVAILABLE_BY_CAUSAL_CUTOFF")
    elif (
        not candidate.deterministic_replay_supported
        or not candidate.exact_provenance_supported
        or not candidate.raw_evidence_retention_supported
        or not candidate.provider_revision_policy_known
    ):
        feasibility = SharedBAcquisitionFeasibility.NOT_FEASIBLE
        reasons.append("EVIDENCE_GOVERNANCE_INCOMPLETE")
    elif (
        candidate.expected_latency_ms is None
        or candidate.acquisition_cost_units is None
        or candidate.health_bps is None
    ):
        feasibility = SharedBAcquisitionFeasibility.UNKNOWN
        reasons.append("COST_LATENCY_OR_HEALTH_UNKNOWN")
    elif candidate.expected_latency_ms > maximum_latency_ms:
        feasibility = SharedBAcquisitionFeasibility.NOT_FEASIBLE
        reasons.append("LATENCY_EXCEEDS_REQUIREMENT")
    elif candidate.acquisition_cost_units > maximum_acquisition_cost_units:
        feasibility = SharedBAcquisitionFeasibility.NOT_FEASIBLE
        reasons.append("ACQUISITION_COST_EXCEEDS_BUDGET")
    elif candidate.health_bps < minimum_health_bps:
        feasibility = SharedBAcquisitionFeasibility.FEASIBLE_DEGRADED
        reasons.append("SENSOR_HEALTH_DEGRADED")
    else:
        feasibility = SharedBAcquisitionFeasibility.FEASIBLE
        reasons.append("CAUSAL_ACQUISITION_FEASIBLE")

    return SharedBAcquisitionFeasibilityAssessment(
        gap_id=gap.gap_id,
        sensor_id=candidate.sensor_id,
        feasibility=feasibility,
        acquisition_cost_units=candidate.acquisition_cost_units,
        expected_latency_ms=candidate.expected_latency_ms,
        redundancy_bps=candidate.redundancy_bps,
        health_bps=candidate.health_bps,
        reason_codes=tuple(sorted(set(reasons))),
    )
