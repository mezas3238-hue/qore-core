from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.domain.departments import (
    CANONICAL_DEPARTMENT_REGISTRY,
    DepartmentDependency,
    DepartmentId,
    DepartmentInteractionMode,
    DepartmentRegistry,
)
from qore.kernel.errors import DomainError


class DepartmentContractError(DomainError):
    """Base error for constitutional cross-department contract definitions."""

    __slots__ = ()


class DepartmentContractValidationError(DepartmentContractError):
    """A cross-department contract definition violates a constitutional invariant."""

    __slots__ = ()


class DepartmentContractKind(StrEnum):
    """Closed semantic classes for cross-department contracts."""

    COMMAND = "command"
    QUERY = "query"
    EVENT = "event"
    EVIDENCE = "evidence"


CANONICAL_DEPARTMENT_COMMAND_ROUTES: tuple[DepartmentDependency, ...] = (
    DepartmentDependency(
        consumer=DepartmentId.CLIENT_EXECUTION,
        provider=DepartmentId.ORDER_EXECUTION,
        mode=DepartmentInteractionMode.SYNCHRONOUS,
    ),
    DepartmentDependency(
        consumer=DepartmentId.EXECUTIVE_CONTROL,
        provider=DepartmentId.CORE_GOVERNANCE,
        mode=DepartmentInteractionMode.SYNCHRONOUS,
    ),
)


def _command_route_values(
    routes: tuple[DepartmentDependency, ...],
) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(route.logical_values() for route in routes))


