"""
result — Contrato oficial para resultados de operaciones del dominio.

Propósito:
    Definir una representación explícita y tipada de éxito o error.

Alcance:
    - ``Success[T]``.
    - ``Failure[E: KernelError]``.
    - Alias genérico ``Result[T, E]``.

Dependencias:
    - Python 3.12.
    - ``qore.kernel.errors.KernelError``.

Restricciones:
    - Las clases son inmutables.
    - El error debe pertenecer a la jerarquía ``KernelError``.
"""
from __future__ import annotations

from dataclasses import dataclass

from qore.kernel.errors import KernelError


@dataclass(frozen=True, slots=True)
class Success[T]:
    """Resultado exitoso que contiene un valor de tipo T."""

    value: T


@dataclass(frozen=True, slots=True)
class Failure[E: KernelError]:
    """Resultado fallido que contiene un KernelError."""

    error: E


type Result[T, E: KernelError] = Success[T] | Failure[E]
