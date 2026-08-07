from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.functional.decisions import FunctionalDecision
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.cibo.contracts import ReviewFunctionalDecisionCommand


class ReviewFunctionalDecisionHandler:
    """Handler puro que proyecta una revisión CIBO a FunctionalDecision."""

    def handle(
        self,
        command: ReviewFunctionalDecisionCommand,
    ) -> CommandResult[FunctionalDecision]:
        return Success(command.to_decision())


@dataclass(frozen=True, slots=True)
class CiboModule:
    """Foundation componible del Chief Investment Business Officer de QORE."""

    _handler: ReviewFunctionalDecisionHandler = field(
        default_factory=ReviewFunctionalDecisionHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("cibo"),
            version=ModuleVersion("1.0"),
        )

    @property
    def review_handler(self) -> ReviewFunctionalDecisionHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(ReviewFunctionalDecisionCommand, self._handler)
        return Success(None)
