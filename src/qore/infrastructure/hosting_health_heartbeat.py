from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_runtime_registry import HostingRuntimeRegistrySnapshot
from qore.kernel.errors import InfrastructureError


class HostingHealthHeartbeatError(InfrastructureError):
    """Base error for Managed Hosting health/heartbeat contracts."""

    __slots__ = ()


class HostingHealthHeartbeatValidationError(HostingHealthHeartbeatError):
    """Violation of a health/heartbeat invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingHealthHeartbeatValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingHealthHeartbeatValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingHeartbeatId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingHealthHeartbeatValidationError(
                "hosting heartbeat id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingHeartbeatEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingHealthHeartbeatValidationError(
                "hosting heartbeat evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingRuntimeHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class HostingHeartbeatFreshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class HostingNewWorkContainment(StrEnum):
    NONE = "none"
    STOP_ASSIGNING_NEW_WORK = "stop_assigning_new_work"
    FAIL_CLOSED = "fail_closed"


@dataclass(frozen=True, slots=True)
class HostingHeartbeatSample:
    """Runtime liveness observation; never execution authority."""

    heartbeat_id: HostingHeartbeatId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    health: HostingRuntimeHealth
    observed_at: datetime
    fresh_until: datetime
    evidence_ref: HostingHeartbeatEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.heartbeat_id, HostingHeartbeatId):
            raise HostingHealthHeartbeatValidationError(
                "heartbeat_id must be HostingHeartbeatId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingHealthHeartbeatValidationError(
                "heartbeat account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingHealthHeartbeatValidationError(
                "heartbeat runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.health, HostingRuntimeHealth):
            raise HostingHealthHeartbeatValidationError(
                "heartbeat health must be HostingRuntimeHealth"
            )
        _validate_timestamp(self.observed_at, field_name="heartbeat observed_at")
        _validate_timestamp(self.fresh_until, field_name="heartbeat fresh_until")
        if self.fresh_until <= self.observed_at:
            raise HostingHealthHeartbeatValidationError(
                "heartbeat fresh_until must be after observed_at"
            )
        if not isinstance(self.evidence_ref, HostingHeartbeatEvidenceReference):
            raise HostingHealthHeartbeatValidationError(
                "heartbeat evidence_ref must be HostingHeartbeatEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.heartbeat_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.health.value,
            self.observed_at.isoformat(),
            self.fresh_until.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingRuntimeHealthAssessment:
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    health: HostingRuntimeHealth
    freshness: HostingHeartbeatFreshness
    containment: HostingNewWorkContainment
    evaluated_at: datetime
    heartbeat_id: HostingHeartbeatId | None
    evidence_ref: HostingHeartbeatEvidenceReference | None

    def __post_init__(self) -> None:
        _validate_timestamp(self.evaluated_at, field_name="health evaluated_at")
        if self.freshness is HostingHeartbeatFreshness.UNKNOWN:
            if self.heartbeat_id is not None or self.evidence_ref is not None:
                raise HostingHealthHeartbeatValidationError(
                    "UNKNOWN heartbeat freshness must not claim heartbeat evidence"
                )
        elif not isinstance(self.heartbeat_id, HostingHeartbeatId) or not isinstance(
            self.evidence_ref, HostingHeartbeatEvidenceReference
        ):
            raise HostingHealthHeartbeatValidationError(
                "known heartbeat freshness requires heartbeat identity/evidence"
            )
        expected = _containment_for(self.health, self.freshness)
        if self.containment is not expected:
            raise HostingHealthHeartbeatValidationError(
                "health containment must derive from health/freshness"
            )

    @property
    def requires_new_work_containment(self) -> bool:
        return self.containment is not HostingNewWorkContainment.NONE

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.health.value,
            self.freshness.value,
            self.containment.value,
            self.evaluated_at.isoformat(),
            self.heartbeat_id.logical_values() if self.heartbeat_id else None,
            self.evidence_ref.logical_values() if self.evidence_ref else None,
        )


def _containment_for(
    health: HostingRuntimeHealth,
    freshness: HostingHeartbeatFreshness,
) -> HostingNewWorkContainment:
    if freshness is HostingHeartbeatFreshness.UNKNOWN:
        return HostingNewWorkContainment.FAIL_CLOSED
    if freshness is HostingHeartbeatFreshness.STALE:
        return HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK
    if health in (HostingRuntimeHealth.UNREACHABLE, HostingRuntimeHealth.UNKNOWN):
        return HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK
    if health is HostingRuntimeHealth.DEGRADED:
        return HostingNewWorkContainment.STOP_ASSIGNING_NEW_WORK
    return HostingNewWorkContainment.NONE


def assess_hosting_runtime_health(
    registry: HostingRuntimeRegistrySnapshot,
    *,
    account_id: TradingAccountId,
    runtime_ref: ExecutionRuntimeReference,
    heartbeat: HostingHeartbeatSample | None,
    evaluated_at: datetime,
) -> HostingRuntimeHealthAssessment:
    """Assess liveness only; never elect, fence or grant writer authority."""

    _validate_timestamp(evaluated_at, field_name="health evaluated_at")
    resolved = registry.resolve_runtime(runtime_ref)
    if not hasattr(resolved, "value"):
        raise HostingHealthHeartbeatValidationError(
            "health runtime must exist in Runtime Registry"
        )
    record = resolved.value
    if record.account_id != account_id:
        raise HostingHealthHeartbeatValidationError(
            "health runtime/account binding mismatch"
        )
    if heartbeat is None:
        return HostingRuntimeHealthAssessment(
            account_id=account_id,
            runtime_ref=runtime_ref,
            health=HostingRuntimeHealth.UNKNOWN,
            freshness=HostingHeartbeatFreshness.UNKNOWN,
            containment=HostingNewWorkContainment.FAIL_CLOSED,
            evaluated_at=evaluated_at,
            heartbeat_id=None,
            evidence_ref=None,
        )
    if heartbeat.account_id != account_id or heartbeat.runtime_ref != runtime_ref:
        raise HostingHealthHeartbeatValidationError(
            "heartbeat account/runtime binding mismatch"
        )
    if heartbeat.observed_at > evaluated_at:
        raise HostingHealthHeartbeatValidationError(
            "heartbeat cannot be observed in the future"
        )
    freshness = (
        HostingHeartbeatFreshness.CURRENT
        if evaluated_at < heartbeat.fresh_until
        else HostingHeartbeatFreshness.STALE
    )
    containment = _containment_for(heartbeat.health, freshness)
    return HostingRuntimeHealthAssessment(
        account_id=account_id,
        runtime_ref=runtime_ref,
        health=heartbeat.health,
        freshness=freshness,
        containment=containment,
        evaluated_at=evaluated_at,
        heartbeat_id=heartbeat.heartbeat_id,
        evidence_ref=heartbeat.evidence_ref,
    )
