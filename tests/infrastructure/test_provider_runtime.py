from __future__ import annotations

from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure as infrastructure
from qore.infrastructure.activation_policy import (
    ProviderActivationMode,
    ProviderActivationPolicy,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.provider_runtime import (
    ExternalProviderRuntimeComponent,
    ExternalProviderRuntimePlan,
    ExternalProviderRuntimePlanBoundary,
    ExternalRuntimeComponentId,
    ExternalRuntimeComponentKind,
    ProviderRuntimePlanCycleError,
    ProviderRuntimePlanDependencyError,
    ProviderRuntimePlanError,
    ProviderRuntimePlanValidationError,
    build_external_provider_runtime_plan,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.kernel.result import Failure, Success

_PROVIDER_ID = ProviderId(UUID("b8000000-0000-0000-0000-000000000001"))
_HEALTH_ADAPTER_ID = AdapterId(UUID("b8000000-0000-0000-0000-000000000002"))
_HEALTH_SOURCE_ID = SourceId(UUID("b8000000-0000-0000-0000-000000000003"))
_MARKET_ADAPTER_ID = AdapterId(UUID("b8000000-0000-0000-0000-000000000004"))
_MARKET_SOURCE_ID = SourceId(UUID("b8000000-0000-0000-0000-000000000005"))


def _provider(
    *,
    provider_id: ProviderId = _PROVIDER_ID,
    capabilities: tuple[ProviderCapability, ...] = (
        ProviderCapability.HEALTH,
        ProviderCapability.MARKET_DATA_READ,
    ),
) -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        provider_name=ProviderName("runtime-provider"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(capabilities),
    )


def _source(
    *,
    adapter_id: AdapterId = _MARKET_ADAPTER_ID,
    source_id: SourceId = _MARKET_SOURCE_ID,
    port_name: str = "market-data.runtime-plan",
) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=adapter_id,
        source_id=source_id,
        port_name=PortName(port_name),
    )


def _policy(
    *,
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    mode: ProviderActivationMode = ProviderActivationMode.READ_ONLY,
) -> ProviderActivationPolicy:
    return ProviderActivationPolicy(
        provider=provider or _provider(),
        source=source or _source(),
        mode=mode,
        required_capabilities=(ProviderCapability.MARKET_DATA_READ,),
        metadata={"purpose": "runtime-plan"},
    )


def _component(
    component_id: str,
    *,
    component_kind: ExternalRuntimeComponentKind = (
        ExternalRuntimeComponentKind.PROVIDER_ADAPTER
    ),
    provider: ProviderDescriptor | None = None,
    source: ExternalSourceDescriptor | None = None,
    policy: ProviderActivationPolicy | None = None,
    depends_on: tuple[ExternalRuntimeComponentId, ...] = (),
) -> ExternalProviderRuntimeComponent:
    resolved_provider = provider or _provider()
    resolved_source = source or _source()
    return ExternalProviderRuntimeComponent(
        component_id=ExternalRuntimeComponentId(component_id),
        component_kind=component_kind,
        provider=resolved_provider,
        source=resolved_source,
        activation_policy=policy
        or _policy(provider=resolved_provider, source=resolved_source),
        depends_on=depends_on,
        metadata={"group": "runtime"},
    )


def _health_component() -> ExternalProviderRuntimeComponent:
    provider = _provider()
    source = _source(
        adapter_id=_HEALTH_ADAPTER_ID,
        source_id=_HEALTH_SOURCE_ID,
        port_name="provider.runtime-plan",
    )
    return _component(
        "provider-health",
        component_kind=ExternalRuntimeComponentKind.HEALTH_SUPERVISOR,
        provider=provider,
        source=source,
        policy=ProviderActivationPolicy(
            provider=provider,
            source=source,
            mode=ProviderActivationMode.READ_ONLY,
            required_capabilities=(ProviderCapability.HEALTH,),
        ),
    )


def test_external_runtime_plan_orders_dependencies_first() -> None:
    health = _health_component()
    market = _component("market-data", depends_on=(health.component_id,))

    result = build_external_provider_runtime_plan(
        components=(market, health),
        metadata={"scope": "external-runtime"},
    )

    assert isinstance(result, Success)
    assert result.value.activation_order == (health.component_id, market.component_id)
    assert result.value.components == (health, market)
    assert result.value.component_for(market.component_id) == market
    assert result.value.logical_values() == result.value.logical_values()


def test_external_runtime_plan_rejects_duplicate_component_ids() -> None:
    first = _component("market-data")
    second = _component("market-data")

    result = build_external_provider_runtime_plan(components=(first, second))

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderRuntimePlanDependencyError)


def test_external_runtime_plan_rejects_unknown_dependency() -> None:
    component = _component(
        "market-data",
        depends_on=(ExternalRuntimeComponentId("missing-provider"),),
    )

    result = build_external_provider_runtime_plan(components=(component,))

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderRuntimePlanDependencyError)


