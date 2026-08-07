"""Minimal executable bootstrap for QORE Genesis."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoreIdentity:
    """Immutable identity returned when the QORE Core foundation starts."""

    name: str
    version: str
    mode: str


def bootstrap() -> CoreIdentity:
    """Return the immutable identity of the Genesis foundation."""

    return CoreIdentity(name="QORE", version="0.1.0", mode="GENESIS")
