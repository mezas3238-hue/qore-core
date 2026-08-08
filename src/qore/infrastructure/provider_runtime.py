from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from re import fullmatch
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

import qore.infrastructure.activation_policy as activation_policy
import qore.infrastructure.ports as ports
import qore.infrastructure.providers as providers
import qore.kernel.result as result_contract
from qore.domain.events import DomainMetadataValue

_RESERVED_RUNTIME_METADATA_KEYS = frozenset(
    {
        "adapter_id",
        "component_id",
        "component_kind",
        "dependency",
        "dependencies",
        "order",
        "provider_id",
        "secret",
        "secret_value",
        "source_id",
        "token",
        "value",
    }
)
_SENSITIVE_RUNTIME_KEY_PARTS = frozenset(
    {"api-key", "api_key", "credential", "password", "secret", "token"}
)
_SENSITIVE_RUNTIME_TEXT_PARTS = frozenset(
    {
        "-----begin",
        "api_key=",
        "authorization:",
        "bearer ",
        "client_secret=",
        "ghp_",
        "github_pat_",
        "password=",
        "secret=",
        "sk-",
        "token=",
        "xox",
    }
)


class ProviderRuntimePlanError(ports.ExternalPortError):
    """Base error for external provider runtime plan contracts."""

    __slots__ = ()


class ProviderRuntimePlanValidationError(ProviderRuntimePlanError):
    """Violation of an external provider runtime plan invariant."""

    __slots__ = ()


class ProviderRuntimePlanDependencyError(ProviderRuntimePlanError):
    """Typed error for invalid external runtime dependencies."""

    __slots__ = ()

    def __init__(self, message: str) -> None:
        if not isinstance(message, str) or not message.strip():
            raise ProviderRuntimePlanValidationError(
                "provider runtime dependency error message must be non-empty"
            )
        super().__init__(message)


class ProviderRuntimePlanCycleError(ProviderRuntimePlanDependencyError):
    """Typed error for cyclic external runtime dependencies."""

    __slots__ = ()

    def __init__(self, cycle: tuple[ExternalRuntimeComponentId, ...]) -> None:
        if not isinstance(cycle, tuple) or not cycle:
            raise ProviderRuntimePlanValidationError(
                "provider runtime dependency cycle must be a non-empty tuple"
            )
        for component_id in cycle:
            if not isinstance(component_id, ExternalRuntimeComponentId):
                raise ProviderRuntimePlanValidationError(
                    "provider runtime dependency cycle entries must be "
                    "ExternalRuntimeComponentId"
                )
        rendered = " -> ".join(component_id.value for component_id in cycle)
        super().__init__(f"external runtime dependency cycle detected: {rendered}")


def _validate_public_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProviderRuntimePlanValidationError(f"{field_name} must be non-empty")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_RUNTIME_TEXT_PARTS):
        raise ProviderRuntimePlanValidationError(
            f"{field_name} must not contain sensitive payloads"
        )


def _validate_metadata_value(value: object) -> None:
    if value is None or isinstance(value, (bool, int, UUID)):
        return
    if isinstance(value, str):
        _validate_public_text(value, field_name="provider runtime metadata value")
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ProviderRuntimePlanValidationError(
                "provider runtime metadata floats must be finite"
            )
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_metadata_value(item)
        return
    raise ProviderRuntimePlanValidationError(
        "provider runtime metadata values must be immutable scalars or tuples"
    )


def _validate_metadata(
    values: Mapping[str, DomainMetadataValue],
) -> MappingProxyType[str, DomainMetadataValue]:
    if not isinstance(values, Mapping):
        raise ProviderRuntimePlanValidationError(
            "provider runtime metadata must be a mapping"
        )
    for key, value in values.items():
        if not isinstance(key, str) or fullmatch(r"[a-z][a-z0-9._-]*", key) is None:
            raise ProviderRuntimePlanValidationError(
                "provider runtime metadata keys must use lowercase letters, "
                "digits, dots, underscores, or hyphens"
            )
        if key in _RESERVED_RUNTIME_METADATA_KEYS:
            raise ProviderRuntimePlanValidationError(
                f"reserved provider runtime metadata key: {key}"
            )
        if any(part in key for part in _SENSITIVE_RUNTIME_KEY_PARTS):
            raise ProviderRuntimePlanValidationError(
                "provider runtime metadata must not contain secret-like keys"
            )
        _validate_metadata_value(value)
    return MappingProxyType({key: values[key] for key in sorted(values)})


