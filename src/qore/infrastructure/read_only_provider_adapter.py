from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from qore.infrastructure.activation_policy import (
    ProviderActivationDecisionSnapshot,
    ProviderActivationMode,
)
from qore.infrastructure.connectivity import (
    ProviderConnectivityMode,
    ReadOnlyProviderConnectivityIntent,
)
from qore.infrastructure.ports import (
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.infrastructure.secret_resolution import (
    SecretAuthenticatedTransportBoundary,
    SecretMaterialResolverBoundary,
    resolve_supervised_secret_material,
)
from qore.infrastructure.secrets import SecretRef
from qore.infrastructure.transport import (
    ExternalTransportBoundary,
    ExternalTransportRequest,
    ExternalTransportResponse,
)
from qore.kernel.result import Failure, Result


class ReadOnlyProviderAdapterError(ExternalPortError):
    """Base error for the controlled read-only provider adapter."""

    __slots__ = ()


class ReadOnlyProviderAdapterValidationError(ReadOnlyProviderAdapterError):
    """Violation of a read-only provider adapter invariant."""

    __slots__ = ()


class ReadOnlyProviderAdapterBlockedError(ReadOnlyProviderAdapterError):
    """Typed fail-closed result when supervision does not permit a read."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ReadOnlyProviderAdapterConfiguration:
    """Immutable binding of connectivity intent to an activation decision."""

    connectivity: ReadOnlyProviderConnectivityIntent
    activation: ProviderActivationDecisionSnapshot
    secret_ref: SecretRef | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.connectivity, ReadOnlyProviderConnectivityIntent):
            raise ReadOnlyProviderAdapterValidationError(
                "read-only adapter connectivity must be ReadOnlyProviderConnectivityIntent"
            )
        if not isinstance(self.activation, ProviderActivationDecisionSnapshot):
            raise ReadOnlyProviderAdapterValidationError(
                "read-only adapter activation must be ProviderActivationDecisionSnapshot"
            )
        if self.secret_ref is not None and not isinstance(self.secret_ref, SecretRef):
            raise ReadOnlyProviderAdapterValidationError(
                "read-only adapter secret_ref must be SecretRef or None"
            )
        if self.connectivity.mode is not ProviderConnectivityMode.NETWORK_READ_ONLY:
            raise ReadOnlyProviderAdapterValidationError(
                "read-only provider adapter requires NETWORK_READ_ONLY connectivity"
            )
        if self.activation.policy.mode is not ProviderActivationMode.READ_ONLY:
            raise ReadOnlyProviderAdapterValidationError(
                "read-only provider adapter requires READ_ONLY activation policy"
            )
        if self.activation.policy.provider != self.connectivity.provider:
            raise ReadOnlyProviderAdapterValidationError(
                "read-only provider connectivity and activation provider must match"
            )
        if self.connectivity.capability not in self.activation.policy.required_capabilities:
            raise ReadOnlyProviderAdapterValidationError(
                "activation policy must require the connectivity capability"
            )
        if self.secret_ref is not None and not self.activation.secret_references.contains(
            self.secret_ref.name
        ):
            raise ReadOnlyProviderAdapterValidationError(
                "read-only adapter secret_ref must be present in activation references"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.connectivity.logical_values(),
            self.activation.logical_values(),
            self.secret_ref.logical_values() if self.secret_ref is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ReadOnlyExternalProviderAdapter:
    """Provider-neutral supervised adapter with no write or trading method."""

    configuration: ReadOnlyProviderAdapterConfiguration
    transport: ExternalTransportBoundary | None = None
    authenticated_transport: SecretAuthenticatedTransportBoundary | None = None
    secret_resolver: SecretMaterialResolverBoundary | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, ReadOnlyProviderAdapterConfiguration):
            raise ReadOnlyProviderAdapterValidationError(
                "read-only provider adapter configuration must be explicit"
            )
        uses_secret = self.configuration.secret_ref is not None
        if uses_secret:
            if self.authenticated_transport is None or self.secret_resolver is None:
                raise ReadOnlyProviderAdapterValidationError(
                    "secret-backed read-only adapter requires authenticated transport and resolver"
                )
            if self.transport is not None:
                raise ReadOnlyProviderAdapterValidationError(
                    "secret-backed read-only adapter must not also expose plain transport"
                )
        else:
            if self.transport is None:
                raise ReadOnlyProviderAdapterValidationError(
                    "read-only adapter without secret requires plain transport"
                )
            if self.authenticated_transport is not None or self.secret_resolver is not None:
                raise ReadOnlyProviderAdapterValidationError(
                    "read-only adapter without secret must not carry secret infrastructure"
                )

    @property
    def connectivity_intent(self) -> ReadOnlyProviderConnectivityIntent:
        """Expose immutable provider connectivity identity."""
        return self.configuration.connectivity

    @property
    def source(self) -> ExternalSourceDescriptor:
        """Expose the supervised external source without duplicating identity."""
        return self.configuration.activation.policy.source

    def read(
        self,
        request: ExternalTransportRequest,
        *,
        metadata: ExternalRequestMetadata,
        resolved_at: datetime,
    ) -> Result[ExternalTransportResponse, ExternalPortError]:
        """Perform one supervised read through an injected transport boundary."""
        if not isinstance(request, ExternalTransportRequest):
            return Failure(
                ReadOnlyProviderAdapterValidationError(
                    "read-only provider request must be ExternalTransportRequest"
                )
            )
        if not isinstance(metadata, ExternalRequestMetadata):
            return Failure(
                ReadOnlyProviderAdapterValidationError(
                    "read-only provider metadata must be ExternalRequestMetadata"
                )
            )
        if request.endpoint != self.configuration.connectivity.endpoint:
            return Failure(
                ReadOnlyProviderAdapterValidationError(
                    "read-only provider request endpoint must match connectivity intent"
                )
            )
        if not self.configuration.activation.can_activate:
            return Failure(
                ReadOnlyProviderAdapterBlockedError(
                    "read-only provider activation is not allowed"
                )
            )

        secret_ref = self.configuration.secret_ref
        if secret_ref is None:
            if self.transport is None:
                return Failure(
                    ReadOnlyProviderAdapterValidationError(
                        "plain transport is unavailable"
                    )
                )
            return self.transport.execute(request, metadata=metadata)

        if self.secret_resolver is None or self.authenticated_transport is None:
            return Failure(
                ReadOnlyProviderAdapterValidationError(
                    "secret-backed adapter dependencies are unavailable"
                )
            )
        resolution = resolve_supervised_secret_material(
            self.secret_resolver,
            secret_ref,
            metadata=metadata,
            resolved_at=resolved_at,
        )
        if isinstance(resolution, Failure):
            return Failure(resolution.error)
        return self.authenticated_transport.execute_authenticated(
            request,
            secret=resolution.value.material,
            metadata=metadata,
        )


class ReadOnlyProviderAdapterBoundary(Protocol):
    """Structural read-only provider boundary without write operations."""

    @property
    def connectivity_intent(self) -> ReadOnlyProviderConnectivityIntent:
        """Expose immutable connectivity identity."""
        ...

    def read(
        self,
        request: ExternalTransportRequest,
        *,
        metadata: ExternalRequestMetadata,
        resolved_at: datetime,
    ) -> Result[ExternalTransportResponse, ExternalPortError]:
        """Perform one supervised provider read."""
        ...
