from __future__ import annotations

from typing import cast


class ServiceRegistry:
    """Registro plano y tipado de servicios por tipo.

    La misma instancia registrada bajo el mismo tipo es idempotente.
    Instancias distintas, aunque comparen iguales, se conservan por separado.
    """

    def __init__(self) -> None:
        self._services: dict[type[object], list[object]] = {}

    def register[T](self, service_type: type[T], instance: T) -> None:
        """Registrar una instancia bajo un tipo sin duplicar la misma identidad."""
        instances = self._services.setdefault(service_type, [])
        if all(existing is not instance for existing in instances):
            instances.append(instance)

    def resolve[T](self, service_type: type[T]) -> T | None:
        """Devolver la última instancia registrada para el tipo."""
        instances = self._services.get(service_type)
        return cast(T, instances[-1]) if instances else None

    def resolve_all[T](self, service_type: type[T]) -> list[T]:
        """Devolver todas las instancias distintas en orden de registro."""
        return [cast(T, instance) for instance in self._services.get(service_type, [])]
