"""
clock — Contrato del servicio de tiempo de QORE.

Propósito:
    Definir el comportamiento que cualquier implementación de reloj debe cumplir.

Alcance:
    - Clase ``Clock`` con ``now() -> datetime`` en UTC.
    - Sin singletons ni estado global mutable.

Dependencias:
    - Python 3.12
    - Biblioteca estándar ``datetime``.

Restricciones:
    - No exportar una instancia global desde el Kernel.
"""
from __future__ import annotations

from datetime import UTC, datetime


class Clock:
    """Reloj base de QORE."""

    def now(self) -> datetime:
        """Obtener la fecha y hora actual en UTC."""
        return datetime.now(tz=UTC)
