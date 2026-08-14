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


def _spec(
    *,
    version: str,
    kind: DepartmentContractKind = DepartmentContractKind.COMMAND,
    provider: DepartmentId = D.ORDER_EXECUTION,
) -> DepartmentContractSpec:
    return DepartmentContractSpec(
        contract_id=DepartmentContractId("client-execution.order-apply"),
        version=DepartmentContractVersion(version),
        kind=kind,
        consumer=D.CLIENT_EXECUTION,
        provider=provider,
        mode=S,
    )


def test_versions_of_same_contract_preserve_authority_profile() -> None:
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(_spec(version="2.0"), _spec(version="1.0")),
    )

    assert len(registry.contracts) == 2


@pytest.mark.parametrize(
    ("kind", "provider"),
    (
        (DepartmentContractKind.QUERY, D.ORDER_EXECUTION),
        (DepartmentContractKind.COMMAND, D.RISK),
    ),
)
def test_version_cannot_change_contract_authority_profile(
    kind: DepartmentContractKind,
    provider: DepartmentId,
) -> None:
    changed = _spec(version="2.0", kind=kind, provider=provider)

    with pytest.raises(
        DepartmentContractValidationError,
        match="versions must preserve authority profile",
    ):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(_spec(version="1.0"), changed),
        )
