from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.optimization.contracts import (
    OptimizationProposal,
    ProposeKnowledgeOptimizationCommand,
)


class ProposeKnowledgeOptimizationHandler:
    """Pure handler deriving one optimization proposal from explicit knowledge."""

    def handle(
        self,
        command: ProposeKnowledgeOptimizationCommand,
    ) -> CommandResult[OptimizationProposal]:
        return Success(command.to_proposal())


@dataclass(frozen=True, slots=True)
class OptimizationServiceModule:
    """Composable Optimization Service foundation."""

    _handler: ProposeKnowledgeOptimizationHandler = field(
        default_factory=ProposeKnowledgeOptimizationHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("optimization"),
            version=ModuleVersion("1.0"),
        )

    @property
    def optimization_handler(self) -> ProposeKnowledgeOptimizationHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(ProposeKnowledgeOptimizationCommand, self._handler)
        return Success(None)
