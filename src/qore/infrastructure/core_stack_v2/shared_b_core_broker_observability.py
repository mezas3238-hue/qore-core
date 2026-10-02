"""Architect-B Core/Broker observational cognition.

Describes observable runtime infrastructure state without mutation authority.
Unknown evidence remains UNKNOWN and must never be normalized to HEALTHY.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SharedBObservedSystemKind(StrEnum):
    PROVIDER = "PROVIDER"
    BROKER = "BROKER"
    DATA_FEED = "DATA_FEED"
    CORE_COMPONENT = "CORE_COMPONENT"
    SENSOR_ADAPTER = "SENSOR_ADAPTER"


class SharedBObservedSystemState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SharedBSystemObservation:
    system_id: str
    system_kind: SharedBObservedSystemKind
    observed_at: datetime
    evidence_cutoff_at: datetime
    availability_known: bool
    available: bool | None
    latency_ms: int | None
    data_integrity_bps: int | None
    freshness_age_ms: int | None
    error_count: int | None
    provenance_refs: tuple[str, ...]
    broker_mutation_performed: bool = False
    restart_authority: bool = False
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.system_id.strip():
            raise ValueError("system_id must be non-empty")
        if not isinstance(self.system_kind, SharedBObservedSystemKind):
            raise ValueError("system_kind invalid")
        for name in ("observed_at", "evidence_cutoff_at"):
            value=getattr(self,name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.evidence_cutoff_at > self.observed_at:
            raise ValueError("future system evidence is forbidden")
        if type(self.availability_known) is not bool:
            raise ValueError("availability_known must be bool")
        if self.availability_known:
            if type(self.available) is not bool:
                raise ValueError("known availability requires bool value")
        elif self.available is not None:
            raise ValueError("unknown availability cannot carry a value")
        for name in ("latency_ms","freshness_age_ms","error_count"):
            value=getattr(self,name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be non-negative int or None")
        if self.data_integrity_bps is not None and (
            type(self.data_integrity_bps) is not int
            or not 0 <= self.data_integrity_bps <= 10_000
        ):
            raise ValueError("data_integrity_bps outside 0..10000")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise ValueError(
                "provenance_refs must be non-empty, unique and canonical"
            )
        if (
            self.broker_mutation_performed
            or self.restart_authority
            or self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("observational cognition carries forbidden authority")


@dataclass(frozen=True, slots=True)
class SharedBSystemAssessment:
    system_id: str
    system_kind: SharedBObservedSystemKind
    state: SharedBObservedSystemState
    observed_at: datetime
    evidence_cutoff_at: datetime
    latency_ms: int | None
    data_integrity_bps: int | None
    freshness_age_ms: int | None
    error_count: int | None
    new_market_inference_allowed: bool
    relation_support_allowed: bool
    reason_codes: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    mutation_authority: bool = False
    restart_authority: bool = False
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise ValueError("reason_codes must be non-empty and canonical")
        if (
            self.mutation_authority
            or self.restart_authority
            or self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.capital_authority
        ):
            raise ValueError("system assessment carries forbidden authority")

    def fingerprint(self) -> str:
        payload={
            "system_id":self.system_id,
            "system_kind":self.system_kind.value,
            "state":self.state.value,
            "observed_at":self.observed_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "evidence_cutoff_at":self.evidence_cutoff_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            "latency_ms":self.latency_ms,
            "data_integrity_bps":self.data_integrity_bps,
            "freshness_age_ms":self.freshness_age_ms,
            "error_count":self.error_count,
            "new_market_inference_allowed":self.new_market_inference_allowed,
            "relation_support_allowed":self.relation_support_allowed,
            "reason_codes":self.reason_codes,
            "provenance_refs":self.provenance_refs,
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",",":"),
                ensure_ascii=True,
            ).encode()
        ).hexdigest()


def assess_system_observation(
    observation: SharedBSystemObservation,
    *,
    latency_degraded_threshold_ms: int,
    integrity_degraded_threshold_bps: int,
    freshness_degraded_threshold_ms: int,
) -> SharedBSystemAssessment:
    """Classify runtime observability with explicit, versionable thresholds."""

    for name,value in (
        ("latency_degraded_threshold_ms",latency_degraded_threshold_ms),
        ("freshness_degraded_threshold_ms",freshness_degraded_threshold_ms),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be non-negative int")
    if (
        type(integrity_degraded_threshold_bps) is not int
        or not 0 <= integrity_degraded_threshold_bps <= 10_000
    ):
        raise ValueError(
            "integrity_degraded_threshold_bps outside 0..10000"
        )

    reasons:list[str]=[]
    if not observation.availability_known:
        state=SharedBObservedSystemState.UNKNOWN
        reasons.append("SYSTEM_AVAILABILITY_UNKNOWN")
    elif observation.available is False:
        state=SharedBObservedSystemState.UNAVAILABLE
        reasons.append("SYSTEM_UNAVAILABLE")
    else:
        degraded=False
        if observation.latency_ms is None:
            degraded=True
            reasons.append("LATENCY_UNKNOWN")
        elif observation.latency_ms > latency_degraded_threshold_ms:
            degraded=True
            reasons.append("LATENCY_DEGRADED")
        if observation.data_integrity_bps is None:
            degraded=True
            reasons.append("DATA_INTEGRITY_UNKNOWN")
        elif observation.data_integrity_bps < integrity_degraded_threshold_bps:
            degraded=True
            reasons.append("DATA_INTEGRITY_DEGRADED")
        if observation.freshness_age_ms is None:
            degraded=True
            reasons.append("FRESHNESS_UNKNOWN")
        elif observation.freshness_age_ms > freshness_degraded_threshold_ms:
            degraded=True
            reasons.append("FRESHNESS_DEGRADED")
        if observation.error_count is None:
            degraded=True
            reasons.append("ERROR_COUNT_UNKNOWN")
        elif observation.error_count > 0:
            degraded=True
            reasons.append("SYSTEM_ERRORS_PRESENT")
        if degraded:
            state=SharedBObservedSystemState.DEGRADED
        else:
            state=SharedBObservedSystemState.HEALTHY
            reasons.append("SYSTEM_OBSERVATION_HEALTHY")

    healthy=state is SharedBObservedSystemState.HEALTHY
    return SharedBSystemAssessment(
        system_id=observation.system_id,
        system_kind=observation.system_kind,
        state=state,
        observed_at=observation.observed_at,
        evidence_cutoff_at=observation.evidence_cutoff_at,
        latency_ms=observation.latency_ms,
        data_integrity_bps=observation.data_integrity_bps,
        freshness_age_ms=observation.freshness_age_ms,
        error_count=observation.error_count,
        new_market_inference_allowed=healthy,
        relation_support_allowed=healthy,
        reason_codes=tuple(sorted(set(reasons))),
        provenance_refs=observation.provenance_refs,
    )
