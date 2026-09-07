from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import cast
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.ctrader_demo_market_data import (
    CTraderDemoMarketDataFlow,
    CTraderDemoMarketDataPayloadAdapter,
    CTraderDemoMarketDataUnsupportedError,
    CTraderDemoMarketDataValidationError,
    CTraderTrendbar,
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    MarketDataValidationError,
    OhlcRequest,
    QuoteRequest,
    Timeframe,
)
from qore.infrastructure.market_observation import MarketTimeframe, MarketTimeframeCode
from qore.infrastructure.ports import (
    AdapterId,
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Result, Success

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("e1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("e1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader-demo"),
)
_CORRELATION = CorrelationId(UUID("e1000000-0000-0000-0000-000000000003"))
_CAUSATION = CausationId(UUID("e1000000-0000-0000-0000-000000000004"))
_SNAPSHOT_ID = MarketDataSnapshotId(UUID("e1000000-0000-0000-0000-000000000005"))
_INSTRUMENT = Instrument("EURUSD")

_M5_OPENED_AT = datetime(2026, 8, 12, 13, 0, tzinfo=UTC)

# Provider-native cTrader period identity for the exact six-period delivery.
# opened_at is aligned to the period's UTC grid so the trendbar open is legal.
_ADMITTED_PERIODS: dict[CTraderTrendbarPeriod, tuple[int, datetime]] = {
    CTraderTrendbarPeriod.M1: (60, datetime(2026, 8, 12, 13, 0, tzinfo=UTC)),
    CTraderTrendbarPeriod.M5: (300, datetime(2026, 8, 12, 13, 0, tzinfo=UTC)),
    CTraderTrendbarPeriod.M15: (900, datetime(2026, 8, 12, 13, 0, tzinfo=UTC)),
    CTraderTrendbarPeriod.M30: (1800, datetime(2026, 8, 12, 13, 0, tzinfo=UTC)),
    CTraderTrendbarPeriod.H1: (3600, datetime(2026, 8, 12, 13, 0, tzinfo=UTC)),
    CTraderTrendbarPeriod.D1: (86400, datetime(2026, 8, 12, 0, 0, tzinfo=UTC)),
}

_UNSUPPORTED_SECONDS = (1, 59, 120, 240, 600, 7200, 14400, 43200, 604800, 86401)


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(
        correlation_id=_CORRELATION,
        causation_id=_CAUSATION,
    )


def _opened_at(period: CTraderTrendbarPeriod) -> datetime:
    return _ADMITTED_PERIODS[period][1]


def _request(
    period: CTraderTrendbarPeriod,
    *,
    opened_at: datetime | None = None,
) -> OhlcRequest:
    seconds = period.seconds
    resolved_opened_at = _opened_at(period) if opened_at is None else opened_at
    return OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=Timeframe(seconds),
        opened_at=resolved_opened_at,
        closed_at=resolved_opened_at + timedelta(seconds=seconds),
    )


def _trendbar(
    period: CTraderTrendbarPeriod,
    *,
    opened_at: datetime | None = None,
    delta_open: int = 10,
    delta_high: int = 50,
    delta_close: int = 25,
    low_relative: int = 110_000,
) -> CTraderTrendbar:
    resolved_opened_at = _opened_at(period) if opened_at is None else opened_at
    return CTraderTrendbar(
        low_relative=low_relative,
        delta_open=delta_open,
        delta_high=delta_high,
        delta_close=delta_close,
        utc_timestamp_in_minutes=int(resolved_opened_at.timestamp()) // 60,
    )


def _result(
    period: CTraderTrendbarPeriod,
    *,
    instrument: str = "EURUSD",
    digits: int = 5,
    trendbars: tuple[CTraderTrendbar, ...] | None = None,
    has_more: bool = False,
) -> CTraderTrendbarReadResult:
    return CTraderTrendbarReadResult(
        instrument=instrument,
        symbol_id=1_234,
        digits=digits,
        period=period,
        trendbars=(_trendbar(period),) if trendbars is None else trendbars,
        has_more=has_more,
    )


