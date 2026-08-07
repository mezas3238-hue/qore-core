"""
entity — Clase base para entidades del dominio QORE.

Propósito:
    Proporcionar una identidad estable e inmutable para todas las entidades,
    definiendo igualdad y hash exclusivamente por dicha identidad.

Alcance:
    - La identidad se asigna durante la construcción y no puede ser modificada.
    - El resto de atributos de la entidad son mutables.
    - No asume ningún tipo concreto de identificador.

Dependencias:
    - Python 3.12+
    - Sin dependencias externas.

Restricciones:
    - El tipo ``ID`` debe ser hashable e inmutable.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

ID = TypeVar("ID")


class Entity(Generic[ID]):
    """Clase base para entidades del dominio."""

    __slots__ = ("_id", "__id_locked")

    def __init__(self, entity_id: ID) -> None:
        object.__setattr__(self, "_id", entity_id)
        object.__setattr__(self, "_Entity__id_locked", True)

    @property
    def id(self) -> ID:
        """Identidad única de la entidad."""
        return self._id

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_id" and getattr(self, "_Entity__id_locked", False):
            raise AttributeError("Entity identity is immutable")
        super().__setattr__(name, value)

    def __eq__(self, other: object) -> bool:
        if other is self:
            return True
        if not isinstance(other, Entity):
            return NotImplemented
        if type(self) is not type(other):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