@dataclass(frozen=True, slots=True)
class DepartmentContractId:
    """Stable transport-neutral identity of one logical department contract."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*", self.value
        ) is None:
            raise DepartmentContractValidationError(
                "department contract id must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DepartmentContractVersion:
    """Explicit logical version of one department contract."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[0-9a-z][0-9a-z._-]*", self.value
        ) is None:
            raise DepartmentContractValidationError(
                "department contract version must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DepartmentContractSpec:
    """Constitutional route for one command, query, event, or evidence contract.

    ``consumer -> provider`` follows the certified FND-05 authority-dependency
    direction. For EVENT and EVIDENCE this is not a physical transport direction:
    a provider may publish material toward its consumers while remaining the owner
    of the authoritative fact/evidence consumed by them.

    This descriptor carries no business payload and grants no execution authority.
    """

    contract_id: DepartmentContractId
    version: DepartmentContractVersion
    kind: DepartmentContractKind
    consumer: DepartmentId
    provider: DepartmentId
    mode: DepartmentInteractionMode

    def __post_init__(self) -> None:
        if not isinstance(self.contract_id, DepartmentContractId):
            raise DepartmentContractValidationError(
                "contract_id must be DepartmentContractId"
            )
        if not isinstance(self.version, DepartmentContractVersion):
            raise DepartmentContractValidationError(
                "version must be DepartmentContractVersion"
            )
        if not isinstance(self.kind, DepartmentContractKind):
            raise DepartmentContractValidationError(
                "kind must be DepartmentContractKind"
            )
        if not isinstance(self.consumer, DepartmentId):
            raise DepartmentContractValidationError("consumer must be DepartmentId")
        if not isinstance(self.provider, DepartmentId):
            raise DepartmentContractValidationError("provider must be DepartmentId")
        if not isinstance(self.mode, DepartmentInteractionMode):
            raise DepartmentContractValidationError(
                "mode must be DepartmentInteractionMode"
            )
        if self.consumer is self.provider:
            raise DepartmentContractValidationError(
                "department contract consumer and provider must differ"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.contract_id.logical_values(),
            self.version.logical_values(),
            self.kind.value,
            self.consumer.value,
            self.provider.value,
            self.mode.value,
        )


@dataclass(frozen=True, slots=True)
class DepartmentContractRegistry:
    """Immutable contracts bound to canonical graph and COMMAND policy material.

    Registration proves only that a logical contract route is compatible with the
    canonical dependency graph and, for COMMAND, that its route is explicitly
    command-capable. It does not authorize an invocation, mutate source-domain
    state, select a transport, or prove message delivery.
    """

    department_registry: DepartmentRegistry
    contracts: tuple[DepartmentContractSpec, ...] = ()
    command_routes: tuple[DepartmentDependency, ...] = CANONICAL_DEPARTMENT_COMMAND_ROUTES

    def __post_init__(self) -> None:
        if not isinstance(self.department_registry, DepartmentRegistry):
            raise DepartmentContractValidationError(
                "department_registry must be DepartmentRegistry"
            )
        if (
            self.department_registry.logical_values()
            != CANONICAL_DEPARTMENT_REGISTRY.logical_values()
        ):
            raise DepartmentContractValidationError(
                "department_registry must match canonical department registry"
            )
        if not isinstance(self.command_routes, tuple):
            raise DepartmentContractValidationError("command_routes must be tuple")
        if not all(
            isinstance(route, DepartmentDependency) for route in self.command_routes
        ):
            raise DepartmentContractValidationError(
                "command_routes must contain DepartmentDependency values"
            )
        if _command_route_values(self.command_routes) != _command_route_values(
            CANONICAL_DEPARTMENT_COMMAND_ROUTES
        ):
            raise DepartmentContractValidationError(
                "command_routes must match canonical command routes"
            )
        if not isinstance(self.contracts, tuple):
            raise DepartmentContractValidationError("contracts must be tuple")
        if not all(
            isinstance(contract, DepartmentContractSpec) for contract in self.contracts
        ):
            raise DepartmentContractValidationError(
                "contracts must contain DepartmentContractSpec values"
            )

        identities = tuple(
            (contract.contract_id, contract.version) for contract in self.contracts
        )
        if len(set(identities)) != len(identities):
            raise DepartmentContractValidationError(
                "department contract id/version pairs must be unique"
            )

        profiles: dict[
            DepartmentContractId,
            tuple[
                DepartmentContractKind,
                DepartmentId,
                DepartmentId,
                DepartmentInteractionMode,
            ],
        ] = {}
        for contract in self.contracts:
            profile = (
                contract.kind,
                contract.consumer,
                contract.provider,
                contract.mode,
            )
            existing = profiles.get(contract.contract_id)
            if existing is None:
                profiles[contract.contract_id] = profile
            elif existing != profile:
                raise DepartmentContractValidationError(
                    "department contract id versions must preserve authority profile"
                )

        dependency_routes = {
            (dependency.consumer, dependency.provider, dependency.mode)
            for dependency in self.department_registry.dependencies
        }
        command_route_keys = {
            (route.consumer, route.provider, route.mode) for route in self.command_routes
        }
        for contract in self.contracts:
            route = (contract.consumer, contract.provider, contract.mode)
            if route not in dependency_routes:
                raise DepartmentContractValidationError(
                    "department contract route must exist in department dependency graph"
                )
            if (
                contract.kind is DepartmentContractKind.COMMAND
                and route not in command_route_keys
            ):
                raise DepartmentContractValidationError(
                    "command contract route must be explicitly command-capable"
                )

    def contract(
        self,
        contract_id: DepartmentContractId,
        version: DepartmentContractVersion,
    ) -> DepartmentContractSpec:
        """Return one exact registered logical contract or fail closed."""
        if not isinstance(contract_id, DepartmentContractId):
            raise DepartmentContractValidationError(
                "contract_id must be DepartmentContractId"
            )
        if not isinstance(version, DepartmentContractVersion):
            raise DepartmentContractValidationError(
                "version must be DepartmentContractVersion"
            )
        for contract in self.contracts:
            if contract.contract_id == contract_id and contract.version == version:
                return contract
        raise DepartmentContractValidationError("unknown department contract version")

    def contracts_for(
        self,
        consumer: DepartmentId,
        *,
        provider: DepartmentId | None = None,
        kind: DepartmentContractKind | None = None,
        mode: DepartmentInteractionMode | None = None,
    ) -> tuple[DepartmentContractSpec, ...]:
        """Return deterministic contracts consumed by one canonical department."""
        if not isinstance(consumer, DepartmentId):
            raise DepartmentContractValidationError("consumer must be DepartmentId")
        if provider is not None and not isinstance(provider, DepartmentId):
            raise DepartmentContractValidationError(
                "provider must be DepartmentId or None"
            )
        if kind is not None and not isinstance(kind, DepartmentContractKind):
            raise DepartmentContractValidationError(
                "kind must be DepartmentContractKind or None"
            )
        if mode is not None and not isinstance(mode, DepartmentInteractionMode):
            raise DepartmentContractValidationError(
                "mode must be DepartmentInteractionMode or None"
            )

        selected = tuple(
            contract
            for contract in self.contracts
            if contract.consumer is consumer
            and (provider is None or contract.provider is provider)
            and (kind is None or contract.kind is kind)
            and (mode is None or contract.mode is mode)
        )
        return tuple(
            sorted(
                selected,
                key=lambda contract: (
                    contract.provider.value,
                    contract.kind.value,
                    contract.contract_id.value,
                    contract.version.value,
                    contract.mode.value,
                ),
            )
        )

    def logical_values(self) -> tuple[object, ...]:
        """Canonical contract, graph, and captured COMMAND-policy material."""
        contract_values = tuple(
            contract.logical_values()
            for contract in sorted(
                self.contracts,
                key=lambda contract: (
                    contract.consumer.value,
                    contract.provider.value,
                    contract.kind.value,
                    contract.contract_id.value,
                    contract.version.value,
                    contract.mode.value,
                ),
            )
        )
        return (
            self.department_registry.logical_values(),
            _command_route_values(self.command_routes),
            contract_values,
        )
