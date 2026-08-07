from __future__ import annotations

from dataclasses import dataclass

from qore.core.configuration import Configuration
from qore.core.engine import CoreEngine
from qore.core.event_bus import EventBus
from qore.core.lifecycle import ApplicationLifecycle
from qore.core.service_registry import ServiceRegistry


@dataclass(frozen=True, slots=True)
class CoreApplication:
    """Root Object inmutable del Core."""

    configuration: Configuration
    service_registry: ServiceRegistry
    event_bus: EventBus
    engine: CoreEngine
    lifecycle: ApplicationLifecycle
