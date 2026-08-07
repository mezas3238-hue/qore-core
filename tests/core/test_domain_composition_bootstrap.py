from __future__ import annotations

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.composition import DomainComposition
from qore.domain.message_bus import HandlerRegistry, MessageBus
from qore.domain.modules import DomainModule, ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.result import Failure, Success


class ExampleModule:
    def __init__(self, name: str) -> None:
        self._descriptor = ModuleDescriptor(
            name=ModuleName(name),
            version=ModuleVersion("1.0"),
        )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return self._descriptor


class TestDomainCompositionBootstrap:
    def test_bootstrap_exposes_empty_domain_composition_by_default(self) -> None:
        result = bootstrap(Configuration(application_name="test-app"))

        assert isinstance(result, Success)
        assert isinstance(result.value.domain, DomainComposition)
        assert isinstance(result.value.domain.handler_registry, HandlerRegistry)
        assert isinstance(result.value.domain.message_bus, MessageBus)
        assert result.value.domain.module_catalog.modules == ()

    def test_bootstrap_composes_modules_in_declared_order(self) -> None:
        first: DomainModule = ExampleModule("first")
        second: DomainModule = ExampleModule("second")

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
        module: DomainModule = ExampleModule("isolated-domain")
        result = bootstrap(
            Configuration(application_name="test-app"),
            domain_modules=(module,),
        )

        assert isinstance(result, Success)
        assert len(result.value.runtime_plan.components) == 1
        assert result.value.runtime_plan.components[0].component is result.value.engine

    def test_duplicate_modules_fail_during_bootstrap(self) -> None:
        first: DomainModule = ExampleModule("duplicate")
        second: DomainModule = ExampleModule("duplicate")

        try:
            bootstrap(
                Configuration(application_name="test-app"),
                domain_modules=(first, second),
            )
        except Exception as exc:
            assert exc.__class__.__name__ == "DuplicateModuleError"
        else:
            raise AssertionError("duplicate domain modules must be rejected")

    def test_genesis_bootstrap_remains_unchanged(self) -> None:
        identity = bootstrap()
        assert identity.name == "QORE"
        assert identity.version == "0.1.0"
        assert identity.mode == "GENESIS"

    def test_domain_modules_without_configuration_are_rejected(self) -> None:
        module: DomainModule = ExampleModule("example")
        result = bootstrap(domain_modules=(module,))
        assert isinstance(result, Failure)