class StubCTraderClient:
    def __init__(
        self,
        result: Result[CTraderTrendbarReadResult, ExternalPortError],
    ) -> None:
        self._result = result
        self.requests: list[OhlcRequest] = []

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return _SOURCE

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        return Success(
            ExternalHealth(
                descriptor=self.descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def read_trendbars(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderTrendbarReadResult, ExternalPortError]:
        del metadata
        self.requests.append(request)
        return self._result


def _flow(
    client: StubCTraderClient,
) -> CTraderDemoMarketDataFlow:
    return CTraderDemoMarketDataFlow(
        CTraderDemoMarketDataPayloadAdapter(client=client)
    )


# --------------------------------------------------------------------------- #
# Provider-native period identity and canonical reconciliation
# --------------------------------------------------------------------------- #

def test_ctrader_period_catalog_is_exactly_the_six_admitted_periods() -> None:
    assert set(CTraderTrendbarPeriod) == {
        CTraderTrendbarPeriod.M1,
        CTraderTrendbarPeriod.M5,
        CTraderTrendbarPeriod.M15,
        CTraderTrendbarPeriod.M30,
        CTraderTrendbarPeriod.H1,
        CTraderTrendbarPeriod.D1,
    }


def test_ctrader_native_daily_identifier_is_d1_not_d() -> None:
    assert CTraderTrendbarPeriod.D1.value == "D1"
    assert "D" not in {period.value for period in CTraderTrendbarPeriod}


@pytest.mark.parametrize(
    ("period", "expected_seconds", "expected_code"),
    [
        (CTraderTrendbarPeriod.M1, 60, MarketTimeframeCode.M1),
        (CTraderTrendbarPeriod.M5, 300, MarketTimeframeCode.M5),
        (CTraderTrendbarPeriod.M15, 900, MarketTimeframeCode.M15),
        (CTraderTrendbarPeriod.M30, 1800, MarketTimeframeCode.M30),
        (CTraderTrendbarPeriod.H1, 3600, MarketTimeframeCode.H1),
        (CTraderTrendbarPeriod.D1, 86400, MarketTimeframeCode.D1),
    ],
)
def test_ctrader_period_seconds_and_canonical_binding(
    period: CTraderTrendbarPeriod,
    expected_seconds: int,
    expected_code: MarketTimeframeCode,
) -> None:
    assert period.seconds == expected_seconds
    assert period.canonical_timeframe_code is expected_code
    assert period.is_daily is (period is CTraderTrendbarPeriod.D1)


def test_ctrader_intraday_seconds_match_canonical_fixed_seconds() -> None:
    for period in CTraderTrendbarPeriod:
        canonical = MarketTimeframe(period.canonical_timeframe_code)
        if period.is_daily:
            assert canonical.fixed_seconds is None
        else:
            assert canonical.fixed_seconds == period.seconds


def test_ctrader_daily_is_calendar_in_canonical_catalog() -> None:
    daily = CTraderTrendbarPeriod.D1
    assert daily.is_daily
    assert MarketTimeframe(MarketTimeframeCode.D1).fixed_seconds is None
    assert daily.seconds == 86400


# --------------------------------------------------------------------------- #
# Normal closed-bar normalization for every admitted period
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("period", list(CTraderTrendbarPeriod))
def test_ctrader_closed_bar_normalizes_for_every_period(
    period: CTraderTrendbarPeriod,
) -> None:
    client = StubCTraderClient(Success(_result(period)))
    flow = _flow(client)

    result = flow.read_ohlc(
        _request(period),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    opened_at = _opened_at(period)
    assert snapshot.snapshot_id is _SNAPSHOT_ID
    assert snapshot.instrument == _INSTRUMENT
    assert snapshot.source is _SOURCE
    assert snapshot.timeframe == Timeframe(period.seconds)
    assert snapshot.opened_at == opened_at
    assert snapshot.closed_at == opened_at + timedelta(seconds=period.seconds)
    assert snapshot.open == 1.1001
    assert snapshot.high == 1.1005
    assert snapshot.low == 1.1
    assert snapshot.close == 1.10025
    assert client.requests == [_request(period)]


def test_ctrader_closed_m5_normalizes_into_canonical_ohlc_snapshot() -> None:
    # Prior M5 closure: preserved verbatim so legacy M5 behavior stays pinned.
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5)))
    flow = _flow(client)

    result = flow.read_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.snapshot_id is _SNAPSHOT_ID
    assert snapshot.instrument == _INSTRUMENT
    assert snapshot.source is _SOURCE
    assert snapshot.timeframe == Timeframe(300)
    assert snapshot.opened_at == _M5_OPENED_AT
    assert snapshot.closed_at == _M5_OPENED_AT + timedelta(minutes=5)
    assert snapshot.open == 1.1001
    assert snapshot.high == 1.1005
    assert snapshot.low == 1.1
    assert snapshot.close == 1.10025
    assert client.requests == [_request(CTraderTrendbarPeriod.M5)]
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5, digits=3)))
    flow = _flow(client)

    result = flow.read_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.open == 1.1
    assert snapshot.high == 1.1
    assert snapshot.low == 1.1
    assert snapshot.close == 1.1


