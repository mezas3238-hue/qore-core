from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from qore.infrastructure import ctrader_historical_tick_data as tick_data
from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiProtocolError
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class NativeTick:
    timestamp: int
    tick: int


def _request(
    *,
    quote_type: tick_data.CTraderQuoteType = tick_data.CTraderQuoteType.BID,
) -> tick_data.CTraderHistoricalTickRequest:
    return tick_data.CTraderHistoricalTickRequest(
        account_id=123,
        symbol_id=456,
        quote_type=quote_type,
        from_at=_BASE,
        to_at=_BASE + timedelta(hours=1),
    )


def test_request_is_bounded_to_official_one_week_window() -> None:
    with pytest.raises(tick_data.CTraderHistoricalTickError, match="seven days"):
        tick_data.CTraderHistoricalTickRequest(
            account_id=123,
            symbol_id=456,
            quote_type=tick_data.CTraderQuoteType.BID,
            from_at=_BASE,
            to_at=_BASE + timedelta(days=7, milliseconds=1),
        )


def test_request_fields_preserve_bid_ask_identity_and_milliseconds() -> None:
    request = _request(quote_type=tick_data.CTraderQuoteType.ASK)

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
        NativeTick(-250, -10),
        NativeTick(-750, -50),
    )

    page = tick_data.decode_historical_tick_page(
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
    assert all(item.quote_type is tick_data.CTraderQuoteType.BID for item in page.ticks)
    assert page.next_older_to_at == (
        newest - timedelta(milliseconds=1_001)
    )


def test_decoder_rejects_timestamp_delta_that_moves_before_epoch() -> None:
    native = (
        NativeTick(500, 100_000),
        NativeTick(-600, 100_000),
    )

    with pytest.raises(tick_data.CTraderHistoricalTickError, match="Unix epoch"):
        tick_data.decode_historical_tick_page(
            request=tick_data.CTraderHistoricalTickRequest(
                account_id=123,
                symbol_id=456,
                quote_type=tick_data.CTraderQuoteType.BID,
                from_at=datetime(1970, 1, 1, tzinfo=UTC),
                to_at=datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC),
            ),
            native_ticks=native,
            has_more=False,
            digits=5,
        )


def test_decoder_rejects_empty_page_claiming_more_records() -> None:
    with pytest.raises(tick_data.CTraderHistoricalTickError, match="cannot advertise"):
        tick_data.decode_historical_tick_page(
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
            NativeTick(-100, -10),
        ],
        hasMore=False,
    )
    client = FakeClient(response)
    reader = tick_data.CTraderHistoricalTickReader(
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
    reader = tick_data.CTraderHistoricalTickReader(
        client=FakeClient(response),
        timeout_seconds=10.0,
    )

    result = reader.read_page(
        request=_request(),
        digits=5,
        client_msg_id="mismatch",
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, tick_data.CTraderHistoricalTickError)


def test_reader_preserves_tick_normalization_failure_reason() -> None:
    response = SimpleNamespace(
        ctidTraderAccountId=123,
        tickData=[],
        hasMore=True,
    )
    reader = tick_data.CTraderHistoricalTickReader(
        client=FakeClient(response),
        timeout_seconds=10.0,
    )

    result = reader.read_page(
        request=_request(),
        digits=5,
        client_msg_id="invalid-provider-page",
    )

    assert isinstance(result, Failure)
    assert "empty tick page cannot advertise has_more" in str(result.error)


class FailingClient(FakeClient):
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
        return Failure(
            CTraderOpenApiProtocolError(
                "cTrader request rejected: HISTORICAL_DATA_NOT_AVAILABLE"
            )
        )


def test_reader_preserves_sanitized_provider_rejection_reason() -> None:
    reader = tick_data.CTraderHistoricalTickReader(
        client=FailingClient(SimpleNamespace()),
        timeout_seconds=10.0,
    )

    result = reader.read_page(
        request=_request(),
        digits=5,
        client_msg_id="provider-rejection",
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, tick_data.CTraderHistoricalTickError)
    assert "HISTORICAL_DATA_NOT_AVAILABLE" in str(result.error)



def test_decoder_allows_zero_delta_for_same_millisecond_ticks() -> None:
    newest = _BASE + timedelta(minutes=10)
    page = tick_data.decode_historical_tick_page(
        request=_request(),
        native_ticks=(
            NativeTick(int(newest.timestamp() * 1_000), 1_234_560),
            NativeTick(0, -10),
            NativeTick(-250, -50),
        ),
        has_more=False,
        digits=5,
    )

    assert tuple(item.observed_at for item in page.ticks) == (
        newest - timedelta(milliseconds=250),
        newest,
        newest,
    )
    assert tuple(item.relative_price for item in page.ticks[-2:]) == (
        1_234_560,
        1_234_550,
    )


def test_decoder_rejects_positive_delta_in_newest_first_stream() -> None:
    newest = _BASE + timedelta(minutes=10)

    with pytest.raises(
        tick_data.CTraderHistoricalTickError,
        match="must be non-positive",
    ):
        tick_data.decode_historical_tick_page(
            request=_request(),
            native_ticks=(
                NativeTick(int(newest.timestamp() * 1_000), 1_234_560),
                NativeTick(1, -10),
            ),
            has_more=False,
            digits=5,
        )


def test_decoder_reconstructs_signed_price_deltas_from_previous_tick() -> None:
    newest = _BASE + timedelta(minutes=10)

    page = tick_data.decode_historical_tick_page(
        request=_request(),
        native_ticks=(
            NativeTick(int(newest.timestamp() * 1_000), 1_234_560),
            NativeTick(-100, -45),
            NativeTick(-100, 20),
            NativeTick(-100, 0),
        ),
        has_more=False,
        digits=5,
    )

    assert tuple(item.relative_price for item in page.ticks) == (
        1_234_535,
        1_234_515,
        1_234_560,
        1_234_560,
    )
    assert tuple(str(item.price) for item in page.ticks) == (
        "12.34535",
        "12.34515",
        "12.34560",
        "12.34560",
    )


def test_decoder_rejects_price_delta_that_reconstructs_non_positive_price() -> None:
    newest = _BASE + timedelta(minutes=10)

    with pytest.raises(
        tick_data.CTraderHistoricalTickError,
        match="reconstructed non-positive price",
    ):
        tick_data.decode_historical_tick_page(
            request=_request(),
            native_ticks=(
                NativeTick(int(newest.timestamp() * 1_000), 100),
                NativeTick(-1, -100),
            ),
            has_more=False,
            digits=5,
        )
