from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from qore.domain.modules import (
    REQUIRED_MODULE_LAYERS,
    DomainModule,
    ModuleDescriptor,
    ModuleLayer,
    ModuleName,
    ModuleValidationError,
    ModuleVersion,
)


class ExampleModule:
    def __init__(self) -> None:
        self._descriptor = ModuleDescriptor(
            name=ModuleName("example-module"),
            version=ModuleVersion("1.0"),
        )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return self._descriptor


class TestModuleArchitectureContracts:
    def test_descriptor_contains_canonical_required_layers(self) -> None:
        descriptor = ModuleDescriptor(
            name=ModuleName("portfolio"),
            version=ModuleVersion("1.0"),
        )

        assert descriptor.layers == (
            ModuleLayer.API,
            ModuleLayer.APPLICATION,
            ModuleLayer.DOMAIN,
            ModuleLayer.CONTRACTS,
            ModuleLayer.SERVICES,
            ModuleLayer.EVENTS,
            ModuleLayer.COMMANDS,
        )
        assert descriptor.layers == REQUIRED_MODULE_LAYERS
        assert descriptor.logical_values() == (
            "portfolio",
            "1.0",
            (
                "api",
                "application",
                "domain",
                "contracts",
                "services",
                "events",
                "commands",
            ),
        )

    def test_descriptor_is_immutable(self) -> None:
        descriptor = ModuleDescriptor(
            name=ModuleName("risk"),
            version=ModuleVersion("1.0"),
        )
        with pytest.raises(FrozenInstanceError):
            descriptor.version = ModuleVersion("2.0")  # type: ignore[misc]

    def test_module_name_and_version_are_validated(self) -> None:
        for invalid in ("", "Portfolio", "portfolio_module", "-portfolio"):
            with pytest.raises(ModuleValidationError):
                ModuleName(invalid)
        with pytest.raises(ModuleValidationError):
            ModuleVersion(" ")

    def test_missing_duplicate_or_reordered_layers_are_rejected(self) -> None:
        with pytest.raises(ModuleValidationError):
            ModuleDescriptor(
                name=ModuleName("missing"),
                version=ModuleVersion("1.0"),
                layers=REQUIRED_MODULE_LAYERS[:-1],
            )
        with pytest.raises(ModuleValidationError):
            ModuleDescriptor(
                name=ModuleName("duplicate"),
                version=ModuleVersion("1.0"),
                layers=(*REQUIRED_MODULE_LAYERS, ModuleLayer.API),
            )
        with pytest.raises(ModuleValidationError):
            ModuleDescriptor(
                name=ModuleName("reordered"),
                version=ModuleVersion("1.0"),
                layers=(
                    ModuleLayer.APPLICATION,
                    ModuleLayer.API,
                    *REQUIRED_MODULE_LAYERS[2:],
                ),
            )

    def test_domain_module_protocol_is_structural(self) -> None:
        module: DomainModule = ExampleModule()
        assert module.descriptor.name == ModuleName("example-module")
