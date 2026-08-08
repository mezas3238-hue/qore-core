from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.infrastructure.adapter_lifecycle import (
    AdapterLifecycleActor,
    AdapterLifecycleBoundary,
    AdapterLifecycleError,
    AdapterLifecycleInvalidTransitionError,
    AdapterLifecycleSnapshot,
    AdapterLifecycleState,
    AdapterLifecycleTransition,
    AdapterLifecycleTransitionReason,
    AdapterLifecycleTransitionRequest,
    AdapterLifecycleValidationError,
    apply_adapter_lifecycle_transition,
    declare_adapter_lifecycle,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 2, 0, tzinfo=UTC)
_LATER = _NOW + timedelta(minutes=1)
_PROVIDER_ID = ProviderId(UUID("f9000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("f9000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("f9000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("f9000000-0000-0000-0000-000000000004"))
_CAUSATION_ID = CausationId(UUID("f9000000-0000-0000-0000-000000000005"))


def _descriptor() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_SOURCE_ID,
        port_name=PortName("market-data.lifecycle"),
    )


def _provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference.lifecycle"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.HEALTH,
                ProviderCapability.MARKET_DATA_READ,
            )
        ),
    )


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION_ID,
        causation_id=_CAUSATION_ID,
        attributes={"workflow": "phase-08"},
    )


def _actor() -> AdapterLifecycleActor:
    return AdapterLifecycleActor("ceo.supervisor")


def _declared() -> AdapterLifecycleSnapshot:
    result = declare_adapter_lifecycle(
        descriptor=_descriptor(),
        provider=_provider(),
        declared_at=_NOW,
        actor=_actor(),
        metadata=_metadata(),
        snapshot_metadata={"source": "test"},
    )
    assert isinstance(result, Success)
    return result.value


def _request(
    to_state: AdapterLifecycleState,
    reason: AdapterLifecycleTransitionReason,
    *,
    transitioned_at: datetime = _LATER,
    message: str | None = None,
) -> AdapterLifecycleTransitionRequest:
    return AdapterLifecycleTransitionRequest(
        to_state=to_state,
        reason=reason,
        transitioned_at=transitioned_at,
        actor=_actor(),
        metadata=_metadata(),
        message=message,
    )


def _apply(
    snapshot: AdapterLifecycleSnapshot,
    to_state: AdapterLifecycleState,
    reason: AdapterLifecycleTransitionReason,
    *,
    minutes: int,
    message: str | None = None,
) -> AdapterLifecycleSnapshot:
    result = apply_adapter_lifecycle_transition(
        snapshot,
        _request(
            to_state,
            reason,
            transitioned_at=_NOW + timedelta(minutes=minutes),
            message=message,
        ),
    )
    assert isinstance(result, Success)
    return result.value


def test_adapter_lifecycle_declares_initial_snapshot_explicitly() -> None:
    snapshot = _declared()

    assert snapshot.descriptor == _descriptor()
    assert snapshot.provider == _provider()
    assert snapshot.state is AdapterLifecycleState.DECLARED
    assert snapshot.observed_at == _NOW
    assert snapshot.last_transition.from_state is AdapterLifecycleState.DECLARED
    assert snapshot.last_transition.to_state is AdapterLifecycleState.DECLARED
    assert snapshot.last_transition.reason is AdapterLifecycleTransitionReason.DECLARED
    assert snapshot.last_transition.actor == _actor()
    assert snapshot.last_transition.metadata == _metadata()
    assert snapshot.metadata["source"] == "test"
    assert not snapshot.is_active
    assert not snapshot.is_terminal_failure
    assert snapshot.logical_values() == _declared().logical_values()


