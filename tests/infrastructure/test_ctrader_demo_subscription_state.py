from __future__ import annotations

from types import SimpleNamespace
from threading import Lock

from qore.infrastructure.ctrader_demo_full_api import (
    CTraderDemoFullApi,
    CTraderDemoMarketDataState,
)
from qore.kernel.result import Success


class ReadyClient:
    account_id = 424242
    is_ready = True

    def __init__(self) -> None:
        self.requests: list[tuple[str, str]] = []

    def request(
        self,
        message_name,
        fields,
        *,
        client_msg_id,
        timeout_seconds,
    ):
        del fields, timeout_seconds
        self.requests.append((message_name, client_msg_id))
        return Success(SimpleNamespace())


def _api(client: ReadyClient) -> CTraderDemoFullApi:
    api = object.__new__(CTraderDemoFullApi)
    api._client = client
    api._binding = SimpleNamespace(
        contracts=(
            SimpleNamespace(symbol_id=1),
            SimpleNamespace(symbol_id=2),
        )
    )
    api._conversion_symbol_id = None
    api._subscription_lock = Lock()
    api._market_data_state = CTraderDemoMarketDataState.DEGRADED
    api._last_subscription_attempt = 0.0
    api._subscription_generation = 0
    api._connected = True
    return api


def test_subscription_repair_is_stateful_and_storm_guarded() -> None:
    client = ReadyClient()
    api = _api(client)

    assert api.repair_market_data_subscription() is True
    assert api.market_data_state is CTraderDemoMarketDataState.REHYDRATING
    assert client.requests == [
        (
            "ProtoOASubscribeSpotsReq",
            "qore-demo-repair-spots-1",
        )
    ]

    assert api.repair_market_data_subscription() is True
    assert len(client.requests) == 1


def test_subscription_repair_rejects_parallel_storm() -> None:
    client = ReadyClient()
    api = _api(client)
    api._market_data_state = CTraderDemoMarketDataState.RESUBSCRIBING
    assert api._subscription_lock.acquire(blocking=False)
    try:
        assert api.repair_market_data_subscription() is True
        assert client.requests == []
    finally:
        api._subscription_lock.release()
