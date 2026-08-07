from datetime import UTC, datetime

from qore.kernel.clock import Clock


def test_clock_returns_utc_datetime() -> None:
    now = Clock().now()
    assert isinstance(now, datetime)
    assert now.tzinfo == UTC


def test_clock_can_be_subclassed() -> None:
    class FrozenClock(Clock):
        def now(self) -> datetime:
            return datetime(2026, 1, 1, tzinfo=UTC)

    clock = FrozenClock()
    assert clock.now() == datetime(2026, 1, 1, tzinfo=UTC)