def test_adapter_lifecycle_applies_valid_deterministic_transitions() -> None:
    declared = _declared()
    configured = _apply(
        declared,
        AdapterLifecycleState.CONFIGURED,
        AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
        minutes=1,
    )
    initialized = _apply(
        configured,
        AdapterLifecycleState.INITIALIZED,
        AdapterLifecycleTransitionReason.INITIALIZE_REQUESTED,
        minutes=2,
    )
    started = _apply(
        initialized,
        AdapterLifecycleState.STARTED,
        AdapterLifecycleTransitionReason.START_REQUESTED,
        minutes=3,
    )
    degraded = _apply(
        started,
        AdapterLifecycleState.DEGRADED,
        AdapterLifecycleTransitionReason.DEGRADED_HEALTH,
        minutes=4,
        message="provider latency degraded",
    )
    recovered = _apply(
        degraded,
        AdapterLifecycleState.STARTED,
        AdapterLifecycleTransitionReason.RECOVERY_CONFIRMED,
        minutes=5,
    )
    stopped = _apply(
        recovered,
        AdapterLifecycleState.STOPPED,
        AdapterLifecycleTransitionReason.STOP_REQUESTED,
        minutes=6,
    )

    assert declared.state is AdapterLifecycleState.DECLARED
    assert configured.last_transition.from_state is AdapterLifecycleState.DECLARED
    assert configured.last_transition.to_state is AdapterLifecycleState.CONFIGURED
    assert started.is_active
    assert degraded.is_active
    assert degraded.last_transition.message == "provider latency degraded"
    assert recovered.state is AdapterLifecycleState.STARTED
    assert stopped.state is AdapterLifecycleState.STOPPED
    assert not stopped.is_active
    assert stopped.metadata["source"] == "test"


