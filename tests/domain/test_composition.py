from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from qore.domain.commands import Command, CommandResult
from qore.domain.composition import (
    ComposableDomainModule,
    DomainComposition,
    DuplicateModuleError,
    ModuleCatalog,
    ModuleRegistrationError,
    compose_domain,
)
from qore.domain.message_bus import HandlerRegistry, MessageBus
from qore.domain.modules import DomainModule, ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success


class ExampleModule:
    def __init__(self, name: str) -> None:
        self._descriptor = ModuleDescriptor(
            name=ModuleName(name),
            version=ModuleVersion("1.0"),
        )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return self._descriptor

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        _ = registry
        return Success(None)


class MutableDescriptorModule(ExampleModule):
    def replace_descriptor(self, name: str) -> None:
        self._descriptor = ModuleDescriptor(
            name=ModuleName(name),
            version=ModuleVersion("2.0"),
        )


class ExampleCommandHandler:
    def handle(self, command: Command) -> CommandResult[str]:
        _ = command
        return Success("registered")


class HandlerContributingModule(ExampleModule):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.handler = ExampleCommandHandler()

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(Command, self.handler)
        return Success(None)


class FailingRegistrationModule(ExampleModule):
    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        _ = registry
        return Failure(DomainError("registration failed"))


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

    def test_descriptor_identity_is_snapshotted_at_composition_time(self) -> None:
        module = MutableDescriptorModule("stable")
        catalog = ModuleCatalog(modules=(module,))

        module.replace_descriptor("changed")

        assert catalog.descriptors[0].name == ModuleName("stable")
        assert catalog.descriptors[0].version == ModuleVersion("1.0")
        assert catalog.get(ModuleName("stable")) is module
        assert catalog.get(ModuleName("changed")) is None


class TestDomainCompositionRoot:
    def test_compose_domain_builds_single_registry_and_bus(self) -> None:
        module: ComposableDomainModule = ExampleModule("example")
        composition = compose_domain(modules=(module,))

        assert isinstance(composition, DomainComposition)
        assert isinstance(composition.handler_registry, HandlerRegistry)
        assert isinstance(composition.message_bus, MessageBus)
        assert composition.module_catalog.descriptors[0].name == ModuleName("example")

    def test_module_handlers_are_registered_during_composition(self) -> None:
        module = HandlerContributingModule("handlers")

        composition = compose_domain(modules=(module,))

        assert composition.handler_registry.command_handler(Command) is module.handler

    def test_registration_failure_aborts_composition(self) -> None:
        with pytest.raises(ModuleRegistrationError, match="registration failed"):
            compose_domain(modules=(FailingRegistrationModule("failing"),))

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
