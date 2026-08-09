from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ClientId,
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.secrets import SecretRef
from qore.kernel.errors import InfrastructureError


class HostingExecutionUnitError(InfrastructureError):
    """Base error for managed-hosting Account Execution Unit contracts."""

    __slots__ = ()


class HostingExecutionUnitValidationError(HostingExecutionUnitError):
    """Violation of an Account Execution Unit invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HostingExecutionUnitValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingExecutionUnitValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingExecutionUnitValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingExecutionUnitId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="hosting execution unit id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingDeploymentReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="hosting deployment reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingRegionReference:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]{1,63}", self.value
        ) is None:
            raise HostingExecutionUnitValidationError(
                "hosting region reference must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class HostingSoftwareVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?", self.value
        ) is None:
            raise HostingExecutionUnitValidationError(
                "hosting software version must use semantic-version syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class HostingMode(StrEnum):
    SELF_HOSTED = "self_hosted"
    QORE_MANAGED = "qore_managed"


class HostingExecutionUnitState(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HostingExecutionUnit:
    """Account-scoped runtime placement descriptor without execution authority."""

    unit_id: HostingExecutionUnitId
    client_id: ClientId
    account_id: TradingAccountId
    mode: HostingMode
    runtime_ref: ExecutionRuntimeReference
    software_version: HostingSoftwareVersion
    deployment_ref: HostingDeploymentReference | None
    region_ref: HostingRegionReference | None
    secret_refs: tuple[SecretRef, ...]
    state: HostingExecutionUnitState
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.unit_id, HostingExecutionUnitId):
            raise HostingExecutionUnitValidationError(
                "unit_id must be HostingExecutionUnitId"
            )
        if not isinstance(self.client_id, ClientId):
            raise HostingExecutionUnitValidationError("client_id must be ClientId")
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingExecutionUnitValidationError(
                "account_id must be TradingAccountId"
            )
        if not isinstance(self.mode, HostingMode):
            raise HostingExecutionUnitValidationError("mode must be HostingMode")
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingExecutionUnitValidationError(
                "runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.software_version, HostingSoftwareVersion):
            raise HostingExecutionUnitValidationError(
                "software_version must be HostingSoftwareVersion"
            )
        if self.deployment_ref is not None and not isinstance(
            self.deployment_ref, HostingDeploymentReference
        ):
            raise HostingExecutionUnitValidationError(
                "deployment_ref must be HostingDeploymentReference or None"
            )
        if self.region_ref is not None and not isinstance(
            self.region_ref, HostingRegionReference
        ):
            raise HostingExecutionUnitValidationError(
                "region_ref must be HostingRegionReference or None"
            )
        if not isinstance(self.secret_refs, tuple) or any(
            not isinstance(secret_ref, SecretRef) for secret_ref in self.secret_refs
        ):
            raise HostingExecutionUnitValidationError(
                "secret_refs must be an immutable tuple of SecretRef"
            )
        secret_ids = [secret_ref.ref_id for secret_ref in self.secret_refs]
        if len(secret_ids) != len(set(secret_ids)):
            raise HostingExecutionUnitValidationError(
                "hosting secret references must be unique"
            )
        if not isinstance(self.state, HostingExecutionUnitState):
            raise HostingExecutionUnitValidationError(
                "state must be HostingExecutionUnitState"
            )
        _validate_timestamp(self.recorded_at, field_name="unit recorded_at")
        self._validate_mode_scope()

    def _validate_mode_scope(self) -> None:
        if self.mode is HostingMode.QORE_MANAGED:
            if self.deployment_ref is None or self.region_ref is None:
                raise HostingExecutionUnitValidationError(
                    "QORE_MANAGED unit requires deployment and region references"
                )
            return
        if self.deployment_ref is not None or self.region_ref is not None:
            raise HostingExecutionUnitValidationError(
                "SELF_HOSTED unit must not claim QORE deployment/region placement"
            )

    @property
    def is_qore_orchestrated(self) -> bool:
        """Return placement classification only; this is not execution authority."""

        return self.mode is HostingMode.QORE_MANAGED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.unit_id.logical_values(),
            self.client_id.logical_values(),
            self.account_id.logical_values(),
            self.mode.value,
            self.runtime_ref.logical_values(),
            self.software_version.logical_values(),
            self.deployment_ref.logical_values() if self.deployment_ref else None,
            self.region_ref.logical_values() if self.region_ref else None,
            tuple(secret_ref.logical_values() for secret_ref in self.secret_refs),
            self.state.value,
            self.recorded_at.isoformat(),
        )
