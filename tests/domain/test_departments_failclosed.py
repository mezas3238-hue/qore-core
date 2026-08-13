from __future__ import annotations

import pytest

from qore.domain.departments import (
    DepartmentDependency,
    DepartmentId,
    DepartmentInteractionMode,
    DepartmentRegistry,
    DepartmentSpec,
    DepartmentValidationError,
)


def _spec(
    department_id: DepartmentId,
    slug: str,
    canonical_name: str,
) -> DepartmentSpec:
    return DepartmentSpec(
        department_id=department_id,
        slug=slug,
        canonical_name=canonical_name,
    )


def test_department_name_with_surrounding_whitespace_is_rejected() -> None:
    with pytest.raises(
        DepartmentValidationError,
        match="canonical department name must not have surrounding whitespace",
    ):
        _spec(
            DepartmentId.CORE_GOVERNANCE,
            "core-governance",
            " Core Governance ",
        )


def test_duplicate_canonical_department_names_are_rejected() -> None:
    first = _spec(
        DepartmentId.CORE_GOVERNANCE,
        "core-governance",
        "Duplicate Authority",
    )
    second = _spec(
        DepartmentId.IDENTITY_SECURITY,
        "identity-security",
        "Duplicate Authority",
    )

    with pytest.raises(
        DepartmentValidationError,
        match="canonical department names must be unique",
    ):
        DepartmentRegistry(departments=(first, second))


def test_unknown_dependency_consumer_is_rejected() -> None:
    governance = _spec(
        DepartmentId.CORE_GOVERNANCE,
        "core-governance",
        "Core Governance",
    )
    dependency = DepartmentDependency(
        consumer=DepartmentId.IDENTITY_SECURITY,
        provider=DepartmentId.CORE_GOVERNANCE,
        mode=DepartmentInteractionMode.SYNCHRONOUS,
    )

    with pytest.raises(
        DepartmentValidationError,
        match="unknown consumer department: D02",
    ):
        DepartmentRegistry(
            departments=(governance,),
            dependencies=(dependency,),
        )


def test_dependencies_for_unknown_department_fails_closed() -> None:
    governance = _spec(
        DepartmentId.CORE_GOVERNANCE,
        "core-governance",
        "Core Governance",
    )
    registry = DepartmentRegistry(departments=(governance,))

    with pytest.raises(
        DepartmentValidationError,
        match="unknown canonical department: D02",
    ):
        registry.dependencies_for(DepartmentId.IDENTITY_SECURITY)