# --------------------------------------------------------------------------- #
# Rejection of unsupported periods and semantic impostors
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("seconds", _UNSUPPORTED_SECONDS)
def test_ctrader_rejects_unsupported_timeframe_before_client_call(
    seconds: int,
) -> None:
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5)))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)
    timeframe = Timeframe(seconds)
    request = OhlcRequest(
        instrument=_INSTRUMENT,
        timeframe=timeframe,
        opened_at=_M5_OPENED_AT,
        closed_at=_M5_OPENED_AT + timedelta(seconds=seconds),
    )

    result = adapter.read_external_ohlc(request, metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataUnsupportedError)
    assert client.requests == []


@pytest.mark.parametrize("period", list(CTraderTrendbarPeriod))
def test_ctrader_rejects_provider_period_mismatch(
    period: CTraderTrendbarPeriod,
) -> None:
    wrong_period = next(
        candidate
        for candidate in CTraderTrendbarPeriod
        if candidate is not period
    )
    client = StubCTraderClient(Success(_result(wrong_period)))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(period), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_impostor_period_that_is_not_an_enum_member() -> None:
    with pytest.raises(CTraderDemoMarketDataValidationError):
        CTraderTrendbarReadResult(
            instrument="EURUSD",
            symbol_id=1_234,
            digits=5,
            period=cast(CTraderTrendbarPeriod, "M5"),  # a str impostor, not a member
            trendbars=(_trendbar(CTraderTrendbarPeriod.M5),),
        )


# --------------------------------------------------------------------------- #
# Daily UTC / calendar-day open-close law
# --------------------------------------------------------------------------- #

def test_ctrader_daily_requires_utc_midnight_open_before_client_call() -> None:
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.D1)))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)
    non_midnight = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)

    result = adapter.read_external_ohlc(
        _request(CTraderTrendbarPeriod.D1, opened_at=non_midnight),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)
    assert client.requests == []


