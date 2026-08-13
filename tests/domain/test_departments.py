from __future__ import annotations

import pytest

from qore.domain.departments import (
    CANONICAL_DEPARTMENT_DEPENDENCIES,
    CANONICAL_DEPARTMENT_REGISTRY,
    CANONICAL_DEPARTMENTS,
    DepartmentDependency,
    DepartmentId,
    DepartmentInteractionMode,
    DepartmentRegistry,
    DepartmentSpec,
    DepartmentValidationError,
)


def _spec(department_id: DepartmentId, slug: str) -> DepartmentSpec:
    return DepartmentSpec(
        department_id=department_id,
        slug=slug,
        canonical_name=f"Department {department_id.value}",
    )


def test_canonical_registry_contains_exactly_the_24_frozen_departments() -> None:
    assert len(CANONICAL_DEPARTMENTS) == 24
    assert tuple(spec.department_id for spec in CANONICAL_DEPARTMENTS) == tuple(DepartmentId)
    assert len({spec.slug for spec in CANONICAL_DEPARTMENTS}) == 24


def test_department_16_is_the_distributed_runtime_hosting_vps_cloud_owner() -> None:
    spec = CANONICAL_DEPARTMENT_REGISTRY.spec(DepartmentId.DISTRIBUTED_RUNTIME_CLOUD)

    assert spec.slug == "distributed-runtime-cloud"
    assert spec.canonical_name == "Distributed Runtime, Hosting, VPS & Cloud Operations"


def test_canonical_synchronous_graph_is_acyclic_and_provider_first() -> None:
    ordered = CANONICAL_DEPARTMENT_REGISTRY.resolve_synchronous_order()
    order_by_id = {spec.department_id: index for index, spec in enumerate(ordered)}

    assert len(ordered) == 24
    assert len(order_by_id) == 24
    for dependency in CANONICAL_DEPARTMENT_DEPENDENCIES:
        if dependency.mode is DepartmentInteractionMode.SYNCHRONOUS:
            assert order_by_id[dependency.provider] < order_by_id[dependency.consumer]


def test_service_planes_are_not_strategic_upstream_dependencies() -> None:
    providers = {
        dependency.provider
        for dependency in CANONICAL_DEPARTMENT_REGISTRY.dependencies_for(
            DepartmentId.DECISION_INTELLIGENCE
        )
    }

    assert DepartmentId.DISTRIBUTED_RUNTIME_CLOUD not in providers
    assert DepartmentId.SIGNAL_DISTRIBUTION not in providers
    assert DepartmentId.CLIENT_EXECUTION not in providers
    assert DepartmentId.CLIENT_READ_MODELS not in providers
    assert DepartmentId.EXECUTIVE_CONTROL not in providers
    assert DepartmentId.COMMERCIAL_ENTITLEMENTS not in providers


def test_hosted_client_execution_depends_on_cloud_without_reversing_authority() -> None:
    client_sync_providers = {
        dependency.provider
        for dependency in CANONICAL_DEPARTMENT_REGISTRY.dependencies_for(
            DepartmentId.CLIENT_EXECUTION,
            mode=DepartmentInteractionMode.SYNCHRONOUS,
        )
    }
    cloud_providers = {
        dependency.provider
        for dependency in CANONICAL_DEPARTMENT_REGISTRY.dependencies_for(
            DepartmentId.DISTRIBUTED_RUNTIME_CLOUD
        )
    }

    assert DepartmentId.DISTRIBUTED_RUNTIME_CLOUD in client_sync_providers
    assert DepartmentId.SIGNAL_DISTRIBUTION in client_sync_providers
    assert DepartmentId.ORDER_EXECUTION in client_sync_providers
    assert DepartmentId.CLIENT_EXECUTION not in cloud_providers


def test_widget_dependencies_are_asynchronous_and_read_side_only() -> None:
    widget_dependencies = CANONICAL_DEPARTMENT_REGISTRY.dependencies_for(
        DepartmentId.CLIENT_READ_MODELS
    )

    assert widget_dependencies
    assert all(
        dependency.mode is DepartmentInteractionMode.ASYNCHRONOUS
        for dependency in widget_dependencies
    )


def test_unknown_dependency_reference_is_rejected() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "governance")
    unknown = DepartmentDependency(
        consumer=DepartmentId.CORE_GOVERNANCE,
        provider=DepartmentId.IDENTITY_SECURITY,
        mode=DepartmentInteractionMode.SYNCHRONOUS,
    )

    with pytest.raises(DepartmentValidationError, match="unknown provider department: D02"):
        DepartmentRegistry(departments=(governance,), dependencies=(unknown,))


