from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from qore.infrastructure.market_data import (
    Instrument,
    OhlcSnapshot,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import ExternalPortError, ExternalSourceDescriptor
from qore.kernel.result import Failure, Result, Success


class MarketDataCertificationPreparationError(ExternalPortError):
    """Base error for deterministic market-data certification preparation."""

    __slots__ = ()


class MarketDataCertificationPreparationValidationError(
    MarketDataCertificationPreparationError
):
    """Structural violation in certification-preparation inputs or policy."""

    __slots__ = ()


class MarketDataCertificationFindingCode(StrEnum):
    """Stable issue codes emitted by deterministic preparation checks."""

    QUOTE_SOURCE_MISMATCH = "quote-source-mismatch"
    QUOTE_SYMBOL_NOT_REQUIRED = "quote-symbol-not-required"
    QUOTE_DUPLICATE_SNAPSHOT_ID = "quote-duplicate-snapshot-id"
    QUOTE_DUPLICATE_TIMESTAMP = "quote-duplicate-timestamp"
    QUOTE_OUT_OF_ORDER = "quote-out-of-order"
    QUOTE_FUTURE_TIMESTAMP = "quote-future-timestamp"
    QUOTE_STALE = "quote-stale"
    QUOTE_MISSING_SYMBOL = "quote-missing-symbol"
    OHLC_SOURCE_MISMATCH = "ohlc-source-mismatch"
    OHLC_SYMBOL_NOT_REQUIRED = "ohlc-symbol-not-required"
    OHLC_TIMEFRAME_NOT_REQUIRED = "ohlc-timeframe-not-required"
    OHLC_DUPLICATE_SNAPSHOT_ID = "ohlc-duplicate-snapshot-id"
    OHLC_DUPLICATE_INTERVAL = "ohlc-duplicate-interval"
    OHLC_OUT_OF_ORDER = "ohlc-out-of-order"
    OHLC_OVERLAP = "ohlc-overlap"
    OHLC_GAP = "ohlc-gap"
    OHLC_MISSING_SERIES = "ohlc-missing-series"


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketDataCertificationPreparationValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketDataCertificationPreparationValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class MarketDataCertificationPreparationPolicy:
    """Explicit deterministic requirements used before operational certification."""

    expected_source: ExternalSourceDescriptor
    required_symbols: tuple[str, ...]
    required_timeframes: tuple[Timeframe, ...]
    max_quote_age: timedelta
    maximum_ohlc_gap_intervals: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.expected_source, ExternalSourceDescriptor):
            raise MarketDataCertificationPreparationValidationError(
                "expected_source must be ExternalSourceDescriptor"
            )
        source_name = self.expected_source.port_name.value
        if source_name != "market-data" and not source_name.startswith("market-data."):
            raise MarketDataCertificationPreparationValidationError(
                "expected_source must use the market-data namespace"
            )
        if not isinstance(self.required_symbols, tuple) or not self.required_symbols:
            raise MarketDataCertificationPreparationValidationError(
                "required_symbols must be a non-empty tuple"
            )
        instruments: list[Instrument] = []
        for symbol in self.required_symbols:
            if not isinstance(symbol, str):
                raise MarketDataCertificationPreparationValidationError(
                    "required_symbols entries must be strings"
                )
            try:
                instruments.append(Instrument(symbol))
            except ExternalPortError as error:
                raise MarketDataCertificationPreparationValidationError(
                    f"required symbol is invalid: {error}"
                ) from error
        canonical_symbols = tuple(item.symbol for item in instruments)
        if canonical_symbols != tuple(sorted(canonical_symbols)):
            raise MarketDataCertificationPreparationValidationError(
                "required_symbols must use stable sorted order"
            )
        if len(set(canonical_symbols)) != len(canonical_symbols):
            raise MarketDataCertificationPreparationValidationError(
                "required_symbols must not contain duplicates"
            )
        if not isinstance(self.required_timeframes, tuple) or not self.required_timeframes:
            raise MarketDataCertificationPreparationValidationError(
                "required_timeframes must be a non-empty tuple"
            )
        if any(not isinstance(item, Timeframe) for item in self.required_timeframes):
            raise MarketDataCertificationPreparationValidationError(
                "required_timeframes entries must be Timeframe"
            )
        seconds = tuple(item.seconds for item in self.required_timeframes)
        if seconds != tuple(sorted(seconds)):
            raise MarketDataCertificationPreparationValidationError(
                "required_timeframes must use stable sorted order"
            )
        if len(set(seconds)) != len(seconds):
            raise MarketDataCertificationPreparationValidationError(
                "required_timeframes must not contain duplicates"
            )
        if not isinstance(self.max_quote_age, timedelta):
            raise MarketDataCertificationPreparationValidationError(
                "max_quote_age must be a timedelta"
            )
        if self.max_quote_age <= timedelta(0):
            raise MarketDataCertificationPreparationValidationError(
                "max_quote_age must be positive"
            )
        if (
            type(self.maximum_ohlc_gap_intervals) is not int
            or self.maximum_ohlc_gap_intervals < 0
        ):
            raise MarketDataCertificationPreparationValidationError(
                "maximum_ohlc_gap_intervals must be a non-negative int"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.expected_source.logical_values(),
            self.required_symbols,
            tuple(item.seconds for item in self.required_timeframes),
            self.max_quote_age.total_seconds(),
            self.maximum_ohlc_gap_intervals,
        )


