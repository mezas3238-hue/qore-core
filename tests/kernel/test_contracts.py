from qore.kernel.contracts import EventHandler, EventPublisher, Repository
from qore.kernel.domain_event import DomainEvent


class DummyPublisher:
    def publish(self, event: DomainEvent) -> None:
        return None


class DummyHandler:
    def handle(self, event: DomainEvent) -> None:
        return None


class DummyRepository:
    def load(self, id: int) -> str | None:
        return None

    def save(self, entity: str) -> None:
        return None


def test_event_publisher_protocol_conformance() -> None:
    publisher: EventPublisher = DummyPublisher()
    assert publisher is not None


def test_event_handler_protocol_conformance() -> None:
    handler: EventHandler = DummyHandler()
    assert handler is not None


def test_repository_protocol_conformance() -> None:
    repository: Repository[str, int] = DummyRepository()
    assert repository.load(1) is None