def test_adapter_lifecycle_rejects_invalid_transition() -> None:
    result: Result[AdapterLifecycleSnapshot, AdapterLifecycleError] = (
        apply_adapter_lifecycle_transition(
            _declared(),
            _request(
                AdapterLifecycleState.STARTED,
                AdapterLifecycleTransitionReason.START_REQUESTED,
            ),
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterLifecycleInvalidTransitionError)
    assert "declared -> started" in str(result.error)


def test_adapter_lifecycle_rejects_reason_target_mismatch() -> None:
    result: Result[AdapterLifecycleSnapshot, AdapterLifecycleError] = (
        apply_adapter_lifecycle_transition(
            _declared(),
            _request(
                AdapterLifecycleState.CONFIGURED,
                AdapterLifecycleTransitionReason.START_REQUESTED,
            ),
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterLifecycleInvalidTransitionError)
    assert "start_requested" in str(result.error)


def test_adapter_lifecycle_requires_messages_for_degraded_and_failed() -> None:
    configured = _apply(
        _declared(),
        AdapterLifecycleState.CONFIGURED,
        AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
        minutes=1,
    )
    failed_result = apply_adapter_lifecycle_transition(
        configured,
        _request(
            AdapterLifecycleState.FAILED,
            AdapterLifecycleTransitionReason.FAILURE_DETECTED,
            transitioned_at=_NOW + timedelta(minutes=2),
        ),
    )

    assert isinstance(failed_result, Failure)
    assert isinstance(failed_result.error, AdapterLifecycleValidationError)
    assert "require a message" in str(failed_result.error)


def test_adapter_lifecycle_requires_causation_and_timezone_aware_time() -> None:
    missing_causation = ExternalRequestMetadata(correlation_id=_CORRELATION_ID)
    declared = declare_adapter_lifecycle(
        descriptor=_descriptor(),
        provider=_provider(),
        declared_at=_NOW,
        actor=_actor(),
        metadata=missing_causation,
    )

    assert isinstance(declared, Failure)
    assert isinstance(declared.error, AdapterLifecycleValidationError)
    assert "causation_id is required" in str(declared.error)
    with pytest.raises(AdapterLifecycleValidationError, match="timezone-aware"):
        AdapterLifecycleTransitionRequest(
            to_state=AdapterLifecycleState.CONFIGURED,
            reason=AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
            transitioned_at=datetime(2026, 8, 8, 2, 0),
            actor=_actor(),
            metadata=_metadata(),
        )


def test_adapter_lifecycle_rejects_runtime_bypasses() -> None:
    invalid_snapshot: Result[AdapterLifecycleSnapshot, AdapterLifecycleError] = (
        apply_adapter_lifecycle_transition(
            cast(AdapterLifecycleSnapshot, object()),
            _request(
                AdapterLifecycleState.CONFIGURED,
                AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
            ),
        )
    )
    invalid_request: Result[AdapterLifecycleSnapshot, AdapterLifecycleError] = (
        apply_adapter_lifecycle_transition(
            _declared(),
            cast(AdapterLifecycleTransitionRequest, object()),
        )
    )

    assert isinstance(invalid_snapshot, Failure)
    assert isinstance(invalid_snapshot.error, AdapterLifecycleValidationError)
    assert isinstance(invalid_request, Failure)
    assert isinstance(invalid_request.error, AdapterLifecycleValidationError)
    with pytest.raises(AdapterLifecycleValidationError):
        AdapterLifecycleActor("CEO Supervisor")
    with pytest.raises(AdapterLifecycleValidationError):
        AdapterLifecycleTransition(
            descriptor=cast(ExternalSourceDescriptor, object()),
            provider=_provider(),
            from_state=AdapterLifecycleState.DECLARED,
            to_state=AdapterLifecycleState.DECLARED,
            reason=AdapterLifecycleTransitionReason.DECLARED,
            transitioned_at=_NOW,
            actor=_actor(),
            metadata=_metadata(),
        )


def test_adapter_lifecycle_validates_snapshot_invariants_and_metadata() -> None:
    snapshot = _declared()
    wrong_transition = AdapterLifecycleTransition(
        descriptor=_descriptor(),
        provider=_provider(),
        from_state=AdapterLifecycleState.DECLARED,
        to_state=AdapterLifecycleState.CONFIGURED,
        reason=AdapterLifecycleTransitionReason.CONFIGURATION_ACCEPTED,
        transitioned_at=_LATER,
        actor=_actor(),
        metadata=_metadata(),
    )

    with pytest.raises(AdapterLifecycleValidationError, match="state must match"):
        AdapterLifecycleSnapshot(
            descriptor=_descriptor(),
            provider=_provider(),
            state=AdapterLifecycleState.DECLARED,
            observed_at=_LATER,
            last_transition=wrong_transition,
        )
    with pytest.raises(AdapterLifecycleValidationError, match="reserved"):
        AdapterLifecycleSnapshot(
            descriptor=snapshot.descriptor,
            provider=snapshot.provider,
            state=snapshot.state,
            observed_at=snapshot.observed_at,
            last_transition=snapshot.last_transition,
            metadata={"state": "hidden"},
        )
    with pytest.raises(AdapterLifecycleValidationError, match="immutable"):
        AdapterLifecycleSnapshot(
            descriptor=snapshot.descriptor,
            provider=snapshot.provider,
            state=snapshot.state,
            observed_at=snapshot.observed_at,
            last_transition=snapshot.last_transition,
            metadata={"bad": cast(DomainMetadataValue, object())},
        )


def test_adapter_lifecycle_boundary_protocol_is_structural() -> None:
    class Harness:
        @property
        def descriptor(self) -> ExternalSourceDescriptor:
            return _descriptor()

        @property
        def provider_descriptor(self) -> ProviderDescriptor:
            return _provider()

        def lifecycle_snapshot(
            self,
            *,
            observed_at: datetime,
            metadata: ExternalRequestMetadata,
        ) -> Result[AdapterLifecycleSnapshot, AdapterLifecycleError]:
            return declare_adapter_lifecycle(
                descriptor=self.descriptor,
                provider=self.provider_descriptor,
                declared_at=observed_at,
                actor=_actor(),
                metadata=metadata,
            )

    boundary: AdapterLifecycleBoundary = Harness()
    result = boundary.lifecycle_snapshot(observed_at=_NOW, metadata=_metadata())

    assert isinstance(result, Success)
    assert result.value.descriptor == _descriptor()
    assert result.value.provider == _provider()


def test_adapter_lifecycle_public_exports() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.AdapterLifecycleActor is AdapterLifecycleActor
    assert infrastructure.AdapterLifecycleBoundary is AdapterLifecycleBoundary
    assert infrastructure.AdapterLifecycleError is AdapterLifecycleError
    assert (
        infrastructure.AdapterLifecycleInvalidTransitionError
        is AdapterLifecycleInvalidTransitionError
    )
    assert infrastructure.AdapterLifecycleSnapshot is AdapterLifecycleSnapshot
    assert infrastructure.AdapterLifecycleState is AdapterLifecycleState
    assert infrastructure.AdapterLifecycleTransition is AdapterLifecycleTransition
    assert (
        infrastructure.AdapterLifecycleTransitionReason
        is AdapterLifecycleTransitionReason
    )
    assert (
        infrastructure.AdapterLifecycleTransitionRequest
        is AdapterLifecycleTransitionRequest
    )
    assert infrastructure.AdapterLifecycleValidationError is AdapterLifecycleValidationError
    assert infrastructure.apply_adapter_lifecycle_transition is (
        apply_adapter_lifecycle_transition
    )
    assert infrastructure.declare_adapter_lifecycle is declare_adapter_lifecycle
    assert issubclass(AdapterLifecycleError, ExternalPortError)
