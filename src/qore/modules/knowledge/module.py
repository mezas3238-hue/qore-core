from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.knowledge.contracts import (
    CaptureStatisticsKnowledgeCommand,
    KnowledgeRecord,
)


class CaptureStatisticsKnowledgeHandler:
    """Pure handler projecting explicit statistics into structured knowledge."""

    def handle(
        self,
        command: CaptureStatisticsKnowledgeCommand,
    ) -> CommandResult[KnowledgeRecord]:
        return Success(command.to_record())


@dataclass(frozen=True, slots=True)
class KnowledgeServiceModule:
    """Composable Knowledge Service foundation."""

    _handler: CaptureStatisticsKnowledgeHandler = field(
        default_factory=CaptureStatisticsKnowledgeHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("knowledge"),
            version=ModuleVersion("1.0"),
        )

    @property
    def knowledge_handler(self) -> CaptureStatisticsKnowledgeHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(CaptureStatisticsKnowledgeCommand, self._handler)
        return Success(None)