def test_ctrader_daily_accepts_utc_midnight_through_to_next_midnight() -> None:
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.D1)))
    flow = _flow(client)
    opened_at = datetime(2026, 8, 12, 0, 0, tzinfo=UTC)

    result = flow.read_ohlc(
        _request(CTraderTrendbarPeriod.D1, opened_at=opened_at),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.opened_at == opened_at
    assert snapshot.closed_at == datetime(2026, 8, 13, 0, 0, tzinfo=UTC)
    assert snapshot.timeframe == Timeframe(86400)


def test_ctrader_daily_rejects_non_midnight_trendbar_timestamp() -> None:
    client = StubCTraderClient(
        Success(
            _result(
                CTraderTrendbarPeriod.D1,
                trendbars=(
                    _trendbar(
                        CTraderTrendbarPeriod.D1,
                        opened_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
                    ),
                ),
            )
        )
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(
        _request(CTraderTrendbarPeriod.D1),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_daily_rejects_forex_17utc_close_convention() -> None:
    # A common non-midnight forex daily anchor is not a UTC calendar day.
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.D1)))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(
        _request(
            CTraderTrendbarPeriod.D1,
            opened_at=datetime(2026, 8, 12, 17, 0, tzinfo=UTC),
        ),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)
    assert client.requests == []


def test_ctrader_daily_law_normalizes_non_utc_offset_to_utc() -> None:
    # A timezone-aware instant equal to UTC midnight is pinned to UTC, so the
    # daily law never depends on the caller's offset (no host-local dependence).
    berlin = ZoneInfo("Europe/Berlin")
    opened_at = datetime(2026, 8, 12, 2, 0, tzinfo=berlin)  # == 00:00 UTC
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.D1)))
    flow = _flow(client)

    result = flow.read_ohlc(
        _request(CTraderTrendbarPeriod.D1, opened_at=opened_at),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    assert result.value.opened_at == datetime(2026, 8, 12, 0, 0, tzinfo=UTC)
    assert result.value.closed_at == datetime(2026, 8, 13, 0, 0, tzinfo=UTC)
    assert result.value.timeframe == Timeframe(86400)


# --------------------------------------------------------------------------- #
# Interval identity / alignment / cross-timeframe lookahead prevention
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("period", list(CTraderTrendbarPeriod))
def test_ctrader_rejects_trendbar_interval_mismatch(
    period: CTraderTrendbarPeriod,
) -> None:
    shifted_opened_at = _opened_at(period) + timedelta(minutes=1)
    client = StubCTraderClient(
        Success(
            _result(
                period,
                trendbars=(
                    _trendbar(period, opened_at=shifted_opened_at),
                ),
            )
        )
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(period), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_one_instant_before_close_as_closed_interval() -> None:
    with pytest.raises(MarketDataValidationError):
        OhlcRequest(
            instrument=_INSTRUMENT,
            timeframe=Timeframe(300),
            opened_at=_M5_OPENED_AT,
            closed_at=_M5_OPENED_AT + timedelta(seconds=299),
        )


def test_ctrader_snapshot_timeframe_binding_distinguishes_timeframes() -> None:
    first = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5)))
    second = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.H1)))

    first_result = _flow(first).read_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )
    second_result = _flow(second).read_ohlc(
        _request(CTraderTrendbarPeriod.H1),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(first_result, Success) and isinstance(second_result, Success)
    first_snapshot = first_result.value
    second_snapshot = second_result.value

    assert first_snapshot.timeframe == Timeframe(300)
    assert second_snapshot.timeframe == Timeframe(3600)
    assert first_snapshot.timeframe != second_snapshot.timeframe
    assert first_snapshot.logical_values() != second_snapshot.logical_values()


# --------------------------------------------------------------------------- #
# Deterministic replay and independence
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("period", list(CTraderTrendbarPeriod))
def test_ctrader_replay_is_deterministic(period: CTraderTrendbarPeriod) -> None:
    first = _flow(StubCTraderClient(Success(_result(period)))).read_ohlc(
        _request(period),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )
    second = _flow(StubCTraderClient(Success(_result(period)))).read_ohlc(
        _request(period),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_ctrader_reads_are_independent_and_do_not_mutate_shared_state() -> None:
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5)))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    adapter.read_external_ohlc(_request(CTraderTrendbarPeriod.M5), metadata=_metadata())
    adapter.read_external_ohlc(_request(CTraderTrendbarPeriod.M5), metadata=_metadata())

    assert client.requests == [
        _request(CTraderTrendbarPeriod.M5),
        _request(CTraderTrendbarPeriod.M5),
    ]


