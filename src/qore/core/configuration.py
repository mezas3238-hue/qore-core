from __future__ import annotations

from dataclasses import dataclass

from qore.kernel.errors import ValidationError
from qore.kernel.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class Configuration(ValueObject):
    """Configuración inmutable del Core."""

    application_name: str
    mode: str = "GENESIS"

    def __post_init__(self) -> None:
        """Validar los invariantes mínimos de configuración."""
        if not self.application_name.strip():
            raise ValidationError("application_name must not be empty")
