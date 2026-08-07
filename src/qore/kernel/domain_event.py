"""
domain_event — Clase base inmutable para eventos del dominio de QORE.

Propósito:
    Definir la estructura inmutable que deben cumplir todos los eventos de dominio.

Alcance:
    - ``DomainEvent`` como dataclass inmutable.
    - ``timestamp`` y ``event_name`` obligatorios.
    - ``event_id``, ``event_version`` y ``metadata`` con defaults.
    - Igualdad y hash basados en ``event_id``.

Dependencias:
    - Python 3.12.

Restricciones:
    - Sin lógica de negocio ni serialización.
    - ``metadata`` se copia defensivamente y se expone como mapping de solo lectura.
    - La inmutabilidad de valores anidados es superficial.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Evento de dominio base para QORE."""

    timestamp: datetime
    event_name: str
    event_id: UUID = field(default_factory=uuid4)
    event_version: str = "1.0"
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}), compare=False, hash=False
    )

    def __post_init__(self) -> None:
        """Aislar metadata de mutaciones externas."""
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def __eq__(self, other: object) -> bool:
        if other is self:
            return True
        if type(self) is not type(other):
            return NotImplemented
        return self.event_id == other.event_id

    def __hash__(self) -> int:
        return hash(self.event_id)
