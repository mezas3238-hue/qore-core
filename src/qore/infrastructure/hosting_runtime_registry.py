from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_execution_unit import (
    HostingExecutionUnit,
    HostingExecutionUnitId,
    HostingMode,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HostingRuntimeRegistryError(InfrastructureError):
    """Base error for Managed Hosting Runtime Registry contracts."""

    __slots__ = ()


class HostingRuntimeRegistryValidationError(HostingRuntimeRegistryError):
    """Violation of a Runtime Registry invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class HostingRuntimeRegistryGeneration:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise HostingRuntimeRegistryValidationError(
                "runtime registry generation must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


class HostingRuntimeDesiredState(StrEnum):
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"


class HostingRuntimeObservedState(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingRuntimeRegistryValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingRuntimeRegistryValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingRuntimeRecord:
    """Registry observation for one QORE-managed runtime candidate."""

    unit: HostingExecutionUnit
    desired_state: HostingRuntimeDesiredState
    observed_state: HostingRuntimeObservedState
    registered_at: datetime
    observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.unit, HostingExecutionUnit):
            raise HostingRuntimeRegistryValidationError(
                "runtime record unit must be HostingExecutionUnit"
            )
        if self.unit.mode is not HostingMode.QORE_MANAGED:
            raise HostingRuntimeRegistryValidationError(
                "Runtime Registry accepts QORE_MANAGED units only"
            )
        if not isinstance(self.desired_state, HostingRuntimeDesiredState):
            raise HostingRuntimeRegistryValidationError(
                "desired_state must be HostingRuntimeDesiredState"
            )
        if not isinstance(self.observed_state, HostingRuntimeObservedState):
            raise HostingRuntimeRegistryValidationError(
                "observed_state must be HostingRuntimeObservedState"
            )
        _validate_timestamp(self.registered_at, field_name="runtime registered_at")
        _validate_timestamp(self.observed_at, field_name="runtime observed_at")
        if self.observed_at < self.registered_at:
            raise HostingRuntimeRegistryValidationError(
                "runtime observation must not predate registration"
            )

    @property
    def account_id(self) -> TradingAccountId:
        return self.unit.account_id

    @property
    def runtime_ref(self) -> ExecutionRuntimeReference:
        return self.unit.runtime_ref

    @property
    def unit_id(self) -> HostingExecutionUnitId:
        return self.unit.unit_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.unit.logical_values(),
            self.desired_state.value,
            self.observed_state.value,
            self.registered_at.isoformat(),
            self.observed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class HostingRuntimeRegistrySnapshot:
    """Immutable registry of runtime candidates; never a writer-election record."""

    generation: HostingRuntimeRegistryGeneration
    records: tuple[HostingRuntimeRecord, ...]
    captured_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.generation, HostingRuntimeRegistryGeneration):
            raise HostingRuntimeRegistryValidationError(
                "registry generation must be HostingRuntimeRegistryGeneration"
            )
        if not isinstance(self.records, tuple):
            raise HostingRuntimeRegistryValidationError(
                "registry records must be immutable tuple"
            )
        if any(not isinstance(record, HostingRuntimeRecord) for record in self.records):
            raise HostingRuntimeRegistryValidationError(
                "registry records must contain HostingRuntimeRecord"
            )
        _validate_timestamp(self.captured_at, field_name="registry captured_at")
        unit_ids = [record.unit_id for record in self.records]
        runtime_refs = [record.runtime_ref for record in self.records]
        if len(unit_ids) != len(set(unit_ids)):
            raise HostingRuntimeRegistryValidationError(
                "registry unit identities must be unique"
            )
        if len(runtime_refs) != len(set(runtime_refs)):
            raise HostingRuntimeRegistryValidationError(
                "registry runtime references must be unique"
            )
        if any(record.observed_at > self.captured_at for record in self.records):
            raise HostingRuntimeRegistryValidationError(
                "registry record cannot be newer than snapshot"
            )
        object.__setattr__(
            self,
            "records",
            tuple(
                sorted(
                    self.records,
                    key=lambda record: (
                        str(record.account_id.value),
                        str(record.runtime_ref.value),
                    ),
                )
            ),
        )

    def candidates_for_account(
        self,
        account_id: TradingAccountId,
    ) -> tuple[HostingRuntimeRecord, ...]:
        if not isinstance(account_id, TradingAccountId):
            raise HostingRuntimeRegistryValidationError(
                "account_id must be TradingAccountId"
            )
        return tuple(
            record for record in self.records if record.account_id == account_id
        )

    def resolve_runtime(
        self,
        runtime_ref: ExecutionRuntimeReference,
    ) -> Result[HostingRuntimeRecord, HostingRuntimeRegistryError]:
        if not isinstance(runtime_ref, ExecutionRuntimeReference):
            return Failure(
                HostingRuntimeRegistryValidationError(
                    "runtime_ref must be ExecutionRuntimeReference"
                )
            )
        matches = tuple(
            record for record in self.records if record.runtime_ref == runtime_ref
        )
        if len(matches) != 1:
            return Failure(
                HostingRuntimeRegistryValidationError(
                    "exact runtime record not found"
                )
            )
        return Success(matches[0])

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.generation.logical_values(),
            tuple(record.logical_values() for record in self.records),
            self.captured_at.isoformat(),
        )