@dataclass(frozen=True, slots=True)
class MarketDataCertificationFinding:
    """One sanitized deterministic issue discovered in a preparation window."""

    code: MarketDataCertificationFindingCode
    instrument: str | None = None
    timeframe_seconds: int | None = None
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, MarketDataCertificationFindingCode):
            raise MarketDataCertificationPreparationValidationError(
                "finding code must be MarketDataCertificationFindingCode"
            )
        if self.instrument is not None:
            try:
                Instrument(self.instrument)
            except ExternalPortError as error:
                raise MarketDataCertificationPreparationValidationError(
                    f"finding instrument is invalid: {error}"
                ) from error
        if self.timeframe_seconds is not None:
            try:
                Timeframe(self.timeframe_seconds)
            except ExternalPortError as error:
                raise MarketDataCertificationPreparationValidationError(
                    f"finding timeframe is invalid: {error}"
                ) from error
        if self.observed_at is not None:
            _validate_aware_datetime(self.observed_at, field_name="finding observed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.code.value,
            self.instrument,
            self.timeframe_seconds,
            self.observed_at.isoformat() if self.observed_at is not None else None,
        )


def _finding_sort_key(
    finding: MarketDataCertificationFinding,
) -> tuple[str, str, int, str]:
    return (
        finding.code.value,
        finding.instrument or "",
        finding.timeframe_seconds or 0,
        finding.observed_at.isoformat() if finding.observed_at is not None else "",
    )


@dataclass(frozen=True, slots=True)
class MarketDataCertificationPreparationReport:
    """Deterministic readiness report; never operational certification evidence."""

    policy: MarketDataCertificationPreparationPolicy
    evaluated_at: datetime
    quote_count: int
    ohlc_count: int
    findings: tuple[MarketDataCertificationFinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.policy, MarketDataCertificationPreparationPolicy):
            raise MarketDataCertificationPreparationValidationError(
                "report policy must be MarketDataCertificationPreparationPolicy"
            )
        _validate_aware_datetime(self.evaluated_at, field_name="report evaluated_at")
        if type(self.quote_count) is not int or self.quote_count < 0:
            raise MarketDataCertificationPreparationValidationError(
                "quote_count must be a non-negative int"
            )
        if type(self.ohlc_count) is not int or self.ohlc_count < 0:
            raise MarketDataCertificationPreparationValidationError(
                "ohlc_count must be a non-negative int"
            )
        if not isinstance(self.findings, tuple):
            raise MarketDataCertificationPreparationValidationError(
                "findings must be a tuple"
            )
        if any(
            not isinstance(item, MarketDataCertificationFinding)
            for item in self.findings
        ):
            raise MarketDataCertificationPreparationValidationError(
                "findings entries must be MarketDataCertificationFinding"
            )
        if self.findings != tuple(sorted(self.findings, key=_finding_sort_key)):
            raise MarketDataCertificationPreparationValidationError(
                "findings must use stable sorted order"
            )

    @property
    def is_prepared(self) -> bool:
        """True only when deterministic preparation checks found no issue."""

        return not self.findings

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy.logical_values(),
            self.evaluated_at.isoformat(),
            self.quote_count,
            self.ohlc_count,
            tuple(item.logical_values() for item in self.findings),
            self.is_prepared,
        )


