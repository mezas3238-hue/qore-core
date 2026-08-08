from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.market_data_certification_preparation import (
    MarketDataCertificationFindingCode,
    MarketDataCertificationPreparationPolicy,
    MarketDataCertificationPreparationValidationError,
    evaluate_market_data_certification_preparation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def _source(seed: int, *, port_name: str = "market-data.oanda-practice") -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID(int=seed)),
        source_id=SourceId(UUID(int=seed + 1000)),
        port_name=PortName(port_name),
    )


_SOURCE = _source(1)
_OTHER_SOURCE = _source(2)


def _snapshot_id(seed: int) -> MarketDataSnapshotId:
    return MarketDataSnapshotId(UUID(int=seed + 2000))


def _quote(
    seed: int,
    symbol: str,
    observed_at: datetime,
    *,
    source: ExternalSourceDescriptor = _SOURCE,
) -> QuoteSnapshot:
    return QuoteSnapshot(
        snapshot_id=_snapshot_id(seed),
        instrument=Instrument(symbol),
        source=source,
        observed_at=observed_at,
        bid=1.1000,
        ask=1.1002,
    )


def _ohlc(
    seed: int,
    symbol: str,
    opened_at: datetime,
    *,
    timeframe_seconds: int = 900,
    source: ExternalSourceDescriptor = _SOURCE,
) -> OhlcSnapshot:
    timeframe = Timeframe(timeframe_seconds)
    return OhlcSnapshot(
        snapshot_id=_snapshot_id(seed),
        instrument=Instrument(symbol),
        source=source,
        timeframe=timeframe,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(seconds=timeframe_seconds),
        open=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1005,
    )


def _policy(
    *,
    symbols: tuple[str, ...] = ("EUR_USD", "GBP_USD"),
    timeframe_seconds: tuple[int, ...] = (900,),
    max_quote_age_seconds: int = 5,
    maximum_ohlc_gap_intervals: int = 0,
    source: ExternalSourceDescriptor = _SOURCE,
) -> MarketDataCertificationPreparationPolicy:
    return MarketDataCertificationPreparationPolicy(
        expected_source=source,
        required_symbols=symbols,
        required_timeframes=tuple(Timeframe(value) for value in timeframe_seconds),
        max_quote_age=timedelta(seconds=max_quote_age_seconds),
        maximum_ohlc_gap_intervals=maximum_ohlc_gap_intervals,
    )


def _clean_quotes() -> tuple[QuoteSnapshot, ...]:
    return (
        _quote(1, "EUR_USD", _BASE - timedelta(seconds=2)),
        _quote(2, "GBP_USD", _BASE - timedelta(seconds=1)),
    )


def _clean_ohlc() -> tuple[OhlcSnapshot, ...]:
    return (
        _ohlc(10, "EUR_USD", _BASE - timedelta(minutes=30)),
        _ohlc(11, "EUR_USD", _BASE - timedelta(minutes=15)),
        _ohlc(12, "GBP_USD", _BASE - timedelta(minutes=30)),
        _ohlc(13, "GBP_USD", _BASE - timedelta(minutes=15)),
    )


def _codes(result: Success[object]) -> set[MarketDataCertificationFindingCode]:
    report = cast(object, result.value)
    findings = getattr(report, "findings")
    return {item.code for item in findings}


