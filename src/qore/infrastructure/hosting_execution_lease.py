from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_execution_unit import HostingExecutionUnitId
from qore.infrastructure.hosting_runtime_registry import HostingRuntimeRegistrySnapshot
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HostingExecutionLeaseError(InfrastructureError):
    """Base error for Managed Hosting single-writer lease contracts."""

    __slots__ = ()


class HostingExecutionLeaseValidationError(HostingExecutionLeaseError):
    """Violation of an execution-lease/fencing invariant."""

    __slots__ = ()


class HostingExecutionLeaseConflictError(HostingExecutionLeaseError):
    """A requested lease conflicts with current single-writer state."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingExecutionLeaseValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingExecutionLeaseValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HostingExecutionLeaseValidationError(f"{field_name} must be UUID")


@dataclass(frozen=True, slots=True)
class HostingExecutionLeaseId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="hosting execution lease id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True, order=True)
class HostingFencingGeneration:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise HostingExecutionLeaseValidationError(
                "fencing generation must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class HostingLeaseEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="hosting lease evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingExecutionLeaseStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HostingExecutionLease:
    """Account/runtime-scoped writer lease with monotonic fencing generation."""

    lease_id: HostingExecutionLeaseId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    unit_id: HostingExecutionUnitId
    generation: HostingFencingGeneration
    status: HostingExecutionLeaseStatus
    acquired_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    evidence_ref: HostingLeaseEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.lease_id, HostingExecutionLeaseId):
            raise HostingExecutionLeaseValidationError(
                "lease_id must be HostingExecutionLeaseId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingExecutionLeaseValidationError(
                "lease account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingExecutionLeaseValidationError(
                "lease runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.unit_id, HostingExecutionUnitId):
            raise HostingExecutionLeaseValidationError(
                "lease unit_id must be HostingExecutionUnitId"
            )
        if not isinstance(self.generation, HostingFencingGeneration):
            raise HostingExecutionLeaseValidationError(
                "lease generation must be HostingFencingGeneration"
            )
        if not isinstance(self.status, HostingExecutionLeaseStatus):
            raise HostingExecutionLeaseValidationError(
                "lease status must be HostingExecutionLeaseStatus"
            )
        _validate_timestamp(self.acquired_at, field_name="lease acquired_at")
        _validate_timestamp(self.expires_at, field_name="lease expires_at")
        if self.expires_at <= self.acquired_at:
            raise HostingExecutionLeaseValidationError(
                "lease expires_at must be after acquired_at"
            )
        if self.revoked_at is not None:
            _validate_timestamp(self.revoked_at, field_name="lease revoked_at")
            if self.revoked_at < self.acquired_at:
                raise HostingExecutionLeaseValidationError(
                    "lease revoked_at must not predate acquired_at"
                )
        if self.status is HostingExecutionLeaseStatus.REVOKED:
            if self.revoked_at is None:
                raise HostingExecutionLeaseValidationError(
                    "REVOKED lease requires revoked_at"
                )
        elif self.revoked_at is not None:
            raise HostingExecutionLeaseValidationError(
                "only REVOKED lease may carry revoked_at"
            )
        if not isinstance(self.evidence_ref, HostingLeaseEvidenceReference):
            raise HostingExecutionLeaseValidationError(
                "lease evidence_ref must be HostingLeaseEvidenceReference"
            )

    def is_authoritative_at(self, evaluated_at: datetime) -> bool:
        _validate_timestamp(evaluated_at, field_name="lease evaluated_at")
        return (
            self.status is HostingExecutionLeaseStatus.ACTIVE
            and self.acquired_at <= evaluated_at < self.expires_at
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.lease_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.unit_id.logical_values(),
            self.generation.logical_values(),
            self.status.value,
            self.acquired_at.isoformat(),
            self.expires_at.isoformat(),
            self.revoked_at.isoformat() if self.revoked_at else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingExecutionAuthorityAttestation:
    """Infrastructure writer attestation; never a strategic Core Decision."""

    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    lease_id: HostingExecutionLeaseId
    generation: HostingFencingGeneration
    evaluated_at: datetime
    evidence_ref: HostingLeaseEvidenceReference

    def __post_init__(self) -> None:
        _validate_timestamp(self.evaluated_at, field_name="authority evaluated_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.lease_id.logical_values(),
            self.generation.logical_values(),
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingExecutionLeaseSnapshot:
    """Immutable single-writer lease history/state for deterministic evaluation."""

    leases: tuple[HostingExecutionLease, ...]
    captured_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.leases, tuple) or any(
            not isinstance(lease, HostingExecutionLease) for lease in self.leases
        ):
            raise HostingExecutionLeaseValidationError(
                "lease snapshot requires immutable HostingExecutionLease tuple"
            )
        _validate_timestamp(self.captured_at, field_name="lease snapshot captured_at")
        lease_ids = [lease.lease_id for lease in self.leases]
        if len(lease_ids) != len(set(lease_ids)):
            raise HostingExecutionLeaseValidationError("lease ids must be unique")
        self._validate_account_generations()
        self._validate_single_writer_at_capture()
        object.__setattr__(
            self,
            "leases",
            tuple(
                sorted(
                    self.leases,
                    key=lambda lease: (
                        str(lease.account_id.value),
                        lease.generation.value,
                        lease.acquired_at,
                    ),
                )
            ),
        )

    def _validate_account_generations(self) -> None:
        accounts = {lease.account_id for lease in self.leases}
        for account_id in accounts:
            account_leases = sorted(
                (lease for lease in self.leases if lease.account_id == account_id),
                key=lambda lease: lease.acquired_at,
            )
            generations = [lease.generation.value for lease in account_leases]
            if len(generations) != len(set(generations)):
                raise HostingExecutionLeaseValidationError(
                    "fencing generations must be unique per account"
                )
            if generations != sorted(generations):
                raise HostingExecutionLeaseValidationError(
                    "fencing generations must increase with lease acquisition"
                )

    def _validate_single_writer_at_capture(self) -> None:
        accounts = {lease.account_id for lease in self.leases}
        for account_id in accounts:
            active = tuple(
                lease
                for lease in self.leases
                if lease.account_id == account_id
                and lease.is_authoritative_at(self.captured_at)
            )
            if len(active) > 1:
                raise HostingExecutionLeaseValidationError(
                    "at most one active execution authority is allowed per account"
                )

    def leases_for_account(
        self,
        account_id: TradingAccountId,
    ) -> tuple[HostingExecutionLease, ...]:
        return tuple(lease for lease in self.leases if lease.account_id == account_id)

    def current_authority(
        self,
        account_id: TradingAccountId,
        *,
        evaluated_at: datetime,
    ) -> Result[HostingExecutionAuthorityAttestation, HostingExecutionLeaseError]:
        _validate_timestamp(evaluated_at, field_name="authority evaluated_at")
        if evaluated_at > self.captured_at:
            return Failure(
                HostingExecutionLeaseValidationError(
                    "authority cannot be inferred beyond lease snapshot capture"
                )
            )
        current = tuple(
            lease
            for lease in self.leases
            if lease.account_id == account_id and lease.is_authoritative_at(evaluated_at)
        )
        if len(current) != 1:
            return Failure(
                HostingExecutionLeaseValidationError(
                    "exact single current execution authority not found"
                )
            )
        lease = current[0]
        newest_generation = max(
            (
                candidate.generation
                for candidate in self.leases
                if candidate.account_id == account_id
                and candidate.acquired_at <= evaluated_at
            ),
            default=lease.generation,
        )
        if lease.generation != newest_generation:
            return Failure(
                HostingExecutionLeaseValidationError(
                    "stale fenced lease generation cannot hold authority"
                )
            )
        return Success(
            HostingExecutionAuthorityAttestation(
                account_id=lease.account_id,
                runtime_ref=lease.runtime_ref,
                lease_id=lease.lease_id,
                generation=lease.generation,
                evaluated_at=evaluated_at,
                evidence_ref=lease.evidence_ref,
            )
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(lease.logical_values() for lease in self.leases),
            self.captured_at.isoformat(),
        )


def acquire_hosting_execution_lease(
    registry: HostingRuntimeRegistrySnapshot,
    snapshot: HostingExecutionLeaseSnapshot,
    *,
    account_id: TradingAccountId,
    runtime_ref: ExecutionRuntimeReference,
    lease_id: HostingExecutionLeaseId,
    generation: HostingFencingGeneration,
    acquired_at: datetime,
    expires_at: datetime,
    evidence_ref: HostingLeaseEvidenceReference,
) -> Result[HostingExecutionLeaseSnapshot, HostingExecutionLeaseError]:
    """Deterministically model one acquisition; durable adapters must make it atomic."""

    _validate_timestamp(acquired_at, field_name="lease acquired_at")
    resolved = registry.resolve_runtime(runtime_ref)
    if isinstance(resolved, Failure):
        return Failure(
            HostingExecutionLeaseValidationError(
                "lease runtime must exist in Runtime Registry"
            )
        )
    record = resolved.value
    if record.account_id != account_id:
        return Failure(
            HostingExecutionLeaseValidationError(
                "lease runtime/account binding mismatch"
            )
        )
    existing_authority = snapshot.current_authority(
        account_id,
        evaluated_at=min(acquired_at, snapshot.captured_at),
    )
    if isinstance(existing_authority, Success):
        return Failure(
            HostingExecutionLeaseConflictError(
                "account already has active execution authority"
            )
        )
    previous = snapshot.leases_for_account(account_id)
    if previous and generation.value <= max(
        lease.generation.value for lease in previous
    ):
        return Failure(
            HostingExecutionLeaseValidationError(
                "new lease fencing generation must exceed account history"
            )
        )
    try:
        lease = HostingExecutionLease(
            lease_id=lease_id,
            account_id=account_id,
            runtime_ref=runtime_ref,
            unit_id=record.unit_id,
            generation=generation,
            status=HostingExecutionLeaseStatus.ACTIVE,
            acquired_at=acquired_at,
            expires_at=expires_at,
            revoked_at=None,
            evidence_ref=evidence_ref,
        )
        return Success(
            HostingExecutionLeaseSnapshot(
                leases=(*snapshot.leases, lease),
                captured_at=max(snapshot.captured_at, acquired_at),
            )
        )
    except HostingExecutionLeaseError as error:
        return Failure(error)


def revoke_hosting_execution_lease(
    snapshot: HostingExecutionLeaseSnapshot,
    lease_id: HostingExecutionLeaseId,
    *,
    revoked_at: datetime,
    evidence_ref: HostingLeaseEvidenceReference,
) -> Result[HostingExecutionLeaseSnapshot, HostingExecutionLeaseError]:
    """Explicitly revoke one lease; no replacement lease is acquired automatically."""

    _validate_timestamp(revoked_at, field_name="lease revoked_at")
    matches = tuple(lease for lease in snapshot.leases if lease.lease_id == lease_id)
    if len(matches) != 1:
        return Failure(HostingExecutionLeaseValidationError("exact lease not found"))
    target = matches[0]
    if target.status is not HostingExecutionLeaseStatus.ACTIVE:
        return Failure(
            HostingExecutionLeaseValidationError("only ACTIVE lease may be revoked")
        )
    if revoked_at >= target.expires_at:
        return Failure(
            HostingExecutionLeaseValidationError(
                "revocation must occur before lease expiry"
            )
        )
    replacement = replace(
        target,
        status=HostingExecutionLeaseStatus.REVOKED,
        revoked_at=revoked_at,
        evidence_ref=evidence_ref,
    )
    leases = tuple(replacement if lease.lease_id == lease_id else lease for lease in snapshot.leases)
    try:
        return Success(
            HostingExecutionLeaseSnapshot(
                leases=leases,
                captured_at=max(snapshot.captured_at, revoked_at),
            )
        )
    except HostingExecutionLeaseError as error:
        return Failure(error)