def _finding(
    code: MarketDataCertificationFindingCode,
    *,
    instrument: str | None = None,
    timeframe_seconds: int | None = None,
    observed_at: datetime | None = None,
) -> MarketDataCertificationFinding:
    return MarketDataCertificationFinding(
        code=code,
        instrument=instrument,
        timeframe_seconds=timeframe_seconds,
        observed_at=observed_at,
    )


def _quote_findings(
    quotes: tuple[QuoteSnapshot, ...],
    *,
    policy: MarketDataCertificationPreparationPolicy,
    evaluated_at: datetime,
) -> list[MarketDataCertificationFinding]:
    findings: list[MarketDataCertificationFinding] = []
    seen_ids: set[object] = set()
    seen_times: dict[str, set[datetime]] = {}
    previous_time: dict[str, datetime] = {}
    present_symbols: set[str] = set()

    for quote in quotes:
        symbol = quote.instrument.symbol
        present_symbols.add(symbol)
        if quote.source != policy.expected_source:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_SOURCE_MISMATCH,
                    instrument=symbol,
                    observed_at=quote.observed_at,
                )
            )
        if symbol not in policy.required_symbols:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_SYMBOL_NOT_REQUIRED,
                    instrument=symbol,
                    observed_at=quote.observed_at,
                )
            )
        snapshot_id = quote.snapshot_id.value
        if snapshot_id in seen_ids:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_DUPLICATE_SNAPSHOT_ID,
                    instrument=symbol,
                    observed_at=quote.observed_at,
                )
            )
        else:
            seen_ids.add(snapshot_id)

        symbol_times = seen_times.setdefault(symbol, set())
        if quote.observed_at in symbol_times:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_DUPLICATE_TIMESTAMP,
                    instrument=symbol,
                    observed_at=quote.observed_at,
                )
            )
        else:
            symbol_times.add(quote.observed_at)

        previous = previous_time.get(symbol)
        if previous is not None and quote.observed_at < previous:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_OUT_OF_ORDER,
                    instrument=symbol,
                    observed_at=quote.observed_at,
                )
            )
        previous_time[symbol] = quote.observed_at

        if quote.observed_at > evaluated_at:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_FUTURE_TIMESTAMP,
                    instrument=symbol,
                    observed_at=quote.observed_at,
                )
            )
        elif evaluated_at - quote.observed_at > policy.max_quote_age:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_STALE,
                    instrument=symbol,
                    observed_at=quote.observed_at,
                )
            )

    for symbol in policy.required_symbols:
        if symbol not in present_symbols:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.QUOTE_MISSING_SYMBOL,
                    instrument=symbol,
                )
            )
    return findings


