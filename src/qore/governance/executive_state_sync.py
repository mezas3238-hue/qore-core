from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_client_surface import ExecutiveClientSurfaceId
from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveReadDelivery
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExecutiveStateSyncError(DomainError):
    """Base error for executive presentation-state synchronization contracts."""

    __slots__ = ()


class ExecutiveStateSyncValidationError(ExecutiveStateSyncError):
    """A state-sync value violates a deterministic freshness invariant."""

    __slots__ = ()


class ExecutiveClientStateStatus(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveStateSyncValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveStateSyncValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_reason_code(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
        raise ExecutiveStateSyncValidationError(
            "state sync reason code must use canonical lowercase syntax"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveClientStateSnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveStateSyncValidationError(
                "executive client state snapshot id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveClientStateVersion:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ExecutiveStateSyncValidationError(
                "executive client state version must be int"
            )
        if self.value <= 0:
            raise ExecutiveStateSyncValidationError(
                "executive client state version must be positive"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveClientSubscriptionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveStateSyncValidationError(
                "executive client subscription id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveClientStateSnapshot:
    """One authorized read delivery with explicit client freshness semantics."""

    snapshot_id: ExecutiveClientStateSnapshotId
    version: ExecutiveClientStateVersion
    delivery: ExecutiveReadDelivery
    received_at: datetime
    fresh_until: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ExecutiveClientStateSnapshotId):
            raise ExecutiveStateSyncValidationError(
                "client state snapshot requires ExecutiveClientStateSnapshotId"
            )
        if not isinstance(self.version, ExecutiveClientStateVersion):
            raise ExecutiveStateSyncValidationError(
                "client state snapshot requires ExecutiveClientStateVersion"
            )
        if not isinstance(self.delivery, ExecutiveReadDelivery):
            raise ExecutiveStateSyncValidationError(
                "client state snapshot requires ExecutiveReadDelivery"
            )
        _validate_timestamp(self.received_at, field_name="received_at")
        _validate_timestamp(self.fresh_until, field_name="fresh_until")
        if self.received_at < self.delivery.receipt.completed_at:
            raise ExecutiveStateSyncValidationError(
                "client state snapshot cannot be received before read completion"
            )
        if self.fresh_until < self.received_at:
            raise ExecutiveStateSyncValidationError(
                "client state freshness deadline cannot predate receipt"
            )

    @property
    def scope(self) -> ExecutiveReadScope:
        return self.delivery.authorized_request.request.scope

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.version.logical_values(),
            self.delivery.logical_values(),
            self.received_at.isoformat(),
            self.fresh_until.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveClientSubscription:
    """Presentation-only subscription identity; it grants no command authority."""

    subscription_id: ExecutiveClientSubscriptionId
    surface_id: ExecutiveClientSurfaceId
    scope: ExecutiveReadScope
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.subscription_id, ExecutiveClientSubscriptionId):
            raise ExecutiveStateSyncValidationError(
                "client subscription requires ExecutiveClientSubscriptionId"
            )
        if not isinstance(self.surface_id, ExecutiveClientSurfaceId):
            raise ExecutiveStateSyncValidationError(
                "client subscription requires ExecutiveClientSurfaceId"
            )
        if not isinstance(self.scope, ExecutiveReadScope):
            raise ExecutiveStateSyncValidationError(
                "client subscription requires ExecutiveReadScope"
            )
        _validate_timestamp(self.created_at, field_name="created_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.subscription_id.logical_values(),
            self.surface_id.logical_values(),
            self.scope.value,
            self.created_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveClientSubscriptionUpdate:
    """One presentation-only subscription delivery bound to an exact snapshot."""

    subscription: ExecutiveClientSubscription
    snapshot: ExecutiveClientStateSnapshot
    delivered_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.subscription, ExecutiveClientSubscription):
            raise ExecutiveStateSyncValidationError(
                "subscription update requires ExecutiveClientSubscription"
            )
        if not isinstance(self.snapshot, ExecutiveClientStateSnapshot):
            raise ExecutiveStateSyncValidationError(
                "subscription update requires ExecutiveClientStateSnapshot"
            )
        _validate_timestamp(self.delivered_at, field_name="delivered_at")
        if self.snapshot.scope is not self.subscription.scope:
            raise ExecutiveStateSyncValidationError(
                "subscription update snapshot scope must match subscription"
            )
        if self.delivered_at < self.snapshot.received_at:
            raise ExecutiveStateSyncValidationError(
                "subscription delivery cannot predate snapshot receipt"
            )
        if self.delivered_at < self.subscription.created_at:
            raise ExecutiveStateSyncValidationError(
                "subscription delivery cannot predate subscription creation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.subscription.logical_values(),
            self.snapshot.logical_values(),
            self.delivered_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveClientStateView:
    """Explicit presentation state; local state is never silently assumed current."""

    status: ExecutiveClientStateStatus
    scope: ExecutiveReadScope
    observed_at: datetime
    reason_code: str
    snapshot: ExecutiveClientStateSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ExecutiveClientStateStatus):
            raise ExecutiveStateSyncValidationError(
                "client state view requires ExecutiveClientStateStatus"
            )
        if not isinstance(self.scope, ExecutiveReadScope):
            raise ExecutiveStateSyncValidationError(
                "client state view requires ExecutiveReadScope"
            )
        _validate_timestamp(self.observed_at, field_name="observed_at")
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))
        snapshot_required = self.status in (
            ExecutiveClientStateStatus.CURRENT,
            ExecutiveClientStateStatus.STALE,
        )
        if snapshot_required and not isinstance(
            self.snapshot,
            ExecutiveClientStateSnapshot,
        ):
            raise ExecutiveStateSyncValidationError(
                "current or stale state requires an exact snapshot"
            )
        if not snapshot_required and self.snapshot is not None:
            raise ExecutiveStateSyncValidationError(
                "unavailable or unknown state must not masquerade as a snapshot"
            )
        if self.snapshot is not None and self.snapshot.scope is not self.scope:
            raise ExecutiveStateSyncValidationError(
                "client state view scope must match snapshot"
            )
        if self.snapshot is not None and self.observed_at < self.snapshot.received_at:
            raise ExecutiveStateSyncValidationError(
                "client state observation cannot predate snapshot receipt"
            )
        if (
            self.status is ExecutiveClientStateStatus.CURRENT
            and self.snapshot is not None
            and self.observed_at > self.snapshot.fresh_until
        ):
            raise ExecutiveStateSyncValidationError(
                "current client state cannot exceed freshness deadline"
            )
        if (
            self.status is ExecutiveClientStateStatus.STALE
            and self.snapshot is not None
            and self.observed_at <= self.snapshot.fresh_until
        ):
            raise ExecutiveStateSyncValidationError(
                "stale client state requires freshness deadline to have passed"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            self.scope.value,
            self.observed_at.isoformat(),
            self.reason_code,
            None if self.snapshot is None else self.snapshot.logical_values(),
        )


def evaluate_executive_client_state_snapshot(
    snapshot: ExecutiveClientStateSnapshot,
    *,
    evaluated_at: datetime,
) -> Result[ExecutiveClientStateView, ExecutiveStateSyncError]:
    if not isinstance(snapshot, ExecutiveClientStateSnapshot):
        return Failure(
            ExecutiveStateSyncValidationError(
                "state evaluation requires ExecutiveClientStateSnapshot"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="evaluated_at")
        if evaluated_at < snapshot.received_at:
            raise ExecutiveStateSyncValidationError(
                "state evaluation cannot predate snapshot receipt"
            )
        status = (
            ExecutiveClientStateStatus.CURRENT
            if evaluated_at <= snapshot.fresh_until
            else ExecutiveClientStateStatus.STALE
        )
        reason_code = (
            "snapshot.current"
            if status is ExecutiveClientStateStatus.CURRENT
            else "snapshot.stale"
        )
        return Success(
            ExecutiveClientStateView(
                status=status,
                scope=snapshot.scope,
                observed_at=evaluated_at,
                reason_code=reason_code,
                snapshot=snapshot,
            )
        )
    except ExecutiveStateSyncError as error:
        return Failure(error)


def build_executive_client_absent_state(
    *,
    status: ExecutiveClientStateStatus,
    scope: ExecutiveReadScope,
    observed_at: datetime,
    reason_code: str,
) -> Result[ExecutiveClientStateView, ExecutiveStateSyncError]:
    if status not in (
        ExecutiveClientStateStatus.UNAVAILABLE,
        ExecutiveClientStateStatus.UNKNOWN,
    ):
        return Failure(
            ExecutiveStateSyncValidationError(
                "absent client state must be unavailable or unknown"
            )
        )
    try:
        return Success(
            ExecutiveClientStateView(
                status=status,
                scope=scope,
                observed_at=observed_at,
                reason_code=reason_code,
                snapshot=None,
            )
        )
    except ExecutiveStateSyncError as error:
        return Failure(error)
