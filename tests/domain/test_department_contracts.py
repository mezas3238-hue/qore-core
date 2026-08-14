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
    CANONICAL_DEPARTMENTS,
    DepartmentId,
    DepartmentInteractionMode,
    DepartmentRegistry,
)

D = DepartmentId
S = DepartmentInteractionMode.SYNCHRONOUS
A = DepartmentInteractionMode.ASYNCHRONOUS


def _contract(
    name: str,
    kind: DepartmentContractKind,
    consumer: DepartmentId,
    provider: DepartmentId,
    mode: DepartmentInteractionMode,
    *,
    version: str = "1.0",
) -> DepartmentContractSpec:
    return DepartmentContractSpec(
        contract_id=DepartmentContractId(name),
        version=DepartmentContractVersion(version),
        kind=kind,
        consumer=consumer,
        provider=provider,
        mode=mode,
    )


def _four_kinds() -> tuple[DepartmentContractSpec, ...]:
    return (
        _contract(
            "client-execution.order-apply",
            DepartmentContractKind.COMMAND,
            D.CLIENT_EXECUTION,
            D.ORDER_EXECUTION,
            S,
        ),
        _contract(
            "executive-control.governance-read",
            DepartmentContractKind.QUERY,
            D.EXECUTIVE_CONTROL,
            D.CORE_GOVERNANCE,
            S,
        ),
        _contract(
            "client-read-models.post-trade-event",
            DepartmentContractKind.EVENT,
            D.CLIENT_READ_MODELS,
            D.POST_TRADE,
            A,
        ),
        _contract(
            "certification-gate.validation-evidence",
            DepartmentContractKind.EVIDENCE,
            D.CERTIFICATION_GATE,
            D.LINEAGE_VALIDATION,
            A,
        ),
    )


def test_contract_kind_is_closed_to_four_semantic_classes() -> None:
    assert tuple(DepartmentContractKind) == (
        DepartmentContractKind.COMMAND,
        DepartmentContractKind.QUERY,
        DepartmentContractKind.EVENT,
        DepartmentContractKind.EVIDENCE,
    )


@pytest.mark.parametrize(
    "value",
    ("", "Upper", " leading", "contains/slash", "white space"),
)
def test_contract_id_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractId(value)


@pytest.mark.parametrize("value", ("", "V1", "1 0", "1/0"))
def test_contract_version_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractVersion(value)


def test_contract_spec_has_deterministic_logical_values() -> None:
    contract = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        S,
    )

    assert contract.logical_values() == (
        ("client-execution.order-apply",),
        ("1.0",),
        "command",
        "D18",
        "D10",
        "synchronous",
    )


def test_all_four_contract_kinds_can_bind_existing_fnd05_routes() -> None:
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=_four_kinds(),
    )

    assert {contract.kind for contract in registry.contracts} == set(
        DepartmentContractKind
    )


def test_registry_rejects_route_absent_from_department_graph() -> None:
    widget_to_execution = _contract(
        "widget.execute",
        DepartmentContractKind.COMMAND,
        D.CLIENT_READ_MODELS,
        D.ORDER_EXECUTION,
        S,
    )

    with pytest.raises(DepartmentContractValidationError, match="route must exist"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(widget_to_execution,),
        )


def test_registry_rejects_interaction_mode_not_certified_for_route() -> None:
    wrong_mode = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        A,
    )

    with pytest.raises(DepartmentContractValidationError, match="route must exist"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(wrong_mode,),
        )


@pytest.mark.parametrize(
    ("consumer", "provider", "name"),
    (
        (D.CLIENT_READ_MODELS, D.ORDER_EXECUTION, "widget.execution-authority"),
        (D.COMMERCIAL_ENTITLEMENTS, D.DECISION_INTELLIGENCE, "billing.strategy"),
        (D.RESEARCH_QUANT, D.ORDER_EXECUTION, "research.execution"),
        (D.OBSERVABILITY_RELIABILITY, D.ACCOUNT_PORTFOLIO, "health.account-write"),
        (D.DISTRIBUTED_RUNTIME_CLOUD, D.DECISION_INTELLIGENCE, "cloud.strategy"),
    ),
)
def test_registry_rejects_authority_inversion_routes(
    consumer: DepartmentId,
    provider: DepartmentId,
    name: str,
) -> None:
    attempted = _contract(
        name,
        DepartmentContractKind.COMMAND,
        consumer,
        provider,
        S,
    )

    with pytest.raises(DepartmentContractValidationError, match="route must exist"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(attempted,),
        )


