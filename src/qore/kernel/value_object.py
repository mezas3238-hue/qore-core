"""
value_object — Clase base para objetos de valor de QORE.

Propósito:
    Definir el contrato de igualdad por valores y la inmutabilidad total
    para todos los Value Objects del dominio.

Alcance:
    - Proporcionar igualdad y hash basados en todos los campos.
    - No añade comportamiento específico del dominio.

Dependencias:
    - Python 3.12+
    - Módulo ``dataclasses``.

Restricciones:
    - Los campos de las subclases deben ser inmutables.
"""
from __future__ import annotations

from dataclasses import astuple, dataclass


@dataclass(frozen=True, slots=True)
class ValueObject:
    """Clase base para objetos de valor inmutables."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return astuple(self) == astuple(other)

    def __hash__(self) -> int:
        return hash(astuple(self))
