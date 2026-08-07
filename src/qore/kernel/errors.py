"""
errors — Jerarquía base de errores de QORE.

Propósito:
    Establecer la taxonomía inicial de errores del Kernel.

Alcance:
    - ``KernelError`` como raíz.
    - ``DomainError``.
    - ``ValidationError``.
    - ``InfrastructureError``.

Dependencias:
    - Python 3.12.

Restricciones:
    - Sin lógica de negocio ni códigos de error específicos.
"""
from __future__ import annotations


class KernelError(Exception):
    """Excepción base para todos los errores del Kernel de QORE."""

    __slots__ = ()


class DomainError(KernelError):
    """Errores originados en el dominio."""

    __slots__ = ()


class ValidationError(DomainError):
    """Errores de validación de datos o parámetros."""

    __slots__ = ()


class InfrastructureError(KernelError):
    """Errores de infraestructura."""

    __slots__ = ()
