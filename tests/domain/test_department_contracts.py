from __future__ import annotations

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
    CANONICAL_DEPARTMENT_DEPENDENCIES,
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


def test_four_semantic_kinds_are_closed_and_bind_valid_routes() -> None:
    assert tuple(DepartmentContractKind) == (
        DepartmentContractKind.COMMAND,
        DepartmentContractKind.QUERY,
        DepartmentContractKind.EVENT,
        DepartmentContractKind.EVIDENCE,
    )
    registry = DepartmentContractRegistry(
        department_registry=CANONICAL_DEPARTMENT_REGISTRY,
        contracts=_four_kinds(),
    )
    assert {item.kind for item in registry.contracts} == set(DepartmentContractKind)


@pytest.mark.parametrize("value", ("", "Upper", " leading", "bad/value", "has space"))
def test_contract_id_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractId(value)


@pytest.mark.parametrize("value", ("", "V1", "1 0", "1/0"))
def test_contract_version_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(DepartmentContractValidationError):
        DepartmentContractVersion(value)


def test_contract_spec_logical_values_are_explicit() -> None:
    item = _four_kinds()[0]
    assert item.logical_values() == (
        ("client-execution.order-apply",),
        ("1.0",),
        "command",
        "D18",
        "D10",
        "synchronous",
    )


def test_equivalent_graph_is_accepted_but_alternate_graph_is_rejected() -> None:
    equivalent = DepartmentRegistry(
        departments=CANONICAL_DEPARTMENTS,
        dependencies=CANONICAL_DEPARTMENT_DEPENDENCIES,
    )
    registry = DepartmentContractRegistry(
        department_registry=equivalent,
        contracts=_four_kinds(),
    )
    assert registry.department_registry.logical_values() == (
        CANONICAL_DEPARTMENT_REGISTRY.logical_values()
    )

    partial = DepartmentRegistry(departments=(CANONICAL_DEPARTMENTS[0],))
    with pytest.raises(DepartmentContractValidationError, match="must match canonical"):
        DepartmentContractRegistry(department_registry=partial)


def test_absent_route_and_wrong_mode_fail_closed() -> None:
    absent = _contract(
        "widget.execute",
        DepartmentContractKind.COMMAND,
        D.CLIENT_READ_MODELS,
        D.ORDER_EXECUTION,
        S,
    )
    wrong_mode = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        A,
    )
    for item in (absent, wrong_mode):
        with pytest.raises(DepartmentContractValidationError, match="route must exist"):
            DepartmentContractRegistry(
                department_registry=CANONICAL_DEPARTMENT_REGISTRY,
                contracts=(item,),
            )


def test_command_capable_routes_are_explicit_and_canonical() -> None:
    assert CANONICAL_DEPARTMENT_COMMAND_ROUTES == (
        (D.CLIENT_EXECUTION, D.ORDER_EXECUTION, S),
        (D.EXECUTIVE_CONTROL, D.CORE_GOVERNANCE, S),
    )
    canonical_routes = {
        (dependency.consumer, dependency.provider, dependency.mode)
        for dependency in CANONICAL_DEPARTMENT_DEPENDENCIES
    }
    assert set(CANONICAL_DEPARTMENT_COMMAND_ROUTES) <= canonical_routes


@pytest.mark.parametrize(
    ("consumer", "provider", "mode"),
    (
        (D.CLIENT_READ_MODELS, D.POST_TRADE, A),
        (D.CERTIFICATION_GATE, D.LINEAGE_VALIDATION, A),
    ),
)
def test_valid_dependency_route_cannot_be_laundered_into_command_authority(
    consumer: DepartmentId,
    provider: DepartmentId,
    mode: DepartmentInteractionMode,
) -> None:
    attempted = _contract(
        "forbidden.command-on-valid-route",
        DepartmentContractKind.COMMAND,
        consumer,
        provider,
        mode,
    )

    with pytest.raises(
        DepartmentContractValidationError,
        match="must be explicitly command-capable",
    ):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(attempted,),
        )


@pytest.mark.parametrize(
    ("consumer", "provider"),
    (
        (D.CLIENT_READ_MODELS, D.ORDER_EXECUTION),
        (D.COMMERCIAL_ENTITLEMENTS, D.DECISION_INTELLIGENCE),
        (D.RESEARCH_QUANT, D.ORDER_EXECUTION),
        (D.OBSERVABILITY_RELIABILITY, D.ACCOUNT_PORTFOLIO),
        (D.DISTRIBUTED_RUNTIME_CLOUD, D.DECISION_INTELLIGENCE),
    ),
)
def test_authority_inversion_routes_are_rejected(
    consumer: DepartmentId,
    provider: DepartmentId,
) -> None:
    attempted = _contract(
        "forbidden.authority",
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


def test_duplicate_identity_rejected_and_versions_are_explicit() -> None:
    v1 = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.COMMAND,
        D.CLIENT_EXECUTION,
        D.ORDER_EXECUTION,
        S,
        version="1.0",
    )
    duplicate = _contract(
        "client-execution.order-apply",
        DepartmentContractKind.QUERY,
        D.CLIENT_EXECUTION,
        D.RISK,
        S,
        version="1.0",
    )
    with pytest.raises(DepartmentContractValidationError, match="must be unique"):
        DepartmentContractRegistry(
            department_registry=CANONICAL_DEPARTMENT_REGISTRY,
            contracts=(v1, duplicate),
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
    with pytest.raises(DepartmentContractValidationError, match="unknown"):
        registry.contract(v1.contract_id, DepartmentContractVersion("3.0"))


def test_filters_and_registry_logical_values_are_deterministic() -> None:
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
    assert forward.contracts_for(
        D.CLIENT_EXECUTION,
        provider=D.ORDER_EXECUTION,
        kind=DepartmentContractKind.COMMAND,
        mode=S,
    ) == (contracts[0],)


def test_self_route_is_rejected() -> None:
    with pytest.raises(DepartmentContractValidationError, match="must differ"):
        _contract(
            "governance.self",
            DepartmentContractKind.QUERY,
            D.CORE_GOVERNANCE,
            D.CORE_GOVERNANCE,
            S,
        )
