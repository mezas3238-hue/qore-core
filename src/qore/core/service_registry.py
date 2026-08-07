from __future__ import annotations


class ServiceRegistry:
    """Registro plano de servicios por tipo.

    La misma instancia registrada bajo el mismo tipo es idempotente.
    Instancias distintas, aunque comparen iguales, se conservan por separado.
    """

    def __init__(self) -> None:
        self._services: dict[type[object], list[object]] = {}

    def register(self, service_type: type[object], instance: object) -> None:
        """Registrar una instancia bajo un tipo sin duplicar la misma identidad."""
        instances = self._services.setdefault(service_type, [])
        if all(existing is not instance for existing in instances):
            instances.append(instance)

    def resolve(self, service_type: type[object]) -> object | None:
        """Devolver la última instancia registrada para el tipo."""
        instances = self._services.get(service_type)
        return instances[-1] if instances else None

    def resolve_all(self, service_type: type[object]) -> list[object]:
        """Devolver todas las instancias distintas en orden de registro."""
        return list(self._services.get(service_type, []))