def test_registry_rejects_duplicate_contract_id_version_pair() -> None:
    first = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        S,
    )
    duplicate_identity = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.QUERY,
        D.CLIENT_EXECUTION,
        D.RISK,
        S,
    )

    with pytest.raises(DepartmentContractValidationError, match="must be unique"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(first, duplicate_identity),
        )


def test_registry_allows_explicit_multiple_versions_of_same_contract() -> None:
    v1 = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        S,
        version="1.0",
    )
    v2 = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        S,
        version="2.0",
    )

    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(v2, v1),
    )

    assert registry.contract(v1.contract_id, v1.version) == v1
    assert registry.contract(v2.contract_id, v2.version) == v2


def test_contract_lookup_fails_closed_for_unknown_version() -> None:
    contract = _four_kinds()[0]
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(contract,),
    )

    with pytest.raises(DepartmentContractValidationError, match="unknown"):
        registry.contract(contract.contract_id, DepartmentContractVersion("2.0"))


def test_contracts_for_filters_and_sorts_deterministically() -> None:
    query = _contract(
        "client-execution.account-query",
        DepartmentContractKind.QUERY,
        D.CLIENT_EXECUTION,
        D.ACCOUNT_PORTFOLIO,
        S,
    )
    command = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        S,
    )
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(command, query),
    )

    assert registry.contracts_for(D.CLIENT_EXECUTION) == (query, command)
    assert registry.contracts_for(
        D.CLIENT_EXECUTION,
        provider=D.ORDER_EXECUTION,
        kind=DepartmentContractKind.COMMAND,
        mode=S,
    ) == (command,)


def test_registry_logical_values_are_declaration_order_independent() -> None:
    contracts = _four_kinds()
    forward = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=contracts,
    )
    reverse = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=tuple(reversed(contracts)),
    )

    assert forward.logical_values() == reverse.logical_values()


@pytest.mark.parametrize(
    "field",
    ("contract_id", "version", "kind", "consumer", "provider", "mode"),
)
def test_contract_spec_rejects_raw_runtime_types(field: str) -> None:
    values: dict[str, object] = {
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
    values[field] = raw[field]

    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractSpec(
            contract_id=cast(DepartmentContractId, values["contract_id"]),
            version=cast(DepartmentContractVersion, values["version"]),
            kind=cast(DepartmentContractKind, values["kind"]),
            consumer=cast(DepartmentId, values["consumer"]),
            provider=cast(DepartmentId, values["provider"]),
            mode=cast(DepartmentInteractionMode, values["mode"]),
        )


def test_contract_spec_rejects_self_route() -> None:
    with pytest.raises(DepartmentContractValidationError, match="must differ"):
        _contract(
            "governance.self",
            DepartmentContractKind.QUERY,
            D.CORE_GOVERNANCE,
            D.CORE_GOVERNANCE,
            S,
        )


def test_registry_rejects_wrong_runtime_container_and_member_types() -> None:
    contract = _four_kinds()[0]

    with pytest.raises(DepartmentContractValidationError, match="contracts must be tuple"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=cast(tuple[DepartmentContractSpec, ...], [contract]),
        )

    with pytest.raises(DepartmentContractValidationError, match="must contain"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=cast(tuple[DepartmentContractSpec, ...], ("bad",)),
        )

    with pytest.raises(DepartmentContractValidationError, match="department_registry"):
        DepartmentContractRegistry(
            department_registry=cast(DepartmentRegistry, "bad"),
            contracts=(),
        )


def test_registry_lookup_rejects_raw_runtime_identity_types() -> None:
    contract = _four_kinds()[0]
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=(contract,),
    )

    with pytest.raises(DepartmentContractValidationError, match="contract_id"):
        registry.contract(
            cast(DepartmentContractId, "client-execution.order-apply"),
            contract.version,
        )
    with pytest.raises(DepartmentContractValidationError, match="version"):
        registry.contract(
            contract.contract_id,
            cast(DepartmentContractVersion, "1.0"),
        )


def test_contracts_for_rejects_raw_runtime_filters() -> None:
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=_four_kinds(),
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


def test_partial_registry_unknown_department_filter_fails_closed() -> None:
    partial = DepartmentRegistry(departments=(CANONICAL_DEPARTMENTS[0],))
    registry = DepartmentContractRegistry(department_registry=partial)

    with pytest.raises(DepartmentContractValidationError, match="unknown consumer"):
        registry.contracts_for(D.IDENTITY_SECURITY)
