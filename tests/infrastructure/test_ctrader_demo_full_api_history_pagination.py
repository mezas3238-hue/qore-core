from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from types import SimpleNamespace

from qore.infrastructure.ctrader_demo_full_api import CTraderDemoFullApi
from qore.kernel.result import Failure, Success


def _bar(opened_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        utcTimestampInMinutes=int(opened_at.timestamp() // 60),
        low=100_000,
        deltaOpen=10,
        deltaHigh=20,
        deltaLow=0,
        deltaClose=15,
    )


class _PagedClient:
    account_id = 42

    def __init__(self) -> None:
        self.fields: list[dict[str, object]] = []

    def request(
        self,
        message_name: str,
        fields: dict[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Success[SimpleNamespace]:
        del client_msg_id, timeout_seconds
        assert message_name == "ProtoOAGetTrendbarsReq"
        self.fields.append(dict(fields))
        if len(self.fields) == 1:
            # Live cTrader DEMO can omit hasMore even though older pages exist.
            return Success(
                SimpleNamespace(
                    trendbar=(
                        _bar(datetime(2026, 10, 2, 11, 58, tzinfo=UTC)),
                        _bar(datetime(2026, 10, 2, 11, 59, tzinfo=UTC)),
                    ),
                )
            )
        return Success(
            SimpleNamespace(
                trendbar=(
                    _bar(datetime(2026, 10, 2, 11, 56, tzinfo=UTC)),
                    _bar(datetime(2026, 10, 2, 11, 57, tzinfo=UTC)),
                ),
                hasMore=False,
            )
        )


class _SecondPageFailureClient(_PagedClient):
    def request(
        self,
        message_name: str,
        fields: dict[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Success[SimpleNamespace] | Failure[RuntimeError]:
        if self.fields:
            self.fields.append(dict(fields))
            return Failure(RuntimeError("transient continuation failure"))
        return super().request(
            message_name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=timeout_seconds,
        )


def _api(client: _PagedClient) -> CTraderDemoFullApi:
    api = object.__new__(CTraderDemoFullApi)
    api._client = client
    api._binding = SimpleNamespace(
        contract=lambda symbol: SimpleNamespace(symbol_id=7)
    )
    api._history = {}
    api._historical_request_lock = Lock()
    api._last_historical_request_at = 0.0
    api._historical_request_interval_seconds = 0.0
    return api


def test_history_preload_pages_backward_when_provider_omits_has_more() -> None:
    client = _PagedClient()
    api = _api(client)

    rows = api._closed_rows("XAUUSD", api.TIMEFRAME_M1, count_hint=3)

    assert len(rows) == 4
    assert [row["utc_time"] for row in rows] == sorted(
        row["utc_time"] for row in rows
    )
    assert len(client.fields) == 2
    assert client.fields[0]["count"] == 64
    assert client.fields[1]["toTimestamp"] < client.fields[0]["toTimestamp"]


def test_history_preload_retains_confirmed_page_when_continuation_fails() -> None:
    client = _SecondPageFailureClient()
    api = _api(client)

    rows = api._closed_rows("XAUUSD", api.TIMEFRAME_M1, count_hint=3)

    assert len(rows) == 2
    assert len(client.fields) == 2
