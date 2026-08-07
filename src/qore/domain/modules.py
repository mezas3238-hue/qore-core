from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from typing import Protocol

from qore.kernel.errors import DomainError


class ModuleArchitectureError(DomainError):
    """Error base de la arquitectura modular de dominio."""

    __slots__ = ()


class ModuleValidationError(ModuleArchitectureError):
    """Descriptor o frontera modular inválida."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ModuleName:
    """Nombre lógico estable de un módulo funcional."""

    value: str

    def __post_init__(self) -> None:
        if fullmatch(r"[a-z][a-z0-9-]*", self.value) is None:
            raise ModuleValidationError(
                "module name must use lowercase letters, digits, or hyphens"
            )


@dataclass(frozen=True, slots=True)
class ModuleVersion:
    """Versión lógica explícita del contrato de módulo."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ModuleValidationError("module version must not be empty")


class ModuleLayer(StrEnum):
    """Fronteras mínimas oficiales de un módulo QORE."""

    API = "api"
    APPLICATION = "application"
    DOMAIN = "domain"
    CONTRACTS = "contracts"
    SERVICES = "services"
    EVENTS = "events"
    COMMANDS = "commands"


REQUIRED_MODULE_LAYERS: tuple[ModuleLayer, ...] = (
    ModuleLayer.API,
    ModuleLayer.APPLICATION,
    ModuleLayer.DOMAIN,
    ModuleLayer.CONTRACTS,
    ModuleLayer.SERVICES,
    ModuleLayer.EVENTS,
    ModuleLayer.COMMANDS,
)


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    """Manifest inmutable de la frontera pública de un módulo funcional."""

    name: ModuleName
    version: ModuleVersion
    layers: tuple[ModuleLayer, ...] = REQUIRED_MODULE_LAYERS

    def __post_init__(self) -> None:
        if len(set(self.layers)) != len(self.layers):
            raise ModuleValidationError("module layers must not contain duplicates")
        missing = tuple(layer for layer in REQUIRED_MODULE_LAYERS if layer not in self.layers)
        if missing:
            names = ", ".join(layer.value for layer in missing)
            raise ModuleValidationError(f"module is missing required layers: {names}")
        if self.layers != REQUIRED_MODULE_LAYERS:
            raise ModuleValidationError("module layers must use the canonical order")

    def logical_values(self) -> tuple[object, ...]:
        """Representación determinista del contrato modular."""
        return (
            self.name.value,
            self.version.value,
            tuple(layer.value for layer in self.layers),
        )


class DomainModule(Protocol):
    """Contrato estructural mínimo para cualquier módulo funcional futuro."""

    @property
    def descriptor(self) -> ModuleDescriptor:
        """Exponer el descriptor inmutable del módulo."""
        ...