def test_duplicate_department_ids_are_rejected() -> None:
    first = _spec(DepartmentId.CORE_GOVERNANCE, "governance")
    second = _spec(DepartmentId.CORE_GOVERNANCE, "governance-copy")

    with pytest.raises(DepartmentValidationError, match="department ids must be unique"):
        DepartmentRegistry(departments=(first, second))


def test_duplicate_department_slugs_are_rejected() -> None:
    first = _spec(DepartmentId.CORE_GOVERNANCE, "duplicate")
    second = _spec(DepartmentId.IDENTITY_SECURITY, "duplicate")

    with pytest.raises(DepartmentValidationError, match="department slugs must be unique"):
        DepartmentRegistry(departments=(first, second))


def test_duplicate_dependency_edges_are_rejected() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "governance")
    identity = _spec(DepartmentId.IDENTITY_SECURITY, "identity")
    dependency = DepartmentDependency(
        consumer=DepartmentId.IDENTITY_SECURITY,
        provider=DepartmentId.CORE_GOVERNANCE,
        mode=DepartmentInteractionMode.ASYNCHRONOUS,
    )

    with pytest.raises(
        DepartmentValidationError,
        match="department dependency edges must be unique",
    ):
        DepartmentRegistry(
            departments=(governance, identity),
            dependencies=(dependency, dependency),
        )


def test_self_dependency_is_rejected() -> None:
    with pytest.raises(DepartmentValidationError, match="department cannot depend on itself"):
        DepartmentDependency(
            consumer=DepartmentId.CORE_GOVERNANCE,
            provider=DepartmentId.CORE_GOVERNANCE,
            mode=DepartmentInteractionMode.SYNCHRONOUS,
        )


def test_synchronous_cycle_is_rejected() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "governance")
    identity = _spec(DepartmentId.IDENTITY_SECURITY, "identity")
    dependencies = (
        DepartmentDependency(
            consumer=DepartmentId.CORE_GOVERNANCE,
            provider=DepartmentId.IDENTITY_SECURITY,
            mode=DepartmentInteractionMode.SYNCHRONOUS,
        ),
        DepartmentDependency(
            consumer=DepartmentId.IDENTITY_SECURITY,
            provider=DepartmentId.CORE_GOVERNANCE,
            mode=DepartmentInteractionMode.SYNCHRONOUS,
        ),
    )

    with pytest.raises(
        DepartmentValidationError,
        match="synchronous department dependency cycle detected",
    ):
        DepartmentRegistry(
            departments=(governance, identity),
            dependencies=dependencies,
        )


def test_async_feedback_cycle_is_permitted() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "governance")
    identity = _spec(DepartmentId.IDENTITY_SECURITY, "identity")
    dependencies = (
        DepartmentDependency(
            consumer=DepartmentId.CORE_GOVERNANCE,
            provider=DepartmentId.IDENTITY_SECURITY,
            mode=DepartmentInteractionMode.ASYNCHRONOUS,
        ),
        DepartmentDependency(
            consumer=DepartmentId.IDENTITY_SECURITY,
            provider=DepartmentId.CORE_GOVERNANCE,
            mode=DepartmentInteractionMode.ASYNCHRONOUS,
        ),
    )

    registry = DepartmentRegistry(
        departments=(identity, governance),
        dependencies=dependencies,
    )

    assert tuple(spec.department_id for spec in registry.resolve_synchronous_order()) == (
        DepartmentId.CORE_GOVERNANCE,
        DepartmentId.IDENTITY_SECURITY,
    )


def test_logical_values_are_independent_of_declaration_order() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "governance")
    identity = _spec(DepartmentId.IDENTITY_SECURITY, "identity")
    dependency = DepartmentDependency(
        consumer=DepartmentId.IDENTITY_SECURITY,
        provider=DepartmentId.CORE_GOVERNANCE,
        mode=DepartmentInteractionMode.SYNCHRONOUS,
    )

    first = DepartmentRegistry(
        departments=(governance, identity),
        dependencies=(dependency,),
    )
    second = DepartmentRegistry(
        departments=(identity, governance),
        dependencies=(dependency,),
    )

    assert first.logical_values() == second.logical_values()


def test_unknown_spec_lookup_fails_closed() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "governance")
    registry = DepartmentRegistry(departments=(governance,))

    with pytest.raises(DepartmentValidationError, match="unknown canonical department: D02"):
        registry.spec(DepartmentId.IDENTITY_SECURITY)


def test_invalid_department_descriptor_is_rejected() -> None:
    with pytest.raises(DepartmentValidationError, match="department slug"):
        DepartmentSpec(
            department_id=DepartmentId.CORE_GOVERNANCE,
            slug="Invalid Slug",
            canonical_name="Governance",
        )

    with pytest.raises(DepartmentValidationError, match="must not be empty"):
        DepartmentSpec(
            department_id=DepartmentId.CORE_GOVERNANCE,
            slug="governance",
            canonical_name=" ",
        )
