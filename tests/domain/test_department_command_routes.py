from __future__ import annotations

import pytest

from qore.domain.department_contracts import (
    CANONICAL_DEPARTMENT_COMMAND_ROUTES,
    DepartmentContractId,
    DepartmentContractKind,
    DepartmentContractRegistry,
    DepartmentContractSpec,
    DepartmentContractVersion,
)
from qore.domain.departments import (
    CANONICAL_DEPARTMENT_REGISTRY,
    DepartmentId,
    DepartmentInteractionMode,
)


@pytest.mark.parametrize(
    ("consumer", "provider", "mode"),
    CANONICAL_DEPARTMENT_COMMAND_ROUTES,
)
def test_every_explicit_command_capable_route_accepts_command_descriptor(
    consumer: DepartmentId,
    provider: DepartmentId,
    mode: DepartmentInteractionMode,
) -> None:
    contract = DepartmentContractSpec(
        contract_id=DepartmentContractId(
            f"command-route.{consumer.value.lower()}.{provider.value.lower()}"
        ),
        version=DepartmentContractVersion("1.0"),
        kind=DepartmentContractKind.COMMAND,
        consumer=consumer,
        provider=provider,
        mode=mode,
    )

    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(contract,),
    )

    assert registry.contract(contract.contract_id, contract.version) == contract
