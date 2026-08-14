from __future__ import annotations

from typing import cast

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
    DepartmentRegistry,
)

D = DepartmentId
S = DepartmentInteractionMode.SYNCHRONOUS


def _valid() -> DepartmentContractSpec:
    return DepartmentContractSpec(
        contract_id=DepartmentContractId("client-execution.order-apply"),
        version=DepartmentContractVersion("1.0"),
        kind=DepartmentContractKind.COMMAND,
        consumer=D.CLIENT_EXECUTION,
        provider=D.ORDER_EXECUTION,
        mode=S,
    )


def test_identity_and_version_reject_non_string_runtime_values() -> None:
    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractId(cast(str, 1))
    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractVersion(cast(str, 1))


@pytest.mark.parametrize(
    "field",
    ("contract_id", "version", "kind", "consumer", "provider", "mode"),
)
def test_spec_rejects_raw_runtime_types(field: str) -> None:
    valid: dict[str, object] = {
        "contract_id": DepartmentContractId("client-execution.order-apply"),
        "version": DepartmentContractVersion("1.0"),
        "kind": DepartmentContractKind.COMMAND,
        "consumer": D.CLIENT_EXECUTION,
        "provider": D.ORDER_EXECUTION,
        "mode": S,
    }
    raw: dict[str, object] = {
        "contract_id": "client-execution.order-apply",
        "version": "1.0",
        "kind": "command",
        "consumer": "D18",
        "provider": "D10",
        "mode": "synchronous",
    }
    valid[field] = raw[field]

    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractSpec(
            contract_id=cast(DepartmentContractId, valid["contract_id"]),
            version=cast(DepartmentContractVersion, valid["version"]),
            kind=cast(DepartmentContractKind, valid["kind"]),
            consumer=cast(DepartmentId, valid["consumer"]),
            provider=cast(DepartmentId, valid["provider"]),
            mode=cast(DepartmentInteractionMode, valid["mode"]),
        )


def test_registry_rejects_wrong_runtime_container_and_member_types() -> None:
    item = _valid()

    with pytest.raises(DepartmentContractValidationError, match="department_registry"):
        DepartmentContractRegistry(
            department_registry=cast(DepartmentRegistry, "bad"),
            contracts=(),
        )

    with pytest.raises(
        DepartmentContractValidationError,
        match="contracts must be tuple",
    ):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=cast(tuple[DepartmentContractSpec, ...], [item]),
        )

    with pytest.raises(DepartmentContractValidationError, match="must contain"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=cast(tuple[DepartmentContractSpec, ...], ("bad",)),
        )


def test_exact_lookup_rejects_raw_identity_and_version() -> None:
    item = _valid()
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(item,),
    )

    with pytest.raises(DepartmentContractValidationError, match="contract_id"):
        registry.contract(
            cast(DepartmentContractId, "client-execution.order-apply"),
            item.version,
        )
    with pytest.raises(DepartmentContractValidationError, match="version"):
        registry.contract(
            item.contract_id,
            cast(DepartmentContractVersion, "1.0"),
        )


def test_filters_reject_raw_runtime_types() -> None:
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(_valid(),),
    )

    with pytest.raises(DepartmentContractValidationError, match="consumer"):
        registry.contracts_for(cast(DepartmentId, "D18"))
    with pytest.raises(DepartmentContractValidationError, match="provider"):
        registry.contracts_for(
            D.CLIENT_EXECUTION,
            provider=cast(DepartmentId, "D10"),
        )
    with pytest.raises(DepartmentContractValidationError, match="kind"):
        registry.contracts_for(
            D.CLIENT_EXECUTION,
            kind=cast(DepartmentContractKind, "command"),
        )
    with pytest.raises(DepartmentContractValidationError, match="mode"):
        registry.contracts_for(
            D.CLIENT_EXECUTION,
            mode=cast(DepartmentInteractionMode, "synchronous"),
        )


def test_default_filters_return_all_contracts_for_consumer() -> None:
    item = _valid()
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(item,),
    )

    assert registry.contracts_for(D.CLIENT_EXECUTION) == (item,)
    assert registry.contracts_for(D.CORE_GOVERNANCE) == ()
