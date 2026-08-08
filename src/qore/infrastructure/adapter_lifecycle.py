from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

import qore.infrastructure.ports as ports
import qore.infrastructure.providers as providers
import qore.kernel.result as result_contract
from qore.domain.events import DomainMetadataValue

_RESERVED_LIFECYCLE_METADATA_KEYS = frozenset(
    {
        "actor",
        "causation_id",
        "correlation_id",
        "descriptor",
        "from_state",
        "provider",
        "reason",
        "state",
        "to_state",
        "transitioned_at",
    }
)


class AdapterLifecycleError(ports.ExternalPortError):
    """Base error for external adapter lifecycle contracts."""

    __slots__ = ()


class AdapterLifecycleValidationError(AdapterLifecycleError):
    """Violation of an adapter lifecycle contract invariant."""

    __slots__ = ()


class AdapterLifecycleInvalidTransitionError(AdapterLifecycleError):
    """Typed error for an invalid lifecycle transition."""

    __slots__ = ()


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, UUID)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise AdapterLifecycleValidationError(
        "adapter lifecycle metadata values must be immutable scalars or tuples"
    )


def _validate_explicit_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise AdapterLifecycleValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdapterLifecycleValidationError(f"{field_name} must be timezone-aware")


def _validate_lifecycle_metadata(
    metadata: Mapping[str, DomainMetadataValue],
    *,
    field_name: str,
) -> Mapping[str, DomainMetadataValue]:
    if not isinstance(metadata, Mapping):
        raise AdapterLifecycleValidationError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) or not key.strip() for key in metadata):
        raise AdapterLifecycleValidationError(
            f"{field_name} keys must be non-empty strings"
        )
    reserved = _RESERVED_LIFECYCLE_METADATA_KEYS.intersection(metadata)
    if reserved:
        names = ", ".join(sorted(reserved))
        raise AdapterLifecycleValidationError(
            f"reserved adapter lifecycle metadata keys: {names}"
        )
    for value in metadata.values():
        _validate_metadata_value(value)
    return MappingProxyType({key: metadata[key] for key in sorted(metadata)})


def _validate_request_metadata(metadata: ports.ExternalRequestMetadata) -> None:
    if not isinstance(metadata, ports.ExternalRequestMetadata):
        raise AdapterLifecycleValidationError(
            "adapter lifecycle metadata must be ExternalRequestMetadata"
        )
    if metadata.causation_id is None:
        raise AdapterLifecycleValidationError(
            "adapter lifecycle metadata causation_id is required"
        )


