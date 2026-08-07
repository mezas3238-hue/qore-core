import datetime

from qore.kernel.clock import Clock


def test_clock_returns_utc_datetime() -> None:
    now = Clock().now()
    assert isinstance(now, datetime.datetime)
    assert now.tzinfo == datetime.timezone.utc


def test_clock_can_be_subclassed() -> None:
    class FrozenClock(Clock):
        def now(self) -> datetime.datetime:
            return datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)

    clock = FrozenClock()
    assert clock.now() == datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
