from __future__ import annotations

from dataclasses import dataclass

from qore.core.application import CoreApplication
from qore.infrastructure.adapter_resilience import AdapterResilienceSnapshot
from qore.infrastructure.connectivity import (
    ProviderConnectionState,
    ProviderConnectivitySnapshot,
)
from qore.infrastructure.connectivity_observability import (
    ConnectivityObservation,
    observe_live_connectivity,
)
from qore.infrastructure.live_market_data import ControlledLiveMarketDataFlow
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.provider_runtime import ExternalProviderRuntimePlan
from qore.kernel.result import Failure, Result, Success


class SupervisedLiveRuntimeError(ExternalPortError):
    """Base error for read-only live runtime composition."""

    __slots__ = ()


class SupervisedLiveRuntimeValidationError(SupervisedLiveRuntimeError):
    """Violation of a supervised live runtime invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class SupervisedLiveRuntimeConfiguration:
    """Explicit PHASE-09 live inputs kept outside the Core object graph."""

    external_runtime_plan: ExternalProviderRuntimePlan
    market_data: ControlledLiveMarketDataFlow
    connectivity: ProviderConnectivitySnapshot
    resilience: AdapterResilienceSnapshot
    latency_milliseconds: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.external_runtime_plan, ExternalProviderRuntimePlan):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime external_runtime_plan must be ExternalProviderRuntimePlan"
            )
        if not isinstance(self.market_data, ControlledLiveMarketDataFlow):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime market_data must be ControlledLiveMarketDataFlow"
            )
        if not isinstance(self.connectivity, ProviderConnectivitySnapshot):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime connectivity must be ProviderConnectivitySnapshot"
            )
        if not isinstance(self.resilience, AdapterResilienceSnapshot):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime resilience must be AdapterResilienceSnapshot"
            )
        if self.latency_milliseconds is not None and (
            type(self.latency_milliseconds) is not int
            or self.latency_milliseconds < 0
        ):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime latency_milliseconds must be a non-negative int or None"
            )
        provider = self.market_data.payload_adapter.provider.configuration.connectivity.provider
        source = self.market_data.descriptor
        if self.connectivity.intent.provider != provider:
            raise SupervisedLiveRuntimeValidationError(
                "live runtime connectivity provider must match market-data provider"
            )
        if self.connectivity.intent.endpoint != (
            self.market_data.payload_adapter.provider.configuration.connectivity.endpoint
        ):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime connectivity endpoint must match market-data provider"
            )
        if self.resilience.policy.provider != provider:
            raise SupervisedLiveRuntimeValidationError(
                "live runtime resilience provider must match market-data provider"
            )
        if self.resilience.policy.source != source:
            raise SupervisedLiveRuntimeValidationError(
                "live runtime resilience source must match market-data source"
            )
        matching_components = tuple(
            component
            for component in self.external_runtime_plan.components
            if component.provider == provider and component.source == source
        )
        if not matching_components:
            raise SupervisedLiveRuntimeValidationError(
                "live runtime external plan must contain the market-data provider/source"
            )


@dataclass(frozen=True, slots=True)
class SupervisedLiveRuntimeComposition:
    """Read-only live provider composition explicitly above an unchanged Core."""

    core: CoreApplication
    configuration: SupervisedLiveRuntimeConfiguration

    def __post_init__(self) -> None:
        if not isinstance(self.core, CoreApplication):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime core must be CoreApplication"
            )
        if not isinstance(self.configuration, SupervisedLiveRuntimeConfiguration):
            raise SupervisedLiveRuntimeValidationError(
                "live runtime configuration must be SupervisedLiveRuntimeConfiguration"
            )

    @property
    def external_runtime_plan(self) -> ExternalProviderRuntimePlan:
        return self.configuration.external_runtime_plan

    @property
    def market_data(self) -> ControlledLiveMarketDataFlow | None:
        """Expose canonical live market data only when connectivity is READY."""
        if self.configuration.connectivity.state is not ProviderConnectionState.READY:
            return None
        if not self.configuration.market_data.payload_adapter.provider.configuration.activation.can_activate:
            return None
        return self.configuration.market_data

    def observability(self):  # noqa: ANN201
        """Build sanitized connectivity observability without a backend side effect."""
        provider = self.configuration.connectivity.intent.provider
        return observe_live_connectivity(
            provider,
            ConnectivityObservation(
                connectivity=self.configuration.connectivity,
                source=self.configuration.market_data.descriptor,
                latency_milliseconds=self.configuration.latency_milliseconds,
            ),
            observed_at=self.configuration.connectivity.observed_at,
        )


def compose_supervised_live_runtime(
    core: CoreApplication,
    configuration: SupervisedLiveRuntimeConfiguration,
) -> Result[SupervisedLiveRuntimeComposition, ExternalPortError]:
    """Compose read-only live infrastructure while proving the Core is untouched."""
    if not isinstance(core, CoreApplication):
        return Failure(SupervisedLiveRuntimeValidationError("core must be CoreApplication"))
    if not isinstance(configuration, SupervisedLiveRuntimeConfiguration):
        return Failure(
            SupervisedLiveRuntimeValidationError(
                "configuration must be SupervisedLiveRuntimeConfiguration"
            )
        )

    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    try:
        composition = SupervisedLiveRuntimeComposition(
            core=core,
            configuration=configuration,
        )
    except ExternalPortError as error:
        return Failure(error)

    if core.event_bus is not event_bus:
        return Failure(
            SupervisedLiveRuntimeValidationError(
                "live runtime must preserve the Core EventBus"
            )
        )
    if core.runtime_plan != runtime_plan:
        return Failure(
            SupervisedLiveRuntimeValidationError(
                "live runtime must not mutate the Core RuntimePlan"
            )
        )
    if core.runtime_snapshot() != runtime_snapshot:
        return Failure(
            SupervisedLiveRuntimeValidationError(
                "live runtime must not mutate the Core RuntimeSnapshot"
            )
        )
    if core.runtime_health() != runtime_health:
        return Failure(
            SupervisedLiveRuntimeValidationError(
                "live runtime must not mutate the Core RuntimeHealth"
            )
        )
    return Success(composition)