def test_clean_canonical_window_is_prepared_deterministically() -> None:
    policy = _policy()

    first = evaluate_market_data_certification_preparation(
        _clean_quotes(),
        _clean_ohlc(),
        policy=policy,
        evaluated_at=_BASE,
    )
    second = evaluate_market_data_certification_preparation(
        _clean_quotes(),
        _clean_ohlc(),
        policy=policy,
        evaluated_at=_BASE,
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.is_prepared is True
    assert first.value.findings == ()
    assert first.value.quote_count == 2
    assert first.value.ohlc_count == 4
    assert first.value.logical_values() == second.value.logical_values()


def test_quote_sequence_flags_freshness_duplicates_and_ordering() -> None:
    policy = _policy(symbols=("EUR_USD",))
    quotes = (
        _quote(20, "EUR_USD", _BASE - timedelta(seconds=10)),
        _quote(20, "EUR_USD", _BASE + timedelta(seconds=1)),
        _quote(22, "EUR_USD", _BASE - timedelta(seconds=10)),
    )
    ohlc = (
        _ohlc(30, "EUR_USD", _BASE - timedelta(minutes=30)),
        _ohlc(31, "EUR_USD", _BASE - timedelta(minutes=15)),
    )

    result = evaluate_market_data_certification_preparation(
        quotes,
        ohlc,
        policy=policy,
        evaluated_at=_BASE,
    )

    assert isinstance(result, Success)
    codes = {item.code for item in result.value.findings}
    assert MarketDataCertificationFindingCode.QUOTE_STALE in codes
    assert MarketDataCertificationFindingCode.QUOTE_FUTURE_TIMESTAMP in codes
    assert MarketDataCertificationFindingCode.QUOTE_DUPLICATE_SNAPSHOT_ID in codes
    assert MarketDataCertificationFindingCode.QUOTE_DUPLICATE_TIMESTAMP in codes
    assert MarketDataCertificationFindingCode.QUOTE_OUT_OF_ORDER in codes
    assert result.value.is_prepared is False


def test_ohlc_sequence_flags_gaps_overlaps_duplicates_and_missing_series() -> None:
    policy = _policy()
    ohlc = (
        _ohlc(40, "EUR_USD", _BASE - timedelta(minutes=45)),
        _ohlc(41, "EUR_USD", _BASE - timedelta(minutes=15)),
        _ohlc(41, "EUR_USD", _BASE - timedelta(minutes=20)),
        _ohlc(43, "EUR_USD", _BASE - timedelta(minutes=20)),
    )

    result = evaluate_market_data_certification_preparation(
        _clean_quotes(),
        ohlc,
        policy=policy,
        evaluated_at=_BASE,
    )

    assert isinstance(result, Success)
    codes = {item.code for item in result.value.findings}
    assert MarketDataCertificationFindingCode.OHLC_GAP in codes
    assert MarketDataCertificationFindingCode.OHLC_OUT_OF_ORDER in codes
    assert MarketDataCertificationFindingCode.OHLC_OVERLAP in codes
    assert MarketDataCertificationFindingCode.OHLC_DUPLICATE_SNAPSHOT_ID in codes
    assert MarketDataCertificationFindingCode.OHLC_DUPLICATE_INTERVAL in codes
    assert MarketDataCertificationFindingCode.OHLC_MISSING_SERIES in codes


def test_source_symbol_and_timeframe_mismatches_are_findings() -> None:
    policy = _policy(symbols=("EUR_USD",))
    quotes = (
        _quote(
            50,
            "USD_JPY",
            _BASE - timedelta(seconds=1),
            source=_OTHER_SOURCE,
        ),
    )
    ohlc = (
        _ohlc(
            51,
            "USD_JPY",
            _BASE - timedelta(minutes=5),
            timeframe_seconds=300,
            source=_OTHER_SOURCE,
        ),
    )

    result = evaluate_market_data_certification_preparation(
        quotes,
        ohlc,
        policy=policy,
        evaluated_at=_BASE,
    )

    assert isinstance(result, Success)
    codes = {item.code for item in result.value.findings}
    assert MarketDataCertificationFindingCode.QUOTE_SOURCE_MISMATCH in codes
    assert MarketDataCertificationFindingCode.QUOTE_SYMBOL_NOT_REQUIRED in codes
    assert MarketDataCertificationFindingCode.QUOTE_MISSING_SYMBOL in codes
    assert MarketDataCertificationFindingCode.OHLC_SOURCE_MISMATCH in codes
    assert MarketDataCertificationFindingCode.OHLC_SYMBOL_NOT_REQUIRED in codes
    assert MarketDataCertificationFindingCode.OHLC_TIMEFRAME_NOT_REQUIRED in codes
    assert MarketDataCertificationFindingCode.OHLC_MISSING_SERIES in codes


def test_policy_makes_gap_tolerance_explicit() -> None:
    policy = _policy(
        symbols=("EUR_USD",),
        maximum_ohlc_gap_intervals=1,
    )
    quotes = (_quote(60, "EUR_USD", _BASE - timedelta(seconds=1)),)
    ohlc = (
        _ohlc(61, "EUR_USD", _BASE - timedelta(minutes=45)),
        _ohlc(62, "EUR_USD", _BASE - timedelta(minutes=15)),
    )

    result = evaluate_market_data_certification_preparation(
        quotes,
        ohlc,
        policy=policy,
        evaluated_at=_BASE,
    )

    assert isinstance(result, Success)
    assert result.value.is_prepared is True


def test_policy_rejects_unstable_or_unsafe_requirements() -> None:
    with pytest.raises(
        MarketDataCertificationPreparationValidationError,
        match="stable sorted order",
    ):
        _policy(symbols=("GBP_USD", "EUR_USD"))

    with pytest.raises(
        MarketDataCertificationPreparationValidationError,
        match="must not contain duplicates",
    ):
        _policy(timeframe_seconds=(900, 900))

    with pytest.raises(
        MarketDataCertificationPreparationValidationError,
        match="max_quote_age must be positive",
    ):
        _policy(max_quote_age_seconds=0)

    with pytest.raises(
        MarketDataCertificationPreparationValidationError,
        match="non-negative int",
    ):
        MarketDataCertificationPreparationPolicy(
            expected_source=_SOURCE,
            required_symbols=("EUR_USD",),
            required_timeframes=(Timeframe(900),),
            max_quote_age=timedelta(seconds=5),
            maximum_ohlc_gap_intervals=cast(int, True),
        )

    with pytest.raises(
        MarketDataCertificationPreparationValidationError,
        match="market-data namespace",
    ):
        _policy(source=_source(3, port_name="execution.oanda-practice"))


def test_evaluation_fails_closed_for_noncanonical_inputs_and_naive_time() -> None:
    policy = _policy()
    raw_quotes = cast(tuple[QuoteSnapshot, ...], ("raw-provider-payload",))

    invalid_payload = evaluate_market_data_certification_preparation(
        raw_quotes,
        _clean_ohlc(),
        policy=policy,
        evaluated_at=_BASE,
    )
    naive_time = evaluate_market_data_certification_preparation(
        _clean_quotes(),
        _clean_ohlc(),
        policy=policy,
        evaluated_at=datetime(2026, 8, 8, 12, 0),
    )

    assert isinstance(invalid_payload, Failure)
    assert isinstance(
        invalid_payload.error,
        MarketDataCertificationPreparationValidationError,
    )
    assert isinstance(naive_time, Failure)
    assert isinstance(
        naive_time.error,
        MarketDataCertificationPreparationValidationError,
    )
