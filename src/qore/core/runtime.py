from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from qore.kernel.errors import KernelError, ValidationError
from qore.kernel.result import Result


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    """Contexto inmutable que identifica una ejecución del Core."""

    execution_id: UUID
    runtime_version: str

    def __post_init__(self) -> None:
        """Validar los invariantes mínimos del contexto de ejecución."""
        if not self.runtime_version.strip():
            raise ValidationError("runtime_version must not be empty")


class RuntimeComponent(Protocol):
    """Contrato mínimo para componentes gobernados por el runtime."""

    @property
    def component_name(self) -> str:
        """Nombre estable del componente."""
        ...

    def start(self) -> Result[None, KernelError]:
        """Iniciar el componente."""
        ...

    def stop(self) -> Result[None, KernelError]:
        """Detener el componente."""
        ...
