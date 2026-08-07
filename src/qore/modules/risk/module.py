from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.functional.decisions import FunctionalDecision
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.risk.contracts import AssessAllocationRiskCommand


class AssessAllocationRiskHandler:
    """Handler puro que evalúa una intención lógica contra RiskPolicy."""

    def handle(
        self,
        command: AssessAllocationRiskCommand,
    ) -> CommandResult[FunctionalDecision]:
        return Success(command.to_decision())


@dataclass(frozen=True, slots=True)
class RiskModule:
    """Foundation componible de Risk Governance de QORE."""

    _handler: AssessAllocationRiskHandler = field(
        default_factory=AssessAllocationRiskHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("risk"),
            version=ModuleVersion("1.0"),
        )

    @property
    def assessment_handler(self) -> AssessAllocationRiskHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(AssessAllocationRiskCommand, self._handler)
        return Success(None)
