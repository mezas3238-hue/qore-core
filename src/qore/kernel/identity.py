"""
identity — Identidad oficial de cualquier componente de QORE.

Propósito:
    Proporcionar una representación inmutable de la identidad de entidades,
    objetos de valor u otros componentes del sistema.

Alcance:
    - Definir un tipo genérico ``Identity[T]``.
    - Garantizar inmutabilidad (``frozen=True, slots=True``).
    - No incluye lógica de negocio ni validación de formato.

Dependencias:
    - Python 3.12+
    - Módulo ``dataclasses`` de la biblioteca estándar.

Restricciones:
    - El tipo ``T`` debe ser hashable e inmutable para preservar los contratos
      de igualdad y hash.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Identity(Generic[T]):
    """Identidad inmutable de una entidad o componente."""

    id: T
