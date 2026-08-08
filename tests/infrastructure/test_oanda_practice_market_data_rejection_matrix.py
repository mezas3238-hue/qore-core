from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.market_data import Instrument, OhlcRequest, QuoteRequest, Timeframe
from qore.infrastructure.oanda_practice_market_feed import (
    OandaPracticeMarketDataDecoder,
    OandaPracticeMarketFeedValidationError,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.transport import ExternalTransportResponse
from qore.kernel.result import Failure

_BASE = datetime(2026, 8, 8, 12, 30, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_DEFAULT = object()
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("e1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.oanda-practice"),
)
_QUOTE_REQUEST = QuoteRequest(Instrument("EUR_USD"))
_OHLC_REQUEST = OhlcRequest(
    instrument=Instrument("EUR_USD"),
    timeframe=Timeframe(900),
    opened_at=_OPENED_AT,
    closed_at=_CLOSED_AT,
)


def _response(payload: bytes) -> ExternalTransportResponse:
    return ExternalTransportResponse(
        status_code=200,
        received_at=_BASE,
        payload=payload,
        headers={"content-type": "application/json"},
    )


def _quote_payload(
    *,
    tradeable: object = True,
    price_time: object = "2026-08-08T12:30:00+00:00",
    bids: object = _DEFAULT,
    asks: object = _DEFAULT,
    count: int = 1,
) -> bytes:
    bid_value = (
        [{"price": "1.1000", "liquidity": 1000}]
        if bids is _DEFAULT
        else bids
    )
    ask_value = (
        [{"price": "1.1002", "liquidity": 1000}]
        if asks is _DEFAULT
        else asks
    )
    price: dict[str, object] = {
        "instrument": "EUR_USD",
        "time": price_time,
        "tradeable": tradeable,
        "bids": bid_value,
        "asks": ask_value,
    }
    payload = {"prices": [dict(price) for _ in range(count)]}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _candle_payload(
    *,
    instrument: object = "EUR_USD",
    granularity: object = "M15",
    complete: object = True,
    candle_time: object = "2026-08-08T12:00:00+00:00",
    mid: object = _DEFAULT,
    count: int = 1,
) -> bytes:
    mid_value = (
        {"o": "1.1000", "h": "1.1010", "l": "1.0990", "c": "1.1005"}
        if mid is _DEFAULT
        else mid
    )
    candle: dict[str, object] = {
        "complete": complete,
        "time": candle_time,
        "mid": mid_value,
    }
    payload = {
        "instrument": instrument,
        "granularity": granularity,
        "candles": [dict(candle) for _ in range(count)],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@pytest.mark.parametrize(
    ("payload", "expected"),
    (
        (b"not-json", "UTF-8 JSON object"),
        (b"[]", "root must be a string-keyed object"),
        (b'{"prices":{}}', "prices must be an array"),
        (_quote_payload(count=2), "exactly one requested instrument"),
        (_quote_payload(tradeable=False), "explicitly tradeable"),
        (_quote_payload(price_time="2026-08-08T12:30:00"), "timezone-aware"),
        (_quote_payload(bids=[]), "bids must contain at least one price bucket"),
        (_quote_payload(asks=[]), "asks must contain at least one price bucket"),
        (
            _quote_payload(
                bids=[{"price": "1.2000"}],
                asks=[{"price": "1.1000"}],
            ),
            "best bid must not exceed best ask",
        ),
    ),
)
def test_quote_decoder_rejection_matrix(payload: bytes, expected: str) -> None:
    decoder = OandaPracticeMarketDataDecoder()

    result = decoder.decode_quote(
        _response(payload),
        source=_SOURCE,
        request=_QUOTE_REQUEST,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeMarketFeedValidationError)
    assert expected in str(result.error)


@pytest.mark.parametrize(
    ("payload", "expected"),
    (
        (_candle_payload(instrument="GBP_USD"), "instrument must match"),
        (_candle_payload(granularity="M5"), "granularity must match"),
        (_candle_payload(count=0), "exactly one candle"),
        (_candle_payload(count=2), "exactly one candle"),
        (_candle_payload(complete=False), "explicitly complete object"),
        (_candle_payload(candle_time="2026-08-08T12:00:00"), "timezone-aware"),
        (
            _candle_payload(candle_time="2026-08-08T11:45:00+00:00"),
            "start must match",
        ),
        (_candle_payload(mid=None), "midpoint candle data must be an object"),
        (
            _candle_payload(
                mid={"o": "0", "h": "1.1010", "l": "1.0990", "c": "1.1005"}
            ),
            "mid.o must be positive and finite",
        ),
    ),
)
def test_ohlc_decoder_rejection_matrix(payload: bytes, expected: str) -> None:
    decoder = OandaPracticeMarketDataDecoder()

    result = decoder.decode_ohlc(
        _response(payload),
        source=_SOURCE,
        request=_OHLC_REQUEST,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeMarketFeedValidationError)
    assert expected in str(result.error)


def test_decoder_errors_do_not_echo_sensitive_wire_payload() -> None:
    sensitive_marker = "sensitive-practice-material"
    payload = json.dumps(
        {"diagnostic": sensitive_marker},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    decoder = OandaPracticeMarketDataDecoder()

    result = decoder.decode_quote(
        _response(payload),
        source=_SOURCE,
        request=_QUOTE_REQUEST,
    )

    assert isinstance(result, Failure)
    assert sensitive_marker not in str(result.error)
    assert sensitive_marker not in repr(result.error)