# --------------------------------------------------------------------------- #
# #290 deltaHigh ambiguity hardening + malformed trendbar family
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    ("delta_open", "delta_high", "delta_close"),
    [
        (60, 50, 25),  # open above high
        (10, 50, 60),  # close above high
        (51, 50, 50),  # open above high at boundary+1
        (50, 50, 51),  # close above high at boundary+1
    ],
)
def test_ctrader_rejects_delta_outside_delta_high(
    delta_open: int,
    delta_high: int,
    delta_close: int,
) -> None:
    with pytest.raises(CTraderDemoMarketDataValidationError):
        CTraderTrendbar(
            low_relative=110_000,
            delta_open=delta_open,
            delta_high=delta_high,
            delta_close=delta_close,
            utc_timestamp_in_minutes=int(_M5_OPENED_AT.timestamp()) // 60,
        )


def test_ctrader_rejects_non_int_trendbar_fields_including_bool() -> None:
    with pytest.raises(CTraderDemoMarketDataValidationError):
        CTraderTrendbar(
            low_relative=True,  # bool must not launder as int
            delta_open=10,
            delta_high=50,
            delta_close=25,
            utc_timestamp_in_minutes=int(_M5_OPENED_AT.timestamp()) // 60,
        )
    with pytest.raises(CTraderDemoMarketDataValidationError):
        CTraderTrendbar(
            low_relative=110_000,
            delta_open=10,
            delta_high=50,
            delta_close=25,
            utc_timestamp_in_minutes=cast(int, 1.5),
        )


def test_ctrader_accepts_legitimate_flat_bar() -> None:
    client = StubCTraderClient(
        Success(
            _result(
                CTraderTrendbarPeriod.M5,
                trendbars=(
                    _trendbar(
                        CTraderTrendbarPeriod.M5,
                        delta_open=0,
                        delta_high=0,
                        delta_close=0,
                    ),
                ),
            )
        )
    )
    flow = _flow(client)

    result = flow.read_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    assert snapshot.open == snapshot.high == snapshot.low == snapshot.close


# --------------------------------------------------------------------------- #
# Truncation, missing/multiple bars, instrument mismatch, client failure
# --------------------------------------------------------------------------- #

def test_ctrader_rejects_missing_or_multiple_exact_interval_trendbars() -> None:
    for trendbars in (
        (),
        (_trendbar(CTraderTrendbarPeriod.M5), _trendbar(CTraderTrendbarPeriod.M5)),
    ):
        client = StubCTraderClient(
            Success(_result(CTraderTrendbarPeriod.M5, trendbars=trendbars))
        )
        adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

        result = adapter.read_external_ohlc(
            _request(CTraderTrendbarPeriod.M5),
            metadata=_metadata(),
        )

        assert isinstance(result, Failure)
        assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_truncated_result() -> None:
    client = StubCTraderClient(
        Success(_result(CTraderTrendbarPeriod.M5, has_more=True))
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_rejects_instrument_mismatch() -> None:
    client = StubCTraderClient(
        Success(_result(CTraderTrendbarPeriod.M5, instrument="GBPUSD"))
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


def test_ctrader_candle_only_adapter_fails_closed_for_quote_reads() -> None:
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5)))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_quote(
        QuoteRequest(instrument=_INSTRUMENT),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataUnsupportedError)


def test_ctrader_client_failure_is_preserved() -> None:
    error = CTraderDemoMarketDataValidationError("sanitized provider failure")
    client = StubCTraderClient(Failure(error))
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert result.error is error


# --------------------------------------------------------------------------- #
# Secret / raw account-material hygiene
# --------------------------------------------------------------------------- #

