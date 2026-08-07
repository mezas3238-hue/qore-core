from __future__ import annotations

from dataclasses import dataclass

from qore.domain.message_bus import HandlerRegistry, MessageBus, MessageMiddleware
from qore.domain.modules import DomainModule, ModuleDescriptor, ModuleName
from qore.kernel.errors import DomainError


class DomainCompositionError(DomainError):
    """Error base de composición del dominio."""

    __slots__ = ()


class DuplicateModuleError(DomainCompositionError):
    """Dos módulos declararon el mismo nombre lógico."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ModuleCatalog:
    """Catálogo inmutable y determinista de módulos funcionales."""

    modules: tuple[DomainModule, ...] = ()

    def __post_init__(self) -> None:
        seen: set[ModuleName] = set()
        for module in self.modules:
            name = module.descriptor.name
            if name in seen:
                raise DuplicateModuleError(name.value)
            seen.add(name)

    @property
    def descriptors(self) -> tuple[ModuleDescriptor, ...]:
        """Exponer manifests en el mismo orden estable de composición."""
        return tuple(module.descriptor for module in self.modules)

    def get(self, name: ModuleName) -> DomainModule | None:
        """Resolver un módulo por identidad lógica sin efectos laterales."""
        for module in self.modules:
            if module.descriptor.name == name:
                return module
        return None


@dataclass(frozen=True, slots=True)
class DomainComposition:
    """Root de composición del dominio sin lifecycle ni infraestructura."""

    module_catalog: ModuleCatalog
    handler_registry: HandlerRegistry
    message_bus: MessageBus


def compose_domain(
    *,
    modules: tuple[DomainModule, ...] = (),
    middleware: tuple[MessageMiddleware, ...] = (),
) -> DomainComposition:
    """Construir de forma determinista la topología interna del dominio."""
    module_catalog = ModuleCatalog(modules=modules)
    handler_registry = HandlerRegistry()
    message_bus = MessageBus(registry=handler_registry, middleware=middleware)
    return DomainComposition(
        module_catalog=module_catalog,
        handler_registry=handler_registry,
        message_bus=message_bus,
    )
