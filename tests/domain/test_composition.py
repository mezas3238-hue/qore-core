from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from qore.domain.composition import (
    DomainComposition,
    DuplicateModuleError,
    ModuleCatalog,
    compose_domain,
)
from qore.domain.message_bus import HandlerRegistry, MessageBus
from qore.domain.modules import DomainModule, ModuleDescriptor, ModuleName, ModuleVersion


class ExampleModule:
    def __init__(self, name: str) -> None:
        self._descriptor = ModuleDescriptor(
            name=ModuleName(name),
            version=ModuleVersion("1.0"),
        )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return self._descriptor


class TestModuleCatalog:
    def test_preserves_composition_order_and_resolves_by_name(self) -> None:
        first: DomainModule = ExampleModule("first")
        second: DomainModule = ExampleModule("second")
        catalog = ModuleCatalog(modules=(first, second))

        assert catalog.modules == (first, second)
        assert catalog.descriptors == (first.descriptor, second.descriptor)
        assert catalog.get(ModuleName("first")) is first
        assert catalog.get(ModuleName("missing")) is None

    def test_duplicate_module_names_are_rejected(self) -> None:
        with pytest.raises(DuplicateModuleError):
            ModuleCatalog(
                modules=(ExampleModule("duplicate"), ExampleModule("duplicate"))
            )

    def test_catalog_is_immutable(self) -> None:
        catalog = ModuleCatalog(modules=(ExampleModule("example"),))
        with pytest.raises(FrozenInstanceError):
            catalog.modules = ()  # type: ignore[misc]


class TestDomainCompositionRoot:
    def test_compose_domain_builds_single_registry_and_bus(self) -> None:
        composition = compose_domain(modules=(ExampleModule("example"),))

        assert isinstance(composition, DomainComposition)
        assert isinstance(composition.handler_registry, HandlerRegistry)
        assert isinstance(composition.message_bus, MessageBus)
        assert composition.module_catalog.descriptors[0].name == ModuleName("example")

    def test_composition_is_deterministic_for_same_module_topology(self) -> None:
        first = compose_domain(modules=(ExampleModule("first"), ExampleModule("second")))
        second = compose_domain(modules=(ExampleModule("first"), ExampleModule("second")))

        assert first.module_catalog.descriptors == second.module_catalog.descriptors
        assert type(first.handler_registry) is type(second.handler_registry)
        assert type(first.message_bus) is type(second.message_bus)

    def test_empty_composition_is_valid(self) -> None:
        composition = compose_domain()
        assert composition.module_catalog.modules == ()
        assert composition.module_catalog.descriptors == ()