def test_ctrader_evidence_never_carries_secret_or_account_material() -> None:
    client = StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5)))
    flow = _flow(client)

    result = flow.read_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )

    assert isinstance(result, Success)
    snapshot = result.value
    for projection in (
        repr(snapshot),
        str(snapshot.logical_values()),
        str(snapshot.source.logical_values()),
        str(_result(CTraderTrendbarPeriod.M5).logical_values()),
    ):
        lowered = projection.lower()
        assert "token" not in lowered
        assert "secret" not in lowered
        assert "password" not in lowered
        assert "api_key" not in lowered
        assert "access_key" not in lowered


# --------------------------------------------------------------------------- #
# Deterministic logical-values stability
# --------------------------------------------------------------------------- #

def test_ctrader_trendbar_logical_values_are_deterministic() -> None:
    first = _result(CTraderTrendbarPeriod.M5)
    second = _result(CTraderTrendbarPeriod.M5)

    assert first.logical_values() == second.logical_values()
    assert first.trendbars[0].logical_values() == second.trendbars[0].logical_values()
    assert first.logical_values() == first.logical_values()


# --------------------------------------------------------------------------- #
# Period-grid alignment (interval opening/closing identity)
# --------------------------------------------------------------------------- #

_NON_DAILY_GRID_PERIODS = [
    period for period in CTraderTrendbarPeriod if period is not CTraderTrendbarPeriod.M1
]


