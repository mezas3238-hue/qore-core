from __future__ import annotations

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.composition import (
    ComposableDomainModule,
    DomainComposition,
    DuplicateModuleError,
    ModuleRegistrationError,
)
from qore.domain.message_bus import HandlerRegistry, MessageBus
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
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


class FailingModule(ExampleModule):
    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        _ = registry
        return Failure(DomainError("cannot register"))


class TestDomainCompositionBootstrap:
    def test_bootstrap_exposes_empty_domain_composition_by_default(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))

        assert isinstance(result, Success)
        assert isinstance(result.value.domain, DomainComposition)
        assert isinstance(result.value.domain.handler_registry, HandlerRegistry)
        assert isinstance(result.value.domain.message_bus, MessageBus)
        assert result.value.domain.module_catalog.modules == ()

    def test_bootstrap_composes_modules_in_declared_order(self) -> None:
        first: ComposableDomainModule = ExampleModule("first")
        second: ComposableDomainModule = ExampleModule("second")

        result = bootstrap(
            Configuration(application_name="test-app"),
            domain_modules=(first, second),
        )

        assert isinstance(result, Success)
        assert result.value.domain.module_catalog.modules == (first, second)
        assert tuple(
            descriptor.name.value
            for descriptor in result.value.domain.module_catalog.descriptors
        ) == ("first", "second")

    def test_domain_modules_do_not_enter_runtime_plan(self) -> None:
        module: ComposableDomainModule = ExampleModule("isolated-domain")
        result = bootstrap(
            Configuration(application_name="test-app"),
            domain_modules=(module,),
        )

        assert isinstance(result, Success)
        assert len(result.value.runtime_plan.components) == 1
        assert result.value.runtime_plan.components[0].component is result.value.engine

    def test_duplicate_modules_fail_during_bootstrap(self) -> None:
        first: ComposableDomainModule = ExampleModule("duplicate")
        second: ComposableDomainModule = ExampleModule("duplicate")

        result = bootstrap(
            Configuration(application_name="test-app"),
            domain_modules=(first, second),
        )

        assert isinstance(result, Failure)
        assert isinstance(result.error, DuplicateModuleError)

    def test_module_registration_failure_is_normalized_by_bootstrap(self) -> None:
        module: ComposableDomainModule = FailingModule("failing")

        result = bootstrap(
            Configuration(application_name="test-app"),
            domain_modules=(module,),
        )

        assert isinstance(result, Failure)
        assert isinstance(result.error, ModuleRegistrationError)
        assert "cannot register" in str(result.error)

    def test_genesis_bootstrap_remains_unchanged(self) -> None:
        identity = bootstrap()
        assert identity.name == "QORE"
        assert identity.version == "0.1.0"
        assert identity.mode == "GENESIS"
