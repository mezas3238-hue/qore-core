from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.domain.commands import (
    Command,
    CommandHandler,
    CommandId,
    CommandMetadata,
    CommandName,
    CommandResult,
    CommandValidationError,
    IdempotencyKey,
)
from qore.domain.events import CausationId, CorrelationId, DomainMetadataValue
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Success

COMMAND_ID = CommandId(UUID("00000000-0000-0000-0000-000000000201"))
CORRELATION_ID = CorrelationId(UUID("00000000-0000-0000-0000-000000000202"))
CAUSATION_ID = CausationId(UUID("00000000-0000-0000-0000-000000000203"))
TIMESTAMP = datetime(2026, 1, 2, tzinfo=UTC)


def command() -> Command:
    return Command(
        command_id=COMMAND_ID,
        timestamp=TIMESTAMP,
        name=CommandName("qore.portfolio.create"),
        metadata=CommandMetadata(
            correlation_id=CORRELATION_ID,
            causation_id=CAUSATION_ID,
            idempotency_key=IdempotencyKey("portfolio:create:1"),
            attributes={"aggregate": "portfolio-1", "attempt": 1},
        ),
    )


class TestCommandContracts:
    def test_command_is_explicit_immutable_and_deterministic(self) -> None:
        value = command()
        assert value.command_id == COMMAND_ID
        assert value.timestamp == TIMESTAMP
        assert value.name == CommandName("qore.portfolio.create")
        assert value.metadata.correlation_id == CORRELATION_ID
        assert value.metadata.causation_id == CAUSATION_ID
        assert value.metadata.idempotency_key == IdempotencyKey("portfolio:create:1")
        assert value.logical_values() == command().logical_values()
        with pytest.raises(FrozenInstanceError):
            value.name = CommandName("other")  # type: ignore[misc]

    def test_metadata_is_defensively_copied_sorted_and_read_only(self) -> None:
        attributes = {"b": 2, "a": 1}
        metadata = CommandMetadata(correlation_id=CORRELATION_ID, attributes=attributes)
        attributes["c"] = 3
        assert tuple(metadata.attributes) == ("a", "b")
        assert "c" not in metadata.attributes
        with pytest.raises(TypeError):
            metadata.attributes["x"] = 1  # type: ignore[index]

    def test_reserved_metadata_keys_are_rejected(self) -> None:
        for reserved in ("correlation_id", "causation_id", "idempotency_key"):
            with pytest.raises(CommandValidationError):
                CommandMetadata(
                    correlation_id=CORRELATION_ID,
                    attributes={reserved: "forged"},
                )

    def test_mutable_or_nondeterministic_metadata_values_are_rejected(self) -> None:
        invalid_values: tuple[object, ...] = (
            ["mutable"],
            {"nested": "mapping"},
            {"unordered"},
            ("valid-prefix", ["nested-mutable"]),
            float("nan"),
            float("inf"),
        )
        for invalid in invalid_values:
            unsafe = cast(Mapping[str, DomainMetadataValue], {"value": invalid})
            with pytest.raises(CommandValidationError):
                CommandMetadata(correlation_id=CORRELATION_ID, attributes=unsafe)

    def test_empty_values_use_uniform_command_validation_error(self) -> None:
        with pytest.raises(CommandValidationError):
            CommandName(" ")
        with pytest.raises(CommandValidationError):
            IdempotencyKey("")
        with pytest.raises(CommandValidationError):
            CommandMetadata(
                correlation_id=CORRELATION_ID,
                attributes={" ": "invalid"},
            )

    def test_causation_and_idempotency_are_optional(self) -> None:
        metadata = CommandMetadata(correlation_id=CORRELATION_ID)
        assert metadata.causation_id is None
        assert metadata.idempotency_key is None

    def test_constructor_requires_identity_timestamp_name_and_metadata(self) -> None:
        with pytest.raises(TypeError):
            Command(  # type: ignore[call-arg]
                timestamp=TIMESTAMP,
                name=CommandName("qore.test.command"),
                metadata=CommandMetadata(correlation_id=CORRELATION_ID),
            )


class ExampleError(DomainError):
    pass


class ExampleHandler:
    def handle(self, command: Command) -> CommandResult[str]:
        if command.name.value == "qore.portfolio.create":
            return Success("accepted")
        return Failure(ExampleError("rejected"))


class TestCommandHandlerContracts:
    def test_handler_protocol_accepts_success_and_failure_results(self) -> None:
        handler: CommandHandler[Command, str] = ExampleHandler()
        success = handler.handle(command())
        failure = handler.handle(
            Command(
                command_id=COMMAND_ID,
                timestamp=TIMESTAMP,
                name=CommandName("qore.portfolio.reject"),
                metadata=CommandMetadata(correlation_id=CORRELATION_ID),
            )
        )
        assert isinstance(success, Success)
        assert success.value == "accepted"
        assert isinstance(failure, Failure)
        assert isinstance(failure.error, ExampleError)
