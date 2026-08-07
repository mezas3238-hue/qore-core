from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.portfolio.contracts import AllocationIntent, CreateAllocationIntentCommand


class CreateAllocationIntentHandler:
    """Handler puro que proyecta una decisión aprobada a una intención lógica."""

    def handle(
        self,
        command: CreateAllocationIntentCommand,
    ) -> CommandResult[AllocationIntent]:
        return Success(command.to_intent())


@dataclass(frozen=True, slots=True)
class PortfolioModule:
    """Foundation componible del Portfolio Manager de QORE."""

    _handler: CreateAllocationIntentHandler = field(
        default_factory=CreateAllocationIntentHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("portfolio"),
            version=ModuleVersion("1.0"),
        )

    @property
    def allocation_handler(self) -> CreateAllocationIntentHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(CreateAllocationIntentCommand, self._handler)
        return Success(None)
