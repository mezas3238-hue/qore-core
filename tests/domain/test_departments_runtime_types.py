from __future__ import annotations

from typing import cast

import pytest

from qore.domain.departments import (
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


def test_department_spec_rejects_raw_department_id() -> None:
    with pytest.raises(DepartmentValidationError, match="department_id must be DepartmentId"):
        DepartmentSpec(
            department_id=cast(DepartmentId, "D01"),
            slug="core-governance",
            canonical_name="Core Governance",
        )


def test_department_spec_rejects_non_string_text_fields() -> None:
    with pytest.raises(DepartmentValidationError, match="department slug must be str"):
        DepartmentSpec(
            department_id=DepartmentId.CORE_GOVERNANCE,
            slug=cast(str, 1),
            canonical_name="Core Governance",
        )

    with pytest.raises(
        DepartmentValidationError,
        match="canonical department name must be str",
    ):
        DepartmentSpec(
            department_id=DepartmentId.CORE_GOVERNANCE,
            slug="core-governance",
            canonical_name=cast(str, 1),
        )


def test_department_dependency_rejects_raw_identifiers_and_mode() -> None:
    with pytest.raises(
        DepartmentValidationError,
        match="dependency consumer must be DepartmentId",
    ):
        DepartmentDependency(
            consumer=cast(DepartmentId, "D01"),
            provider=DepartmentId.IDENTITY_SECURITY,
            mode=DepartmentInteractionMode.SYNCHRONOUS,
        )

    with pytest.raises(
        DepartmentValidationError,
        match="dependency provider must be DepartmentId",
    ):
        DepartmentDependency(
            consumer=DepartmentId.CORE_GOVERNANCE,
            provider=cast(DepartmentId, "D02"),
            mode=DepartmentInteractionMode.SYNCHRONOUS,
        )

    with pytest.raises(
        DepartmentValidationError,
        match="dependency mode must be DepartmentInteractionMode",
    ):
        DepartmentDependency(
            consumer=DepartmentId.CORE_GOVERNANCE,
            provider=DepartmentId.IDENTITY_SECURITY,
            mode=cast(DepartmentInteractionMode, "synchronous"),
        )


def test_raw_synchronous_mode_cannot_bypass_cycle_validation() -> None:
    with pytest.raises(
        DepartmentValidationError,
        match="dependency mode must be DepartmentInteractionMode",
    ):
        DepartmentDependency(
            consumer=DepartmentId.CORE_GOVERNANCE,
            provider=DepartmentId.IDENTITY_SECURITY,
            mode=cast(DepartmentInteractionMode, "synchronous"),
        )


def test_registry_rejects_non_tuple_collections_and_wrong_members() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "core-governance")

    with pytest.raises(DepartmentValidationError, match="departments must be tuple"):
        DepartmentRegistry(departments=cast(tuple[DepartmentSpec, ...], [governance]))

    with pytest.raises(DepartmentValidationError, match="dependencies must be tuple"):
        DepartmentRegistry(
            departments=(governance,),
            dependencies=cast(tuple[DepartmentDependency, ...], []),
        )

    with pytest.raises(
        DepartmentValidationError,
        match="departments must contain DepartmentSpec values",
    ):
        DepartmentRegistry(
            departments=cast(tuple[DepartmentSpec, ...], ("not-a-spec",)),
        )

    with pytest.raises(
        DepartmentValidationError,
        match="dependencies must contain DepartmentDependency values",
    ):
        DepartmentRegistry(
            departments=(governance,),
            dependencies=cast(
                tuple[DepartmentDependency, ...],
                ("not-a-dependency",),
            ),
        )


def test_registry_lookup_apis_reject_raw_identifiers_and_modes() -> None:
    governance = _spec(DepartmentId.CORE_GOVERNANCE, "core-governance")
    identity = _spec(DepartmentId.IDENTITY_SECURITY, "identity-security")
    dependency = DepartmentDependency(
        consumer=DepartmentId.IDENTITY_SECURITY,
        provider=DepartmentId.CORE_GOVERNANCE,
        mode=DepartmentInteractionMode.SYNCHRONOUS,
    )
    registry = DepartmentRegistry(
        departments=(governance, identity),
        dependencies=(dependency,),
    )

    with pytest.raises(DepartmentValidationError, match="department_id must be DepartmentId"):
        registry.spec(cast(DepartmentId, "D01"))

    with pytest.raises(DepartmentValidationError, match="department_id must be DepartmentId"):
        registry.dependencies_for(cast(DepartmentId, "D02"))

    with pytest.raises(
        DepartmentValidationError,
        match="mode must be DepartmentInteractionMode or None",
    ):
        registry.dependencies_for(
            DepartmentId.IDENTITY_SECURITY,
            mode=cast(DepartmentInteractionMode, "synchronous"),
        )
