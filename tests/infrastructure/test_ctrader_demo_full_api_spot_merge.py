from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from threading import Event, Lock
from types import SimpleNamespace

from qore.infrastructure.ctrader_demo_full_api import CTraderDemoFullApi
from qore.kernel.result import Success


class _SpotClient:
    def __init__(self, events: list[SimpleNamespace]) -> None:
        self.events = list(events)
        self.calls = 0

    @property
    def is_ready(self) -> bool:
        return self.calls < len(self.events)

    def wait_for_event(self, message_name: str, *, timeout_seconds: float):
        assert message_name == "ProtoOASpotEvent"
        assert timeout_seconds == 1.0
        event = self.events[self.calls]
        self.calls += 1
        return Success(event)


def _api(events: list[SimpleNamespace]) -> CTraderDemoFullApi:
    api = object.__new__(CTraderDemoFullApi)
    api._client = _SpotClient(events)
    api._stop = Event()
    api._spot_lock = Lock()
    api._spots = {}
    return api


def test_one_sided_ask_update_preserves_last_valid_bid() -> None:
    ts = int(datetime(2026, 9, 24, 19, 0, tzinfo=UTC).timestamp() * 1000)
    api = _api(
        [
            SimpleNamespace(symbolId=11, bid=113700, ask=113710, timestamp=ts),
            SimpleNamespace(symbolId=11, bid=0, ask=113720, timestamp=ts + 10),
        ]
    )

    api._pump_spots()

    bid, ask, _ = api._spots[11]
    assert bid == Decimal("1.137")
    assert ask == Decimal("1.1372")


def test_one_sided_bid_update_preserves_last_valid_ask() -> None:
    ts = int(datetime(2026, 9, 24, 19, 0, tzinfo=UTC).timestamp() * 1000)
    api = _api(
        [
            SimpleNamespace(symbolId=12, bid=132100, ask=132120, timestamp=ts),
            SimpleNamespace(symbolId=12, bid=132110, ask=0, timestamp=ts + 10),
        ]
    )

    api._pump_spots()

    bid, ask, _ = api._spots[12]
    assert bid == Decimal("1.3211")
    assert ask == Decimal("1.3212")


def test_initial_incomplete_quote_is_not_published() -> None:
    ts = int(datetime(2026, 9, 24, 19, 0, tzinfo=UTC).timestamp() * 1000)
    api = _api(
        [SimpleNamespace(symbolId=13, bid=0, ask=100020, timestamp=ts)]
    )

    api._pump_spots()

    assert 13 not in api._spots
