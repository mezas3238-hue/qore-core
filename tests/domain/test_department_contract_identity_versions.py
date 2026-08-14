from __future__ import annotations

import pytest

from qore.domain.department_contracts import (
    DepartmentContractId,
    DepartmentContractKind,
    DepartmentContractRegistry,
    DepartmentContractSpec,
    DepartmentContractValidationError,
    DepartmentContractVersion,
)
from qore.domain.departments import (
    CANONICAL_DEPARTMENT_REGISTRY,
    DepartmentId,
    DepartmentInteractionMode,
)

D = DepartmentId
S = DepartmentInteractionMode.SYNCHRONOUS
A = DepartmentInteractionMode.ASYNCHRONOUS


def _spec(
    *,
    version: str,
    kind: DepartmentContractKind = DepartmentContractKind.COMMAND,
    consumer: DepartmentId = D.CLIENT_EXECUTION,
    provider: DepartmentId = D.ORDER_EXECUTION,
    mode: DepartmentInteractionMode = S,
) -> DepartmentContractSpec:
    return DepartmentContractSpec(
        contract_id=DepartmentContractId("client-execution.order-apply"),
        version=DepartmentContractVersion(version),
        kind=kind,
        consumer=consumer,
        provider=provider,
        mode=mode,
    )


def test_versions_of_same_contract_preserve_authority_profile() -> None:
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(_spec(version="2.0"), _spec(version="1.0")),
    )

    assert len(registry.contracts) == 2


@pytest.mark.parametrize(
    ("kind", "consumer", "provider", "mode"),
    (
        (
            DepartmentContractKind.QUERY,
            D.CLIENT_EXECUTION,
            D.ORDER_EXECUTION,
            S,
        ),
        (
            DepartmentContractKind.COMMAND,
            D.POST_TRADE,
            D.ORDER_EXECUTION,
            S,
        ),
        (
            DepartmentContractKind.COMMAND,
            D.CLIENT_EXECUTION,
            D.RISK,
            S,
        ),
        (
            DepartmentContractKind.COMMAND,
            D.CLIENT_EXECUTION,
            D.ORDER_EXECUTION,
            A,
        ),
    ),
)
def test_version_cannot_change_contract_authority_profile(
    kind: DepartmentContractKind,
    consumer: DepartmentId,
    provider: DepartmentId,
    mode: DepartmentInteractionMode,
) -> None:
    changed = _spec(
        version="2.0",
        kind=kind,
        consumer=consumer,
        provider=provider,
        mode=mode,
    )

    with pytest.raises(
        DepartmentContractValidationError,
        match="versions must preserve authority profile",
    ):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(_spec(version="1.0"), changed),
        )
