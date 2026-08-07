from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.trader.contracts import ProduceVirtualTraderAnalysisCommand
from qore.specialist.analysis import SpecialistAnalysis


class ProduceVirtualTraderAnalysisHandler:
    """Pure handler that projects explicit internal input into SpecialistAnalysis."""

    def handle(
        self,
        command: ProduceVirtualTraderAnalysisCommand,
    ) -> CommandResult[SpecialistAnalysis]:
        return Success(command.to_analysis())


@dataclass(frozen=True, slots=True)
class VirtualTraderModule:
    """Composable foundation for QORE Virtual Trader specialists."""

    _handler: ProduceVirtualTraderAnalysisHandler = field(
        default_factory=ProduceVirtualTraderAnalysisHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("virtual-trader"),
            version=ModuleVersion("1.0"),
        )

    @property
    def analysis_handler(self) -> ProduceVirtualTraderAnalysisHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(ProduceVirtualTraderAnalysisCommand, self._handler)
        return Success(None)
