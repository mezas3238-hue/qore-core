from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from qore.domain.commands import Command, CommandHandler, CommandResult
from qore.domain.events import BusinessDomainEvent
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success

type Message = Command | BusinessDomainEvent
type MessageResult = Result[object | None, DomainError]


class MessageBusError(DomainError):
    """Error base del message bus interno de dominio."""

    __slots__ = ()


class MessageBusValidationError(MessageBusError):
    """Configuración o decisión inválida del message bus."""

    __slots__ = ()


class DuplicateCommandHandlerError(MessageBusError):
    """Un comando intentó registrar más de un handler."""

    __slots__ = ()


class CommandHandlerNotFoundError(MessageBusError):
    """No existe handler registrado para el tipo concreto del comando."""

    __slots__ = ()


class HandlerExecutionError(MessageBusError):
    """Un handler o middleware lanzó una excepción no representada."""

    __slots__ = ()


class DomainEventHandler[E: BusinessDomainEvent](Protocol):
    """Handler tipado de eventos de negocio."""

    def handle(self, event: E) -> Result[None, DomainError]:
        """Procesar un evento de negocio."""
        ...


class MessageMiddleware(Protocol):
    """Middleware síncrono con orden explícito before/after."""

    def before(self, message: Message) -> Result[None, DomainError]:
        """Ejecutar antes del handler o handlers."""
        ...

    def after(self, message: Message, result: MessageResult) -> None:
        """Finalizar únicamente si before terminó con éxito."""
        ...


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Decisión pura de retry sin temporización ni ejecución."""

    should_retry: bool
    next_attempt: int | None = None

    def __post_init__(self) -> None:
        if self.should_retry and (self.next_attempt is None or self.next_attempt < 1):
            raise MessageBusValidationError(
                "retry decision requires a positive next attempt"
            )
        if not self.should_retry and self.next_attempt is not None:
            raise MessageBusValidationError(
                "non-retry decision cannot define next attempt"
            )


class RetryPolicy(Protocol):
    """Contrato puro para decidir si un error admite otro intento."""

    def decide(self, *, attempt: int, error: DomainError) -> RetryDecision:
        """Calcular una decisión sin ejecutar waits ni side effects."""
        ...


class HandlerRegistry:
    """Registro determinista de handlers por tipo concreto de mensaje."""

    def __init__(self) -> None:
        self._command_handlers: dict[type[Command], object] = {}
        self._event_handlers: dict[type[BusinessDomainEvent], list[object]] = {}

    def register_command[C: Command, R](
        self,
        command_type: type[C],
        handler: CommandHandler[C, R],
    ) -> None:
        if command_type in self._command_handlers:
            raise DuplicateCommandHandlerError(command_type.__qualname__)
        self._command_handlers[command_type] = handler

    def command_handler[C: Command, R](
        self,
        command_type: type[C],
    ) -> CommandHandler[C, R] | None:
        handler = self._command_handlers.get(command_type)
        if handler is None:
            return None
        return cast(CommandHandler[C, R], handler)

    def register_event[E: BusinessDomainEvent](
        self,
        event_type: type[E],
        handler: DomainEventHandler[E],
    ) -> None:
        self._event_handlers.setdefault(event_type, []).append(handler)

    def event_handlers[E: BusinessDomainEvent](
        self,
        event_type: type[E],
    ) -> tuple[DomainEventHandler[E], ...]:
        handlers = self._event_handlers.get(event_type, [])
        return tuple(cast(DomainEventHandler[E], handler) for handler in handlers)


class MessageBus:
    """Dispatcher interno, síncrono y determinista de mensajes de negocio."""

    def __init__(
        self,
        *,
        registry: HandlerRegistry,
        middleware: tuple[MessageMiddleware, ...] = (),
    ) -> None:
        self._registry = registry
        self._middleware = middleware

    def dispatch_command[C: Command, R](self, command: C) -> CommandResult[R]:
        entered, before = self._run_before(command)
        if isinstance(before, Failure):
            self._run_after(command, cast(MessageResult, before), entered)
            return Failure(before.error)

        handler: CommandHandler[C, R] | None = self._registry.command_handler(
            type(command)
        )
        if handler is None:
            result: CommandResult[R] = Failure(
                CommandHandlerNotFoundError(type(command).__qualname__)
            )
        else:
            try:
                result = handler.handle(command)
            except Exception as exc:
                result = Failure(HandlerExecutionError(str(exc)))

        after = self._run_after(command, cast(MessageResult, result), entered)
        if isinstance(result, Success) and isinstance(after, Failure):
            return Failure(after.error)
        return result

    def publish_event[E: BusinessDomainEvent](
        self,
        event: E,
    ) -> Result[None, DomainError]:
        entered, before = self._run_before(event)
        if isinstance(before, Failure):
            self._run_after(event, cast(MessageResult, before), entered)
            return before

        result: Result[None, DomainError] = Success(None)
        for handler in self._registry.event_handlers(type(event)):
            try:
                current = handler.handle(event)
            except Exception as exc:
                current = Failure(HandlerExecutionError(str(exc)))
            if isinstance(current, Failure):
                result = current
                break

        after = self._run_after(event, cast(MessageResult, result), entered)
        if isinstance(result, Success) and isinstance(after, Failure):
            return Failure(after.error)
        return result

    def _run_before(
        self,
        message: Message,
    ) -> tuple[tuple[MessageMiddleware, ...], Result[None, DomainError]]:
        entered: list[MessageMiddleware] = []
        for middleware in self._middleware:
            try:
                result = middleware.before(message)
            except Exception as exc:
                return tuple(entered), Failure(HandlerExecutionError(str(exc)))
            if isinstance(result, Failure):
                return tuple(entered), result
            entered.append(middleware)
        return tuple(entered), Success(None)

    def _run_after(
        self,
        message: Message,
        result: MessageResult,
        middleware: tuple[MessageMiddleware, ...],
    ) -> Result[None, DomainError]:
        first_error: DomainError | None = None
        for item in reversed(middleware):
            try:
                item.after(message, result)
            except Exception as exc:
                if first_error is None:
                    first_error = HandlerExecutionError(str(exc))
        if first_error is not None:
            return Failure(first_error)
        return Success(None)