@dataclass(frozen=True, slots=True)
class AdapterLifecycleActor:
    """Explicit actor that requested or recorded a lifecycle transition."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*",
            self.value,
        ) is None:
            raise AdapterLifecycleValidationError(
                "adapter lifecycle actor must use lowercase letters, digits, dots, "
                "or hyphens"
            )

    def logical_values(self) -> tuple[str]:
        return (self.value,)


class AdapterLifecycleState(StrEnum):
    """Closed external adapter lifecycle state."""

    DECLARED = "declared"
    CONFIGURED = "configured"
    INITIALIZED = "initialized"
    STARTED = "started"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    FAILED = "failed"


class AdapterLifecycleTransitionReason(StrEnum):
    """Closed reason for a deterministic lifecycle transition."""

    DECLARED = "declared"
    CONFIGURATION_ACCEPTED = "configuration_accepted"
    INITIALIZE_REQUESTED = "initialize_requested"
    START_REQUESTED = "start_requested"
    DEGRADED_HEALTH = "degraded_health"
    RECOVERY_CONFIRMED = "recovery_confirmed"
    STOP_REQUESTED = "stop_requested"
    FAILURE_DETECTED = "failure_detected"
    RESET_REQUESTED = "reset_requested"


_ALLOWED_TRANSITIONS: Mapping[
    AdapterLifecycleState,
    frozenset[AdapterLifecycleState],
] = MappingProxyType(
    {
        AdapterLifecycleState.DECLARED: frozenset(
            {
                AdapterLifecycleState.DECLARED,
                AdapterLifecycleState.CONFIGURED,
                AdapterLifecycleState.FAILED,
            }
        ),
        AdapterLifecycleState.CONFIGURED: frozenset(
            {
                AdapterLifecycleState.INITIALIZED,
                AdapterLifecycleState.STOPPED,
                AdapterLifecycleState.FAILED,
            }
        ),
        AdapterLifecycleState.INITIALIZED: frozenset(
            {
                AdapterLifecycleState.STARTED,
                AdapterLifecycleState.STOPPED,
                AdapterLifecycleState.FAILED,
            }
        ),
        AdapterLifecycleState.STARTED: frozenset(
            {
                AdapterLifecycleState.DEGRADED,
                AdapterLifecycleState.STOPPED,
                AdapterLifecycleState.FAILED,
            }
        ),
        AdapterLifecycleState.DEGRADED: frozenset(
            {
                AdapterLifecycleState.STARTED,
                AdapterLifecycleState.STOPPED,
                AdapterLifecycleState.FAILED,
            }
        ),
        AdapterLifecycleState.STOPPED: frozenset(
            {
                AdapterLifecycleState.CONFIGURED,
                AdapterLifecycleState.INITIALIZED,
                AdapterLifecycleState.FAILED,
            }
        ),
        AdapterLifecycleState.FAILED: frozenset({AdapterLifecycleState.STOPPED}),
    }
)

_REASON_TARGETS: Mapping[
    AdapterLifecycleTransitionReason,
    frozenset[AdapterLifecycleState],
] = MappingProxyType(
    {
        AdapterLifecycleTransitionReason.DECLARED: frozenset(
            {AdapterLifecycleState.DECLARED}
        ),
        AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED: frozenset(
            {AdapterLifecycleState.CONFIGURED}
        ),
        AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED: frozenset(
            {AdapterLifecycleState.INITIALIZED}
        ),
        AdapterLifecycleTransitionReason.START_REQUESTED: frozenset(
            {AdapterLifecycleState.STARTED}
        ),
        AdapterLifecycleTransitionReason.DEGRADED_HEALTH: frozenset(
            {AdapterLifecycleState.DEGRADED}
        ),
        AdapterLifecycleTransitionReason.RECOVERY_CONFIRMED: frozenset(
            {AdapterLifecycleState.STARTED}
        ),
        AdapterLifecycleTransitionReason.STOP_REQUESTED: frozenset(
            {AdapterLifecycleState.STOPPED}
        ),
        AdapterLifecycleTransitionReason.FAILURE_DETECTED: frozenset(
            {AdapterLifecycleState.FAILED}
        ),
        AdapterLifecycleTransitionReason.RESET_REQUESTED: frozenset(
            {AdapterLifecycleState.CONFIGURED}
        ),
    }
)


def _validate_transition(
    *,
    from_state: AdapterLifecycleState,
    to_state: AdapterLifecycleState,
    reason: AdapterLifecycleTransitionReason,
    message: str | None,
) -> None:
    allowed_targets = _ALLOWED_TRANSITIONS[from_state]
    if to_state not in allowed_targets:
        raise AdapterLifecycleInvalidTransitionError(
            f"invalid adapter lifecycle transition: {from_state.value} -> "
            f"{to_state.value}"
        )
    reason_targets = _REASON_TARGETS[reason]
    if to_state not in reason_targets:
        raise AdapterLifecycleInvalidTransitionError(
            f"adapter lifecycle reason {reason.value} does not allow target "
            f"{to_state.value}"
        )
    if from_state is to_state and not (
        from_state is AdapterLifecycleState.DECLARED
        and reason is AdapterLifecycleTransitionReason.DECLARED
    ):
        raise AdapterLifecycleInvalidTransitionError(
            "adapter lifecycle self-transitions are only valid for declaration"
        )
    if to_state in {
        AdapterLifecycleState.DEGRADED,
        AdapterLifecycleState.FAILED,
    } and message is None:
        raise AdapterLifecycleValidationError(
            "degraded or failed lifecycle transitions require a message"
        )


@dataclass(frozen=True, slots=True)
class AdapterLifecycleTransition:
    """Immutable event describing one explicit lifecycle transition."""

    descriptor: ports.ExternalSourceDescriptor
    provider: providers.ProviderDescriptor
    from_state: AdapterLifecycleState
    to_state: AdapterLifecycleState
    reason: AdapterLifecycleTransitionReason
    transitioned_at: datetime
    actor: AdapterLifecycleActor
    metadata: ports.ExternalRequestMetadata
    message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ports.ExternalSourceDescriptor):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle descriptor must be ExternalSourceDescriptor"
            )
        if not isinstance(self.provider, providers.ProviderDescriptor):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle provider must be ProviderDescriptor"
            )
        if not isinstance(self.from_state, AdapterLifecycleState):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle from_state must be AdapterLifecycleState"
            )
        if not isinstance(self.to_state, AdapterLifecycleState):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle to_state must be AdapterLifecycleState"
            )
        if not isinstance(self.reason, AdapterLifecycleTransitionReason):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle reason must be AdapterLifecycleTransitionReason"
            )
        _validate_explicit_datetime(
            self.transitioned_at,
            field_name="transitioned_at",
        )
        if not isinstance(self.actor, AdapterLifecycleActor):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle actor must be AdapterLifecycleActor"
            )
        _validate_request_metadata(self.metadata)
        if self.message is not None and (
            not isinstance(self.message, str) or not self.message.strip()
        ):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle transition message must be non-empty or None"
            )
        _validate_transition(
            from_state=self.from_state,
            to_state=self.to_state,
            reason=self.reason,
            message=self.message,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.descriptor.logical_values(),
            self.provider.logical_values(),
            self.from_state.value,
            self.to_state.value,
            self.reason.value,
            self.transitioned_at.isoformat(),
            self.actor.logical_values(),
            self.metadata.logical_values(),
            self.message,
        )


@dataclass(frozen=True, slots=True)
class AdapterLifecycleTransitionRequest:
    """Explicit requested lifecycle transition, without global time or side effects."""

    to_state: AdapterLifecycleState
    reason: AdapterLifecycleTransitionReason
    transitioned_at: datetime
    actor: AdapterLifecycleActor
    metadata: ports.ExternalRequestMetadata
    message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.to_state, AdapterLifecycleState):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle request to_state must be AdapterLifecycleState"
            )
        if not isinstance(self.reason, AdapterLifecycleTransitionReason):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle request reason must be "
                "AdapterLifecycleTransitionReason"
            )
        _validate_explicit_datetime(
            self.transitioned_at,
            field_name="transitioned_at",
        )
        if not isinstance(self.actor, AdapterLifecycleActor):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle request actor must be AdapterLifecycleActor"
            )
        _validate_request_metadata(self.metadata)
        if self.message is not None and (
            not isinstance(self.message, str) or not self.message.strip()
        ):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle request message must be non-empty or None"
            )


@dataclass(frozen=True, slots=True)
class AdapterLifecycleSnapshot:
    """Immutable lifecycle snapshot for one provider/source pair."""

    descriptor: ports.ExternalSourceDescriptor
    provider: providers.ProviderDescriptor
    state: AdapterLifecycleState
    observed_at: datetime
    last_transition: AdapterLifecycleTransition
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, ports.ExternalSourceDescriptor):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot descriptor must be "
                "ExternalSourceDescriptor"
            )
        if not isinstance(self.provider, providers.ProviderDescriptor):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot provider must be ProviderDescriptor"
            )
        if not isinstance(self.state, AdapterLifecycleState):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot state must be AdapterLifecycleState"
            )
        _validate_explicit_datetime(self.observed_at, field_name="observed_at")
        if not isinstance(self.last_transition, AdapterLifecycleTransition):
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot last_transition must be "
                "AdapterLifecycleTransition"
            )
        if self.last_transition.descriptor != self.descriptor:
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot descriptor must match transition"
            )
        if self.last_transition.provider != self.provider:
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot provider must match transition"
            )
        if self.last_transition.to_state is not self.state:
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot state must match transition target"
            )
        if self.last_transition.transitioned_at > self.observed_at:
            raise AdapterLifecycleValidationError(
                "adapter lifecycle snapshot observed_at must be at or after transition"
            )
        object.__setattr__(
            self,
            "metadata",
            _validate_lifecycle_metadata(self.metadata, field_name="metadata"),
        )

    @property
    def is_active(self) -> bool:
        """Return whether the lifecycle is externally active."""
        return self.state in {
            AdapterLifecycleState.STARTED,
            AdapterLifecycleState.DEGRADED,
        }

    @property
    def is_terminal_failure(self) -> bool:
        """Return whether the lifecycle has entered failed state."""
        return self.state is AdapterLifecycleState.FAILED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.descriptor.logical_values(),
            self.provider.logical_values(),
            self.state.value,
            self.observed_at.isoformat(),
            self.last_transition.logical_values(),
            tuple(self.metadata.items()),
        )


class AdapterLifecycleBoundary(Protocol):
    """Structural boundary exposing external adapter lifecycle state."""

    @property
    def descriptor(self) -> ports.ExternalSourceDescriptor:
        """Expose the explicit adapter/source descriptor."""
        ...

    @property
    def provider_descriptor(self) -> providers.ProviderDescriptor:
        """Expose immutable provider governance state."""
        ...

    def lifecycle_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[
        AdapterLifecycleSnapshot,
        AdapterLifecycleError,
    ]:
        """Return a lifecycle snapshot without mutating Core RuntimePlan."""
        ...


def declare_adapter_lifecycle(
    *,
    descriptor: ports.ExternalSourceDescriptor,
    provider: providers.ProviderDescriptor,
    declared_at: datetime,
    actor: AdapterLifecycleActor,
    metadata: ports.ExternalRequestMetadata,
    snapshot_metadata: Mapping[str, DomainMetadataValue] | None = None,
) -> result_contract.Result[AdapterLifecycleSnapshot, AdapterLifecycleError]:
    """Create the initial declared lifecycle snapshot with explicit time and actor."""
    try:
        transition = AdapterLifecycleTransition(
            descriptor=descriptor,
            provider=provider,
            from_state=AdapterLifecycleState.DECLARED,
            to_state=AdapterLifecycleState.DECLARED,
            reason=AdapterLifecycleTransitionReason.DECLARED,
            transitioned_at=declared_at,
            actor=actor,
            metadata=metadata,
        )
        snapshot = AdapterLifecycleSnapshot(
            descriptor=descriptor,
            provider=provider,
            state=AdapterLifecycleState.DECLARED,
            observed_at=declared_at,
            last_transition=transition,
            metadata=snapshot_metadata or MappingProxyType({}),
        )
    except AdapterLifecycleError as error:
        return result_contract.Failure(error)
    return result_contract.Success(snapshot)


def apply_adapter_lifecycle_transition(
    snapshot: AdapterLifecycleSnapshot,
    request: AdapterLifecycleTransitionRequest,
) -> result_contract.Result[AdapterLifecycleSnapshot, AdapterLifecycleError]:
    """Apply one deterministic lifecycle transition to an immutable snapshot."""
    if not isinstance(snapshot, AdapterLifecycleSnapshot):
        return result_contract.Failure(
            AdapterLifecycleValidationError(
                "adapter lifecycle snapshot must be AdapterLifecycleSnapshot"
            )
        )
    if not isinstance(request, AdapterLifecycleTransitionRequest):
        return result_contract.Failure(
            AdapterLifecycleValidationError(
                "adapter lifecycle request must be AdapterLifecycleTransitionRequest"
            )
        )
    try:
        transition = AdapterLifecycleTransition(
            descriptor=snapshot.descriptor,
            provider=snapshot.provider,
            from_state=snapshot.state,
            to_state=request.to_state,
            reason=request.reason,
            transitioned_at=request.transitioned_at,
            actor=request.actor,
            metadata=request.metadata,
            message=request.message,
        )
        next_snapshot = AdapterLifecycleSnapshot(
            descriptor=snapshot.descriptor,
            provider=snapshot.provider,
            state=request.to_state,
            observed_at=request.transitioned_at,
            last_transition=transition,
            metadata=snapshot.metadata,
        )
    except AdapterLifecycleError as error:
        return result_contract.Failure(error)
    return result_contract.Success(next_snapshot)
