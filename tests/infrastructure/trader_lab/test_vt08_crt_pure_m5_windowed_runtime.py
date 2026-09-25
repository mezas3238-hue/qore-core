from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import SpotwareCTraderOpenApiClient
from qore.infrastructure.trader_lab.vt08_crt_pure_m5_windowed_runtime import (
    MAX_CALENDAR_M5_BARS_PER_CHUNK,
    read_windowed_chunk,
)


class _FakeClient:
    def __init__(self, bars: tuple[object, ...]) -> None:
        self.bars = bars
        self.payload: dict[str, Any] | None = None

    def request(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> object:
        del client_msg_id, timeout_seconds
        assert name == "ProtoOAGetTrendbarsReq"
        self.payload = payload
        return SimpleNamespace(value=SimpleNamespace(trendbar=self.bars))


def test_windowed_transport_does_not_send_count() -> None:
    fake = _FakeClient((object(), object()))
    opened_at = datetime(2026, 9, 1, tzinfo=UTC)
    closed_at = opened_at + timedelta(days=7)
    result = read_windowed_chunk(
        cast(SpotwareCTraderOpenApiClient, fake),
        account_id=1,
        symbol_id=2,
        opened_at=opened_at,
        closed_at=closed_at,
        client_msg_id="test",
    )
    assert len(result) == 2
    assert fake.payload is not None
    assert "count" not in fake.payload
    assert fake.payload["fromTimestamp"] == int(opened_at.timestamp() * 1000)
    assert fake.payload["toTimestamp"] == int(closed_at.timestamp() * 1000) - 1


def test_windowed_transport_rejects_impossible_calendar_bar_count() -> None:
    fake = _FakeClient(tuple(object() for _ in range(MAX_CALENDAR_M5_BARS_PER_CHUNK + 1)))
    opened_at = datetime(2026, 9, 1, tzinfo=UTC)
    closed_at = opened_at + timedelta(days=7)
    try:
        read_windowed_chunk(
            cast(SpotwareCTraderOpenApiClient, fake),
            account_id=1,
            symbol_id=2,
            opened_at=opened_at,
            closed_at=closed_at,
            client_msg_id="test-cap",
        )
    except RuntimeError as error:
        assert "calendar grid" in str(error)
    else:
        raise AssertionError("impossible provider M5 count must fail closed")
