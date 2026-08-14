from __future__ import annotations

from typing import cast

import pytest

from qore.domain.department_contracts import (
    CANONICAL_DEPARTMENT_COMMAND_ROUTES,
    DepartmentContractId,
    DepartmentContractKind,
    DepartmentContractRegistry,
    DepartmentContractSpec,
    DepartmentContractValidationError,
    DepartmentContractVersion,
)
from qore.domain.departments import (
    CANONICAL_DEPARTMENT_REGISTRY,
    DepartmentDependency,
)


@pytest.mark.parametrize("route", CANONICAL_DEPARTMENT_COMMAND_ROUTES)
def test_every_explicit_command_capable_route_accepts_command_descriptor(
    route: DepartmentDependency,
) -> None:
    contract = DepartmentContractSpec(
        contract_id=DepartmentContractId(
            f"command-route.{route.consumer.value.lower()}.{route.provider.value.lower()}"
        ),
        version=DepartmentContractVersion("1.0"),
        kind=DepartmentContractKind.COMMAND,
        consumer=route.consumer,
        provider=route.provider,
        mode=route.mode,
    )

    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(contract,),
    )

    assert registry.contract(contract.contract_id, contract.version) == contract


def test_registry_logical_values_bind_captured_command_admission_policy() -> None:
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
    )

    assert registry.logical_values()[1] == (
        ("D18", "D10", "synchronous"),
        ("D20", "D01", "synchronous"),
    )


def test_equivalent_command_policy_order_is_accepted_and_deterministic() -> None:
    forward = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
    )
    reverse = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        command_routes=tuple(reversed(CANONICAL_DEPARTMENT_COMMAND_ROUTES)),
    )

    assert forward.logical_values() == reverse.logical_values()


def test_command_policy_container_member_and_alternate_fail_closed() -> None:
    with pytest.raises(DepartmentContractValidationError, match="must be tuple"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            command_routes=cast(
                tuple[DepartmentDependency, ...],
                list(CANONICAL_DEPARTMENT_COMMAND_ROUTES),
            ),
        )

    with pytest.raises(
        DepartmentContractValidationError,
        match="must contain DepartmentDependency",
    ):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            command_routes=cast(tuple[DepartmentDependency, ...], ("not-a-route",)),
        )

    with pytest.raises(
        DepartmentContractValidationError,
        match="must match canonical command routes",
    ):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            command_routes=(CANONICAL_DEPARTMENT_COMMAND_ROUTES[0],),
        )