@dataclass(frozen=True, slots=True)
class ExternalRuntimeComponentId:
    """Stable declarative identity for one external runtime component."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._-]*",
            self.value,
        ) is None:
            raise ProviderRuntimePlanValidationError(
                "external runtime component id must use lowercase letters, digits, "
                "dots, underscores, or hyphens"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExternalRuntimeComponentKind(StrEnum):
    """Closed external runtime component kinds; none are Core components."""

    PROVIDER_ADAPTER = "provider_adapter"
    MARKET_DATA_HARNESS = "market_data_harness"
    PERSISTENCE_HARNESS = "persistence_harness"
    HEALTH_SUPERVISOR = "health_supervisor"


@dataclass(frozen=True, slots=True)
class ExternalProviderRuntimeComponent:
    """Declarative external component planned outside the Core RuntimePlan."""

    component_id: ExternalRuntimeComponentId
    component_kind: ExternalRuntimeComponentKind
    provider: providers.ProviderDescriptor
    source: ports.ExternalSourceDescriptor
    activation_policy: activation_policy.ProviderActivationPolicy
    depends_on: tuple[ExternalRuntimeComponentId, ...] = ()
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.component_id, ExternalRuntimeComponentId):
            raise ProviderRuntimePlanValidationError(
                "external runtime component_id must be ExternalRuntimeComponentId"
            )
        if not isinstance(self.component_kind, ExternalRuntimeComponentKind):
            raise ProviderRuntimePlanValidationError(
                "external runtime component_kind must be ExternalRuntimeComponentKind"
            )
        if not isinstance(self.provider, providers.ProviderDescriptor):
            raise ProviderRuntimePlanValidationError(
                "external runtime provider must be ProviderDescriptor"
            )
        if not isinstance(self.source, ports.ExternalSourceDescriptor):
            raise ProviderRuntimePlanValidationError(
                "external runtime source must be ExternalSourceDescriptor"
            )
        if not isinstance(
            self.activation_policy,
            activation_policy.ProviderActivationPolicy,
        ):
            raise ProviderRuntimePlanValidationError(
                "external runtime activation_policy must be ProviderActivationPolicy"
            )
        if self.activation_policy.provider != self.provider:
            raise ProviderRuntimePlanValidationError(
                "external runtime activation policy provider must match component"
            )
        if self.activation_policy.source != self.source:
            raise ProviderRuntimePlanValidationError(
                "external runtime activation policy source must match component"
            )
        if not isinstance(self.depends_on, tuple):
            raise ProviderRuntimePlanValidationError(
                "external runtime dependencies must be a tuple"
            )
        seen: set[ExternalRuntimeComponentId] = set()
        for dependency in self.depends_on:
            if not isinstance(dependency, ExternalRuntimeComponentId):
                raise ProviderRuntimePlanValidationError(
                    "external runtime dependency entries must be "
                    "ExternalRuntimeComponentId"
                )
            if dependency == self.component_id:
                raise ProviderRuntimePlanDependencyError(
                    "external runtime component must not depend on itself"
                )
            if dependency in seen:
                raise ProviderRuntimePlanDependencyError(
                    "external runtime dependencies must not contain duplicates"
                )
            seen.add(dependency)
        object.__setattr__(
            self,
            "depends_on",
            tuple(sorted(self.depends_on, key=lambda item: item.value)),
        )
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.component_id.logical_values(),
            self.component_kind.value,
            self.provider.logical_values(),
            self.source.logical_values(),
            self.activation_policy.logical_values(),
            tuple(dependency.logical_values() for dependency in self.depends_on),
            tuple(self.metadata.items()),
        )


def _ordered_components(
    components: tuple[ExternalProviderRuntimeComponent, ...],
) -> tuple[ExternalProviderRuntimeComponent, ...]:
    components_by_id: dict[
        ExternalRuntimeComponentId,
        ExternalProviderRuntimeComponent,
    ] = {}
    for component in components:
        if component.component_id in components_by_id:
            raise ProviderRuntimePlanDependencyError(
                "external runtime plan component ids must be unique"
            )
        components_by_id[component.component_id] = component

    for component in components:
        for dependency in component.depends_on:
            if dependency not in components_by_id:
                raise ProviderRuntimePlanDependencyError(
                    "external runtime dependency must reference a known component: "
                    f"{dependency.value}"
                )

    visiting: set[ExternalRuntimeComponentId] = set()
    visited: set[ExternalRuntimeComponentId] = set()
    ordered: list[ExternalProviderRuntimeComponent] = []

    def visit(
        component_id: ExternalRuntimeComponentId,
        path: tuple[ExternalRuntimeComponentId, ...],
    ) -> None:
        if component_id in visited:
            return
        if component_id in visiting:
            raise ProviderRuntimePlanCycleError(path + (component_id,))
        visiting.add(component_id)
        component = components_by_id[component_id]
        for dependency in component.depends_on:
            visit(dependency, path + (component_id,))
        visiting.remove(component_id)
        visited.add(component_id)
        ordered.append(component)

    for component_id in sorted(components_by_id, key=lambda item: item.value):
        visit(component_id, ())

    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class ExternalProviderRuntimePlan:
    """Declarative external runtime plan, separate from the Core RuntimePlan."""

    components: tuple[ExternalProviderRuntimeComponent, ...] = ()
    metadata: Mapping[str, DomainMetadataValue] = field(
        default_factory=lambda: MappingProxyType({}),
        compare=True,
        hash=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.components, tuple):
            raise ProviderRuntimePlanValidationError(
                "external runtime plan components must be a tuple"
            )
        for component in self.components:
            if not isinstance(component, ExternalProviderRuntimeComponent):
                raise ProviderRuntimePlanValidationError(
                    "external runtime plan components must contain "
                    "ExternalProviderRuntimeComponent"
                )
        object.__setattr__(self, "components", _ordered_components(self.components))
        object.__setattr__(self, "metadata", _validate_metadata(self.metadata))

    @property
    def activation_order(self) -> tuple[ExternalRuntimeComponentId, ...]:
        """Return stable dependency-first activation order."""
        return tuple(component.component_id for component in self.components)

    def component_for(
        self,
        component_id: ExternalRuntimeComponentId,
    ) -> ExternalProviderRuntimeComponent:
        """Return a component by id, or fail with a typed validation error."""
        if not isinstance(component_id, ExternalRuntimeComponentId):
            raise ProviderRuntimePlanValidationError(
                "external runtime component lookup id must be "
                "ExternalRuntimeComponentId"
            )
        for component in self.components:
            if component.component_id == component_id:
                return component
        raise ProviderRuntimePlanDependencyError(
            f"external runtime component not found: {component_id.value}"
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            tuple(component.logical_values() for component in self.components),
            tuple(self.metadata.items()),
        )


class ExternalProviderRuntimePlanBoundary(Protocol):
    """Structural boundary exposing an external plan without Core registration."""

    @property
    def external_runtime_plan(self) -> ExternalProviderRuntimePlan:
        """Expose the immutable provider runtime plan."""
        ...


def build_external_provider_runtime_plan(
    *,
    components: tuple[ExternalProviderRuntimeComponent, ...],
    metadata: Mapping[str, DomainMetadataValue] | None = None,
) -> result_contract.Result[ExternalProviderRuntimePlan, ProviderRuntimePlanError]:
    """Build a deterministic external runtime plan without Core side effects."""
    try:
        return result_contract.Success(
            ExternalProviderRuntimePlan(
                components=components,
                metadata=metadata or MappingProxyType({}),
            )
        )
    except ProviderRuntimePlanError as error:
        return result_contract.Failure(error)
