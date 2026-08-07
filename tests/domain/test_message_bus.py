from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.domain.commands import (
    Command,
    CommandId,
    CommandMetadata,
    CommandName,
    CommandResult,
)
from qore.domain.events import (
    BusinessDomainEvent,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.domain.message_bus import (
    CommandHandlerNotFoundError,
    DomainEventHandler,
    DuplicateCommandHandlerError,
    HandlerExecutionError,
    HandlerRegistry,
    Message,
    MessageBus,
    MessageBusValidationError,
    MessageMiddleware,
    MessageResult,
    RetryDecision,
    RetryPolicy,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

TIMESTAMP = datetime(2026, 1, 5, tzinfo=UTC)
CORRELATION_ID = CorrelationId(UUID("00000000-0000-0000-0000-000000000502"))


def command() -> Command:
    return Command(
        command_id=CommandId(UUID("00000000-0000-0000-0000-000000000501")),
        timestamp=TIMESTAMP,
        name=CommandName("qore.test.execute"),
        metadata=CommandMetadata(correlation_id=CORRELATION_ID),
    )


def event() -> BusinessDomainEvent:
    return BusinessDomainEvent(
        timestamp=TIMESTAMP,
        event_name="qore.test.completed",
        event_id=DomainEventId(UUID("00000000-0000-0000-0000-000000000503")),
        event_version=DomainEventVersion("1.0"),
        metadata=DomainEventMetadata(
            category=DomainEventCategory("test"),
            correlation_id=CORRELATION_ID,
        ),
    )


class ExampleCommandHandler:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def handle(self, value: Command) -> CommandResult[str]:
        self.calls.append(value.name.value)
        return Success("done")


class FailingCommandHandler:
    def handle(self, value: Command) -> CommandResult[str]:
        _ = value
        raise RuntimeError("boom")


class ExampleEventHandler:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def handle(self, value: BusinessDomainEvent) -> Result[None, DomainError]:
        _ = value
        self.calls.append(self.name)
        return Success(None)


class FailingEventHandler:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def handle(self, value: BusinessDomainEvent) -> Result[None, DomainError]:
        _ = value
        self.calls.append("fail")
        return Failure(DomainError("stop"))


class RecordingMiddleware:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls

    def before(self, message: Message) -> Result[None, DomainError]:
        _ = message
        self.calls.append(f"before:{self.name}")
        return Success(None)

    def after(self, message: Message, result: MessageResult) -> None:
        _ = message, result
        self.calls.append(f"after:{self.name}")


class BlockingMiddleware:
    def __init__(self, calls: list[str] | None = None) -> None:
        self.calls = calls

    def before(self, message: Message) -> Result[None, DomainError]:
        _ = message
        if self.calls is not None:
            self.calls.append("before:block")
        return Failure(DomainError("blocked"))

    def after(self, message: Message, result: MessageResult) -> None:
        _ = message, result
        if self.calls is not None:
            self.calls.append("after:block")


class FailingAfterMiddleware:
    def __init__(self, calls: list[str] | None = None) -> None:
        self.calls = calls

    def before(self, message: Message) -> Result[None, DomainError]:
        _ = message
        if self.calls is not None:
            self.calls.append("before:fail-after")
        return Success(None)

    def after(self, message: Message, result: MessageResult) -> None:
        _ = message, result
        if self.calls is not None:
            self.calls.append("after:fail-after")
        raise RuntimeError("after boom")


class NoRetryPolicy:
    def decide(self, *, attempt: int, error: DomainError) -> RetryDecision:
        _ = attempt, error
        return RetryDecision(should_retry=False)


class TestHandlerRegistry:
    def test_command_handler_is_unique(self) -> None:
        registry = HandlerRegistry()
        handler = ExampleCommandHandler([])
        registry.register_command(Command, handler)
        with pytest.raises(DuplicateCommandHandlerError):
            registry.register_command(Command, handler)

    def test_event_handlers_preserve_registration_order(self) -> None:
        calls: list[str] = []
        registry = HandlerRegistry()
        first: DomainEventHandler[BusinessDomainEvent] = ExampleEventHandler("first", calls)
        second: DomainEventHandler[BusinessDomainEvent] = ExampleEventHandler("second", calls)
        registry.register_event(BusinessDomainEvent, first)
        registry.register_event(BusinessDomainEvent, second)
        assert registry.event_handlers(BusinessDomainEvent) == (first, second)


class TestMessageBus:
    def test_command_dispatch_returns_typed_result(self) -> None:
        calls: list[str] = []
        registry = HandlerRegistry()
        registry.register_command(Command, ExampleCommandHandler(calls))
        bus = MessageBus(registry=registry)
        result: CommandResult[str] = bus.dispatch_command(command())
        assert isinstance(result, Success)
        assert result.value == "done"
        assert calls == ["qore.test.execute"]

    def test_missing_command_handler_is_explicit_failure(self) -> None:
        bus = MessageBus(registry=HandlerRegistry())
        result: CommandResult[str] = bus.dispatch_command(command())
        assert isinstance(result, Failure)
        assert isinstance(result.error, CommandHandlerNotFoundError)

    def test_unrepresented_handler_exception_is_normalized(self) -> None:
        registry = HandlerRegistry()
        registry.register_command(Command, FailingCommandHandler())
        bus = MessageBus(registry=registry)
        result: CommandResult[str] = bus.dispatch_command(command())
        assert isinstance(result, Failure)
        assert isinstance(result.error, HandlerExecutionError)

    def test_event_handlers_run_in_order_and_stop_on_first_failure(self) -> None:
        calls: list[str] = []
        registry = HandlerRegistry()
        registry.register_event(BusinessDomainEvent, ExampleEventHandler("first", calls))
        registry.register_event(BusinessDomainEvent, FailingEventHandler(calls))
        registry.register_event(BusinessDomainEvent, ExampleEventHandler("third", calls))
        result = MessageBus(registry=registry).publish_event(event())
        assert isinstance(result, Failure)
        assert calls == ["first", "fail"]

    def test_middleware_before_and_after_have_stable_nested_order(self) -> None:
        calls: list[str] = []
        registry = HandlerRegistry()
        registry.register_command(Command, ExampleCommandHandler(calls))
        first: MessageMiddleware = RecordingMiddleware("first", calls)
        second: MessageMiddleware = RecordingMiddleware("second", calls)
        bus = MessageBus(registry=registry, middleware=(first, second))
        result: CommandResult[str] = bus.dispatch_command(command())
        assert isinstance(result, Success)
        assert calls == [
            "before:first",
            "before:second",
            "qore.test.execute",
            "after:second",
            "after:first",
        ]

    def test_failing_before_middleware_prevents_handler_execution(self) -> None:
        calls: list[str] = []
        registry = HandlerRegistry()
        registry.register_command(Command, ExampleCommandHandler(calls))
        bus = MessageBus(registry=registry, middleware=(BlockingMiddleware(),))
        result: CommandResult[str] = bus.dispatch_command(command())
        assert isinstance(result, Failure)
        assert str(result.error) == "blocked"
        assert calls == []

    def test_entered_middleware_is_finalized_when_later_before_blocks(self) -> None:
        calls: list[str] = []
        registry = HandlerRegistry()
        registry.register_command(Command, ExampleCommandHandler(calls))
        first: MessageMiddleware = RecordingMiddleware("first", calls)
        blocker: MessageMiddleware = BlockingMiddleware(calls)
        bus = MessageBus(registry=registry, middleware=(first, blocker))
        result: CommandResult[str] = bus.dispatch_command(command())
        assert isinstance(result, Failure)
        assert calls == ["before:first", "before:block", "after:first"]

    def test_failing_after_middleware_is_normalized_after_success(self) -> None:
        registry = HandlerRegistry()
        registry.register_command(Command, ExampleCommandHandler([]))
        bus = MessageBus(registry=registry, middleware=(FailingAfterMiddleware(),))
        result: CommandResult[str] = bus.dispatch_command(command())
        assert isinstance(result, Failure)
        assert isinstance(result.error, HandlerExecutionError)

    def test_outer_finalizers_still_run_after_inner_finalizer_fails(self) -> None:
        calls: list[str] = []
        registry = HandlerRegistry()
        registry.register_command(Command, ExampleCommandHandler(calls))
        outer: MessageMiddleware = RecordingMiddleware("outer", calls)
        inner: MessageMiddleware = FailingAfterMiddleware(calls)
        bus = MessageBus(registry=registry, middleware=(outer, inner))

        result: CommandResult[str] = bus.dispatch_command(command())

        assert isinstance(result, Failure)
        assert isinstance(result.error, HandlerExecutionError)
        assert calls == [
            "before:outer",
            "before:fail-after",
            "qore.test.execute",
            "after:fail-after",
            "after:outer",
        ]


class TestRetryContracts:
    def test_retry_policy_is_structural_and_decision_is_pure(self) -> None:
        policy: RetryPolicy = NoRetryPolicy()
        decision = policy.decide(attempt=1, error=DomainError("x"))
        assert decision == RetryDecision(should_retry=False)

    def test_retry_decision_rejects_contradictory_state(self) -> None:
        with pytest.raises(MessageBusValidationError):
            RetryDecision(should_retry=True)
        with pytest.raises(MessageBusValidationError):
            RetryDecision(should_retry=False, next_attempt=2)
