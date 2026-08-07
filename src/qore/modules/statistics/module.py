from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.statistics.contracts import (
    StatisticsSnapshot,
    SummarizeValidationAssessmentsCommand,
)


class SummarizeValidationAssessmentsHandler:
    """Pure handler producing deterministic descriptive statistics."""

    def handle(
        self,
        command: SummarizeValidationAssessmentsCommand,
    ) -> CommandResult[StatisticsSnapshot]:
        return Success(command.to_snapshot())


@dataclass(frozen=True, slots=True)
class StatisticsServiceModule:
    """Composable Statistics Service foundation."""

    _handler: SummarizeValidationAssessmentsHandler = field(
        default_factory=SummarizeValidationAssessmentsHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("statistics"),
            version=ModuleVersion("1.0"),
        )

    @property
    def statistics_handler(self) -> SummarizeValidationAssessmentsHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(SummarizeValidationAssessmentsCommand, self._handler)
        return Success(None)
