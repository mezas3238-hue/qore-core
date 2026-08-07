from __future__ import annotations

from dataclasses import dataclass

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.functional.decisions import FunctionalDecision
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.cio.contracts import CreateCioDecisionCommand


class CreateCioDecisionHandler:
    """Handler puro que convierte una solicitud explícita en FunctionalDecision."""

    def handle(
        self,
        command: CreateCioDecisionCommand,
    ) -> CommandResult[FunctionalDecision]:
        return Success(command.to_decision())


@dataclass(frozen=True, slots=True)
class CioModule:
    """Foundation componible del Chief Investment Officer de QORE."""

    _handler: CreateCioDecisionHandler = CreateCioDecisionHandler()

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("cio"),
            version=ModuleVersion("1.0"),
        )

    @property
    def decision_handler(self) -> CreateCioDecisionHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(CreateCioDecisionCommand, self._handler)
        return Success(None)