def test_external_runtime_plan_rejects_cycles() -> None:
    first_id = ExternalRuntimeComponentId("first")
    second_id = ExternalRuntimeComponentId("second")
    first = _component("first", depends_on=(second_id,))
    second = _component("second", depends_on=(first_id,))

    result = build_external_provider_runtime_plan(components=(first, second))

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProviderRuntimePlanCycleError)


def test_component_rejects_self_dependency_and_duplicate_dependencies() -> None:
    component_id = ExternalRuntimeComponentId("market-data")
    with pytest.raises(ProviderRuntimePlanDependencyError):
        ExternalProviderRuntimeComponent(
            component_id=component_id,
            component_kind=ExternalRuntimeComponentKind.PROVIDER_ADAPTER,
            provider=_provider(),
            source=_source(),
            activation_policy=_policy(),
            depends_on=(component_id,),
        )

    dependency = ExternalRuntimeComponentId("provider-health")
    with pytest.raises(ProviderRuntimePlanDependencyError):
        _component("market-data", depends_on=(dependency, dependency))


def test_component_rejects_activation_policy_identity_mismatch() -> None:
    provider = _provider()
    source = _source()
    other_provider = _provider(
        provider_id=ProviderId(UUID("b8000000-0000-0000-0000-000000000006"))
    )
    policy = _policy(provider=other_provider, source=source)

    with pytest.raises(ProviderRuntimePlanValidationError):
        _component("market-data", provider=provider, source=source, policy=policy)

    other_source = _source(
        adapter_id=AdapterId(UUID("b8000000-0000-0000-0000-000000000007")),
        source_id=SourceId(UUID("b8000000-0000-0000-0000-000000000008")),
    )
    policy = _policy(provider=provider, source=other_source)

    with pytest.raises(ProviderRuntimePlanValidationError):
        _component("market-data", provider=provider, source=source, policy=policy)


def test_external_runtime_metadata_is_canonical_and_safe() -> None:
    component = _component(
        "market-data",
        depends_on=(ExternalRuntimeComponentId("provider-health"),),
    )
    assert tuple(component.metadata.items()) == (("group", "runtime"),)

    with pytest.raises(TypeError):
        cast(dict[str, object], component.metadata)["unsafe"] = "mutation"

    with pytest.raises(ProviderRuntimePlanValidationError):
        ExternalProviderRuntimeComponent(
            component_id=ExternalRuntimeComponentId("metadata-test"),
            component_kind=ExternalRuntimeComponentKind.PROVIDER_ADAPTER,
            provider=_provider(),
            source=_source(),
            activation_policy=_policy(),
            metadata={"token": "redacted"},
        )


def test_external_runtime_rejects_runtime_type_bypasses() -> None:
    with pytest.raises(ProviderRuntimePlanValidationError):
        ExternalRuntimeComponentId(cast(str, "UPPERCASE"))

    with pytest.raises(ProviderRuntimePlanValidationError):
        ExternalProviderRuntimeComponent(
            component_id=cast(ExternalRuntimeComponentId, "not-id"),
            component_kind=ExternalRuntimeComponentKind.PROVIDER_ADAPTER,
            provider=_provider(),
            source=_source(),
            activation_policy=_policy(),
        )

    with pytest.raises(ProviderRuntimePlanValidationError):
        ExternalProviderRuntimePlan(
            components=cast(tuple[ExternalProviderRuntimeComponent, ...], ["invalid"])
        )


def test_external_runtime_plan_boundary_is_structural() -> None:
    plan_result = build_external_provider_runtime_plan(
        components=(_health_component(),),
    )
    assert isinstance(plan_result, Success)

    class Boundary:
        def __init__(self, plan: ExternalProviderRuntimePlan) -> None:
            self._plan = plan

        @property
        def external_runtime_plan(self) -> ExternalProviderRuntimePlan:
            return self._plan

    boundary: ExternalProviderRuntimePlanBoundary = Boundary(plan_result.value)

    assert boundary.external_runtime_plan == plan_result.value


def test_public_exports() -> None:
    assert infrastructure.ExternalRuntimeComponentId is ExternalRuntimeComponentId
    assert infrastructure.ExternalRuntimeComponentKind is ExternalRuntimeComponentKind
    assert (
        infrastructure.ExternalProviderRuntimeComponent
        is ExternalProviderRuntimeComponent
    )
    assert infrastructure.ExternalProviderRuntimePlan is ExternalProviderRuntimePlan
    assert (
        infrastructure.ExternalProviderRuntimePlanBoundary
        is ExternalProviderRuntimePlanBoundary
    )
    assert infrastructure.ProviderRuntimePlanError is ProviderRuntimePlanError
    assert (
        infrastructure.ProviderRuntimePlanValidationError
        is ProviderRuntimePlanValidationError
    )
    assert (
        infrastructure.ProviderRuntimePlanDependencyError
        is ProviderRuntimePlanDependencyError
    )
    assert infrastructure.ProviderRuntimePlanCycleError is ProviderRuntimePlanCycleError
    assert (
        infrastructure.build_external_provider_runtime_plan
        is build_external_provider_runtime_plan
    )
