from __future__ import annotations

from dataclasses import dataclass

from qore.core.runtime import RuntimeComponent
from qore.kernel.errors import ValidationError
from qore.kernel.result import Failure, Result, Success


@dataclass(frozen=True, slots=True)
class RuntimeComponentSpec:
    """Declaración inmutable de un componente y sus dependencias."""

    component_name: str
    component: RuntimeComponent
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validar invariantes locales de la declaración."""
        if not self.component_name.strip():
            raise ValidationError("component_name must not be empty")
        if self.component_name != self.component.component_name:
            raise ValidationError("component_name must match component.component_name")
        if any(not dependency.strip() for dependency in self.depends_on):
            raise ValidationError("dependency names must not be empty")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValidationError("dependency names must be unique within a component")


@dataclass(frozen=True, slots=True)
class RuntimePlan:
    """Plan declarativo e inmutable de componentes del runtime."""

    components: tuple[RuntimeComponentSpec, ...] = ()

    def resolve_start_order(
        self,
    ) -> Result[tuple[RuntimeComponentSpec, ...], ValidationError]:
        """Validar el grafo y resolver un orden topológico estable."""
        names = [spec.component_name for spec in self.components]
        if len(set(names)) != len(names):
            return Failure(ValidationError("runtime component names must be unique"))

        known_names = set(names)
        for spec in self.components:
            for dependency in spec.depends_on:
                if dependency not in known_names:
                    return Failure(
                        ValidationError(
                            f"unknown runtime component dependency: {dependency}"
                        )
                    )

        remaining = list(self.components)
        resolved_names: set[str] = set()
        ordered: list[RuntimeComponentSpec] = []

        while remaining:
            next_remaining: list[RuntimeComponentSpec] = []
            progressed = False

            for spec in remaining:
                if all(dependency in resolved_names for dependency in spec.depends_on):
                    ordered.append(spec)
                    resolved_names.add(spec.component_name)
                    progressed = True
                else:
                    next_remaining.append(spec)

            if not progressed:
                return Failure(
                    ValidationError("runtime component dependency cycle detected")
                )
            remaining = next_remaining

        return Success(tuple(ordered))
