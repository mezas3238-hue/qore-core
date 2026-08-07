from __future__ import annotations

from dataclasses import dataclass, field

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
    _descriptors: tuple[ModuleDescriptor, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        descriptors = tuple(module.descriptor for module in self.modules)
        seen: set[ModuleName] = set()
        for descriptor in descriptors:
            name = descriptor.name
            if name in seen:
                raise DuplicateModuleError(name.value)
            seen.add(name)
        object.__setattr__(self, "_descriptors", descriptors)

    @property
    def descriptors(self) -> tuple[ModuleDescriptor, ...]:
        """Exponer manifests capturados en el momento de composición."""
        return self._descriptors

    def get(self, name: ModuleName) -> DomainModule | None:
        """Resolver un módulo por la identidad capturada al componer."""
        for descriptor, module in zip(self._descriptors, self.modules, strict=True):
            if descriptor.name == name:
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