@pytest.mark.parametrize("period", _NON_DAILY_GRID_PERIODS)
def test_ctrader_rejects_off_grid_trendbar_open(
    period: CTraderTrendbarPeriod,
) -> None:
    base_minutes = int(_opened_at(period).timestamp()) // 60
    off_grid_minutes = base_minutes + 1  # +1 minute is off-grid for every non-M1 period
    client = StubCTraderClient(
        Success(
            _result(
                period,
                trendbars=(
                    CTraderTrendbar(
                        low_relative=110_000,
                        delta_open=10,
                        delta_high=50,
                        delta_close=25,
                        utc_timestamp_in_minutes=off_grid_minutes,
                    ),
                ),
            )
        )
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(_request(period), metadata=_metadata())

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


@pytest.mark.parametrize("period", _NON_DAILY_GRID_PERIODS)
def test_ctrader_rejects_off_grid_request_with_matching_bar(
    period: CTraderTrendbarPeriod,
) -> None:
    off_grid_opened_at = _opened_at(period) + timedelta(minutes=1)
    client = StubCTraderClient(
        Success(
            _result(
                period,
                trendbars=(_trendbar(period, opened_at=off_grid_opened_at),),
            )
        )
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(
        _request(period, opened_at=off_grid_opened_at),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


# --------------------------------------------------------------------------- #
# Exact runtime-type hardening (no subclass laundering)
# --------------------------------------------------------------------------- #

def test_ctrader_rejects_tuple_subclass_for_trendbars() -> None:
    class TrendbarTuple(tuple[CTraderTrendbar, ...]):
        pass

    with pytest.raises(CTraderDemoMarketDataValidationError):
        CTraderTrendbarReadResult(
            instrument="EURUSD",
            symbol_id=1_234,
            digits=5,
            period=CTraderTrendbarPeriod.M5,
            trendbars=TrendbarTuple((_trendbar(CTraderTrendbarPeriod.M5),)),
        )


def test_ctrader_rejects_trendbar_subclass_bypassing_delta_validation() -> None:
    class BypassTrendbar(CTraderTrendbar):
        def __post_init__(self) -> None:
            return None

    with pytest.raises(CTraderDemoMarketDataValidationError):
        CTraderTrendbarReadResult(
            instrument="EURUSD",
            symbol_id=1_234,
            digits=5,
            period=CTraderTrendbarPeriod.M5,
            trendbars=(
                BypassTrendbar(
                    low_relative=1,
                    delta_open=999,
                    delta_high=0,
                    delta_close=999,
                    utc_timestamp_in_minutes=int(_M5_OPENED_AT.timestamp()) // 60,
                ),
            ),
        )


# --------------------------------------------------------------------------- #
# Adversarial normalization (negative deltas, non-positive low, huge timestamp)
# --------------------------------------------------------------------------- #

def test_ctrader_rejects_negative_deltas_and_nonpositive_low() -> None:
    for field in ("delta_open", "delta_high", "delta_close"):
        kwargs = {
            "low_relative": 110_000,
            "delta_open": 10,
            "delta_high": 50,
            "delta_close": 25,
            "utc_timestamp_in_minutes": int(_M5_OPENED_AT.timestamp()) // 60,
        }
        kwargs[field] = -1
        with pytest.raises(CTraderDemoMarketDataValidationError):
            CTraderTrendbar(**kwargs)
    for low in (0, -1):
        with pytest.raises(CTraderDemoMarketDataValidationError):
            CTraderTrendbar(
                low_relative=low,
                delta_open=10,
                delta_high=50,
                delta_close=25,
                utc_timestamp_in_minutes=int(_M5_OPENED_AT.timestamp()) // 60,
            )


def test_ctrader_accepts_digits_zero_and_minimal_valid_delta() -> None:
    digits_zero = _flow(StubCTraderClient(Success(_result(CTraderTrendbarPeriod.M5, digits=0))))
    zero_result = digits_zero.read_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )
    assert isinstance(zero_result, Success)
    assert zero_result.value.low == 1.0

    minimal = _flow(
        StubCTraderClient(
            Success(
                _result(
                    CTraderTrendbarPeriod.M5,
                    trendbars=(
                        _trendbar(
                            CTraderTrendbarPeriod.M5,
                            delta_open=0,
                            delta_high=1,
                            delta_close=0,
                        ),
                    ),
                )
            )
        )
    )
    minimal_result = minimal.read_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        snapshot_id=_SNAPSHOT_ID,
        metadata=_metadata(),
    )
    assert isinstance(minimal_result, Success)
    assert (
        minimal_result.value.open
        == minimal_result.value.low
        == minimal_result.value.close
    )
    assert minimal_result.value.high > minimal_result.value.low


def test_ctrader_huge_timestamp_fails_closed_not_exception() -> None:
    # 4_223_371_675 minutes == 9999-12-31 23:55 UTC; adding the M5 span overflows.
    client = StubCTraderClient(
        Success(
            _result(
                CTraderTrendbarPeriod.M5,
                trendbars=(
                    CTraderTrendbar(
                        low_relative=110_000,
                        delta_open=10,
                        delta_high=50,
                        delta_close=25,
                        utc_timestamp_in_minutes=4_223_371_675,
                    ),
                ),
            )
        )
    )
    adapter = CTraderDemoMarketDataPayloadAdapter(client=client)

    result = adapter.read_external_ohlc(
        _request(CTraderTrendbarPeriod.M5),
        metadata=_metadata(),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoMarketDataValidationError)


# --------------------------------------------------------------------------- #
# Module-level immutability and clock-free boundary
# --------------------------------------------------------------------------- #

def test_ctrader_period_mappings_are_immutable_bijections() -> None:
    import qore.infrastructure.ctrader_demo_market_data as ctrader_mod

    for mapping in (
        ctrader_mod._SECONDS_BY_PERIOD,
        ctrader_mod._CANONICAL_TIMEFRAME_CODE_BY_PERIOD,
        ctrader_mod._PERIOD_BY_SECONDS,
    ):
        assert type(mapping) is MappingProxyType
    assert len(ctrader_mod._PERIOD_BY_SECONDS) == len(
        ctrader_mod._SECONDS_BY_PERIOD
    ) == 6


def test_ctrader_boundary_is_clock_free() -> None:
    source = Path("src/qore/infrastructure/ctrader_demo_market_data.py").read_text()
    for forbidden in (
        "datetime.now",
        "utcnow()",
        "today()",
        "date.today",
        "time.time(",
    ):
        assert forbidden not in source
