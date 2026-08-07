from __future__ import annotations

from dataclasses import dataclass, field

from qore.domain.commands import CommandResult
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleDescriptor, ModuleName, ModuleVersion
from qore.kernel.errors import DomainError
from qore.kernel.result import Result, Success
from qore.modules.validation.contracts import (
    ValidateSpecialistAnalysisCommand,
    ValidationAssessment,
)


class ValidateSpecialistAnalysisHandler:
    """Pure handler evaluating one specialist analysis under an explicit policy."""

    def handle(
        self,
        command: ValidateSpecialistAnalysisCommand,
    ) -> CommandResult[ValidationAssessment]:
        return Success(command.to_assessment())


@dataclass(frozen=True, slots=True)
class ValidationLabModule:
    """Composable deterministic Validation Lab foundation."""

    _handler: ValidateSpecialistAnalysisHandler = field(
        default_factory=ValidateSpecialistAnalysisHandler
    )

    @property
    def descriptor(self) -> ModuleDescriptor:
        return ModuleDescriptor(
            name=ModuleName("validation-lab"),
            version=ModuleVersion("1.0"),
        )

    @property
    def validation_handler(self) -> ValidateSpecialistAnalysisHandler:
        return self._handler

    def register_handlers(
        self,
        registry: HandlerRegistry,
    ) -> Result[None, DomainError]:
        registry.register_command(ValidateSpecialistAnalysisCommand, self._handler)
        return Success(None)
