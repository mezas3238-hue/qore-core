from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_historical_tick_data import (
    CTraderHistoricalTickError,
    CTraderHistoricalTickReader,
    CTraderHistoricalTickRequest,
    CTraderQuoteType,
    decode_historical_tick_page,
)
from qore.kernel.result import Failure, Success


_BASE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class NativeTick:
    timestamp: int
    tick: int


def _request(
    *,
    quote_type: CTraderQuoteType = CTraderQuoteType.BID,
) -> CTraderHistoricalTickRequest:
    return CTraderHistoricalTickRequest(
        account_id=123,
        symbol_id=456,
        quote_type=quote_type,
        from_at=_BASE,
        to_at=_BASE + timedelta(hours=1),
    )


def test_request_is_bounded_to_official_one_week_window() -> None:
    with pytest.raises(CTraderHistoricalTickError, match="seven days"):
        CTraderHistoricalTickRequest(
            account_id=123,
            symbol_id=456,
            quote_type=CTraderQuoteType.BID,
            from_at=_BASE,
            to_at=_BASE + timedelta(days=7, milliseconds=1),
        )


def test_request_fields_preserve_bid_ask_identity_and_milliseconds() -> None:
    request = _request(quote_type=CTraderQuoteType.ASK)

    assert request.fields() == {
        "ctidTraderAccountId": 123,
        "symbolId": 456,
        "type": 2,
        "fromTimestamp": int(_BASE.timestamp() * 1_000),
        "toTimestamp": int((_BASE + timedelta(hours=1)).timestamp() * 1_000),
    }


def test_decoder_reconstructs_newest_first_delta_timestamps() -> None:
    newest = _BASE + timedelta(minutes=10)
    native = (
        NativeTick(int(newest.timestamp() * 1_000), 1_234_560),
        NativeTick(250, 1_234_550),
        NativeTick(750, 1_234_500),
    )

    page = decode_historical_tick_page(
        request=_request(),
        native_ticks=native,
        has_more=True,
        digits=5,
    )

    assert tuple(item.observed_at for item in page.ticks) == (
        newest - timedelta(milliseconds=1_000),
        newest - timedelta(milliseconds=250),
        newest,
    )
    assert tuple(str(item.price) for item in page.ticks) == (
        "12.34500",
        "12.34550",
        "12.34560",
    )
    assert all(item.quote_type is CTraderQuoteType.BID for item in page.ticks)
    assert page.next_older_to_at == (
        newest - timedelta(milliseconds=1_001)
    )


def test_decoder_rejects_timestamp_delta_that_moves_before_epoch() -> None:
    native = (
        NativeTick(500, 100_000),
        NativeTick(600, 100_000),
    )

    with pytest.raises(CTraderHistoricalTickError, match="Unix epoch"):
        decode_historical_tick_page(
            request=CTraderHistoricalTickRequest(
                account_id=123,
                symbol_id=456,
                quote_type=CTraderQuoteType.BID,
                from_at=datetime(1970, 1, 1, tzinfo=UTC),
                to_at=datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC),
            ),
            native_ticks=native,
            has_more=False,
            digits=5,
        )


def test_decoder_rejects_empty_page_claiming_more_records() -> None:
    with pytest.raises(CTraderHistoricalTickError, match="cannot advertise"):
        decode_historical_tick_page(
            request=_request(),
            native_ticks=(),
            has_more=True,
            digits=5,
        )


class FakeClient:
    def __init__(self, response: object) -> None:
        self.is_ready = True
        self.account_id = 123
        self.response = response
        self.requests: list[tuple[str, dict[str, object], str, float]] = []

    def connect_and_authenticate(self):
        return Success(None)

    def request(
        self,
        message_name: str,
        fields,
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ):
        self.requests.append(
            (message_name, dict(fields), client_msg_id, timeout_seconds)
        )
        return Success(self.response)

    def wait_for_event(self, *args, **kwargs):
        raise AssertionError("historical reader must not subscribe or wait for events")

    def close(self) -> None:
        return None


def test_reader_uses_read_only_historical_tick_request() -> None:
    newest = _BASE + timedelta(minutes=10)
    response = SimpleNamespace(
        ctidTraderAccountId=123,
        tickData=[
            NativeTick(int(newest.timestamp() * 1_000), 1_234_560),
            NativeTick(100, 1_234_550),
        ],
        hasMore=False,
    )
    client = FakeClient(response)
    reader = CTraderHistoricalTickReader(
        client=client,
        timeout_seconds=10.0,
    )

    result = reader.read_page(
        request=_request(),
        digits=5,
        client_msg_id="wp05-v12-historical-bid",
    )

    assert isinstance(result, Success)
    assert client.requests[0][0] == "ProtoOAGetTickDataReq"
    assert client.requests[0][1]["type"] == 1
    assert client.requests[0][2] == "wp05-v12-historical-bid"


def test_reader_fails_closed_on_account_mismatch() -> None:
    response = SimpleNamespace(
        ctidTraderAccountId=999,
        tickData=[],
        hasMore=False,
    )
    reader = CTraderHistoricalTickReader(
        client=FakeClient(response),
        timeout_seconds=10.0,
    )

    result = reader.read_page(
        request=_request(),
        digits=5,
        client_msg_id="mismatch",
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderHistoricalTickError)