def _ohlc_findings(
    snapshots: tuple[OhlcSnapshot, ...],
    *,
    policy: MarketDataCertificationPreparationPolicy,
) -> list[MarketDataCertificationFinding]:
    findings: list[MarketDataCertificationFinding] = []
    seen_ids: set[object] = set()
    seen_intervals: dict[tuple[str, int], set[datetime]] = {}
    previous: dict[tuple[str, int], OhlcSnapshot] = {}
    present_series: set[tuple[str, int]] = set()
    required_timeframes = tuple(item.seconds for item in policy.required_timeframes)

    for snapshot in snapshots:
        symbol = snapshot.instrument.symbol
        seconds = snapshot.timeframe.seconds
        key = (symbol, seconds)
        present_series.add(key)

        if snapshot.source != policy.expected_source:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.OHLC_SOURCE_MISMATCH,
                    instrument=symbol,
                    timeframe_seconds=seconds,
                    observed_at=snapshot.opened_at,
                )
            )
        if symbol not in policy.required_symbols:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.OHLC_SYMBOL_NOT_REQUIRED,
                    instrument=symbol,
                    timeframe_seconds=seconds,
                    observed_at=snapshot.opened_at,
                )
            )
        if seconds not in required_timeframes:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.OHLC_TIMEFRAME_NOT_REQUIRED,
                    instrument=symbol,
                    timeframe_seconds=seconds,
                    observed_at=snapshot.opened_at,
                )
            )

        snapshot_id = snapshot.snapshot_id.value
        if snapshot_id in seen_ids:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.OHLC_DUPLICATE_SNAPSHOT_ID,
                    instrument=symbol,
                    timeframe_seconds=seconds,
                    observed_at=snapshot.opened_at,
                )
            )
        else:
            seen_ids.add(snapshot_id)

        intervals = seen_intervals.setdefault(key, set())
        if snapshot.opened_at in intervals:
            findings.append(
                _finding(
                    MarketDataCertificationFindingCode.OHLC_DUPLICATE_INTERVAL,
                    instrument=symbol,
                    timeframe_seconds=seconds,
                    observed_at=snapshot.opened_at,
                )
            )
        else:
            intervals.add(snapshot.opened_at)

        previous_snapshot = previous.get(key)
        if previous_snapshot is not None:
            if snapshot.opened_at < previous_snapshot.opened_at:
                findings.append(
                    _finding(
                        MarketDataCertificationFindingCode.OHLC_OUT_OF_ORDER,
                        instrument=symbol,
                        timeframe_seconds=seconds,
                        observed_at=snapshot.opened_at,
                    )
                )
            if snapshot.opened_at < previous_snapshot.closed_at:
                findings.append(
                    _finding(
                        MarketDataCertificationFindingCode.OHLC_OVERLAP,
                        instrument=symbol,
                        timeframe_seconds=seconds,
                        observed_at=snapshot.opened_at,
                    )
                )
            elif snapshot.opened_at > previous_snapshot.closed_at:
                gap_seconds = (
                    snapshot.opened_at - previous_snapshot.closed_at
                ).total_seconds()
                allowed_seconds = policy.maximum_ohlc_gap_intervals * seconds
                if gap_seconds > allowed_seconds:
                    findings.append(
                        _finding(
                            MarketDataCertificationFindingCode.OHLC_GAP,
                            instrument=symbol,
                            timeframe_seconds=seconds,
                            observed_at=snapshot.opened_at,
                        )
                    )
        previous[key] = snapshot

    for symbol in policy.required_symbols:
        for timeframe in policy.required_timeframes:
            if (symbol, timeframe.seconds) not in present_series:
                findings.append(
                    _finding(
                        MarketDataCertificationFindingCode.OHLC_MISSING_SERIES,
                        instrument=symbol,
                        timeframe_seconds=timeframe.seconds,
                    )
                )
    return findings


def evaluate_market_data_certification_preparation(
    quotes: tuple[QuoteSnapshot, ...],
    ohlc_snapshots: tuple[OhlcSnapshot, ...],
    *,
    policy: MarketDataCertificationPreparationPolicy,
    evaluated_at: datetime,
) -> Result[
    MarketDataCertificationPreparationReport,
    MarketDataCertificationPreparationError,
]:
    """Evaluate deterministic sequence-level readiness without claiming certification."""

    if not isinstance(quotes, tuple) or any(
        not isinstance(item, QuoteSnapshot) for item in quotes
    ):
        return Failure(
            MarketDataCertificationPreparationValidationError(
                "quotes must be a tuple of QuoteSnapshot"
            )
        )
    if not isinstance(ohlc_snapshots, tuple) or any(
        not isinstance(item, OhlcSnapshot) for item in ohlc_snapshots
    ):
        return Failure(
            MarketDataCertificationPreparationValidationError(
                "ohlc_snapshots must be a tuple of OhlcSnapshot"
            )
        )
    if not isinstance(policy, MarketDataCertificationPreparationPolicy):
        return Failure(
            MarketDataCertificationPreparationValidationError(
                "policy must be MarketDataCertificationPreparationPolicy"
            )
        )
    try:
        _validate_aware_datetime(evaluated_at, field_name="evaluated_at")
        findings = _quote_findings(
            quotes,
            policy=policy,
            evaluated_at=evaluated_at,
        )
        findings.extend(_ohlc_findings(ohlc_snapshots, policy=policy))
        report = MarketDataCertificationPreparationReport(
            policy=policy,
            evaluated_at=evaluated_at,
            quote_count=len(quotes),
            ohlc_count=len(ohlc_snapshots),
            findings=tuple(sorted(findings, key=_finding_sort_key)),
        )
    except MarketDataCertificationPreparationError as error:
        return Failure(error)
    return Success(report)
