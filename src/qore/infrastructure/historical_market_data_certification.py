from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.historical_market_data import HistoricalOhlcRequestPlan
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.ports import ExternalPortError, ExternalSourceDescriptor
from qore.kernel.result import Failure, Result, Success


class HistoricalMarketDataCertificationError(ExternalPortError):
    """Base error for historical market-data certification preparation."""

    __slots__ = ()


class HistoricalMarketDataCertificationValidationError(
    HistoricalMarketDataCertificationError
):
    """Historical coverage input violates deterministic preparation rules."""

    __slots__ = ()


class HistoricalOhlcCoverageFindingCode(StrEnum):
    """Stable sanitized findings for one historical OHLC request plan."""

    SOURCE_MISMATCH = "source-mismatch"
    DUPLICATE_SNAPSHOT_ID = "duplicate-snapshot-id"
    DUPLICATE_INTERVAL = "duplicate-interval"
    UNEXPECTED_INTERVAL = "unexpected-interval"
    MISSING_INTERVAL = "missing-interval"


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HistoricalMarketDataCertificationValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise HistoricalMarketDataCertificationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _request_key(request: object) -> tuple[str, int, datetime, datetime]:
    from qore.infrastructure.market_data import OhlcRequest

    if not isinstance(request, OhlcRequest):
        raise HistoricalMarketDataCertificationValidationError(
            "historical coverage request must be OhlcRequest"
        )
    return (
        request.instrument.symbol,
        request.timeframe.seconds,
        request.opened_at,
        request.closed_at,
    )


def _snapshot_key(snapshot: OhlcSnapshot) -> tuple[str, int, datetime, datetime]:
    return (
        snapshot.instrument.symbol,
        snapshot.timeframe.seconds,
        snapshot.opened_at,
        snapshot.closed_at,
    )


@dataclass(frozen=True, slots=True)
class HistoricalOhlcCoverageFinding:
    """One deterministic mismatch between a historical plan and snapshots."""

    code: HistoricalOhlcCoverageFindingCode
    instrument: str
    timeframe_seconds: int
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.code, HistoricalOhlcCoverageFindingCode):
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage finding code is invalid"
            )
        if not isinstance(self.instrument, str) or not self.instrument:
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage finding instrument must be non-empty"
            )
        if type(self.timeframe_seconds) is not int or self.timeframe_seconds <= 0:
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage finding timeframe must be positive int"
            )
        _validate_aware_datetime(self.opened_at, field_name="finding opened_at")
        _validate_aware_datetime(self.closed_at, field_name="finding closed_at")
        if self.closed_at <= self.opened_at:
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage finding interval must be positive"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.code.value,
            self.instrument,
            self.timeframe_seconds,
            self.opened_at.isoformat(),
            self.closed_at.isoformat(),
        )


def _finding_sort_key(
    finding: HistoricalOhlcCoverageFinding,
) -> tuple[str, str, int, str, str]:
    return (
        finding.code.value,
        finding.instrument,
        finding.timeframe_seconds,
        finding.opened_at.isoformat(),
        finding.closed_at.isoformat(),
    )


@dataclass(frozen=True, slots=True)
class HistoricalOhlcCoverageReport:
    """Exact plan-to-snapshot coverage report; never operational certification."""

    plan: HistoricalOhlcRequestPlan
    expected_source: ExternalSourceDescriptor
    snapshot_count: int
    findings: tuple[HistoricalOhlcCoverageFinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.plan, HistoricalOhlcRequestPlan):
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage report plan must be HistoricalOhlcRequestPlan"
            )
        if not isinstance(self.expected_source, ExternalSourceDescriptor):
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage expected_source must be ExternalSourceDescriptor"
            )
        port_name = self.expected_source.port_name.value
        if port_name != "market-data" and not port_name.startswith("market-data."):
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage source must use market-data namespace"
            )
        if type(self.snapshot_count) is not int or self.snapshot_count < 0:
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage snapshot_count must be non-negative int"
            )
        if not isinstance(self.findings, tuple) or any(
            not isinstance(item, HistoricalOhlcCoverageFinding)
            for item in self.findings
        ):
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage findings must be a tuple of findings"
            )
        if self.findings != tuple(sorted(self.findings, key=_finding_sort_key)):
            raise HistoricalMarketDataCertificationValidationError(
                "historical coverage findings must use stable sorted order"
            )

    @property
    def is_complete(self) -> bool:
        """True only when snapshots cover the plan exactly once from the expected source."""

        return not self.findings

    def series_key(self) -> tuple[str, int]:
        return (
            self.plan.window.instrument.symbol,
            self.plan.window.timeframe.seconds,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.plan.logical_values(),
            self.expected_source.logical_values(),
            self.snapshot_count,
            tuple(item.logical_values() for item in self.findings),
            self.is_complete,
        )


def _finding_from_key(
    code: HistoricalOhlcCoverageFindingCode,
    key: tuple[str, int, datetime, datetime],
) -> HistoricalOhlcCoverageFinding:
    return HistoricalOhlcCoverageFinding(
        code=code,
        instrument=key[0],
        timeframe_seconds=key[1],
        opened_at=key[2],
        closed_at=key[3],
    )


def evaluate_historical_ohlc_coverage(
    plan: HistoricalOhlcRequestPlan,
    snapshots: tuple[OhlcSnapshot, ...],
    *,
    expected_source: ExternalSourceDescriptor,
) -> Result[HistoricalOhlcCoverageReport, HistoricalMarketDataCertificationError]:
    """Compare canonical snapshots with every request in one historical plan exactly."""

    if not isinstance(plan, HistoricalOhlcRequestPlan):
        return Failure(
            HistoricalMarketDataCertificationValidationError(
                "historical coverage requires HistoricalOhlcRequestPlan"
            )
        )
    if not isinstance(snapshots, tuple) or any(
        not isinstance(item, OhlcSnapshot) for item in snapshots
    ):
        return Failure(
            HistoricalMarketDataCertificationValidationError(
                "historical coverage snapshots must be tuple of OhlcSnapshot"
            )
        )
    if not isinstance(expected_source, ExternalSourceDescriptor):
        return Failure(
            HistoricalMarketDataCertificationValidationError(
                "historical coverage requires ExternalSourceDescriptor"
            )
        )

    try:
        expected_keys = tuple(_request_key(request) for request in plan.requests)
        expected_set = set(expected_keys)
        findings: list[HistoricalOhlcCoverageFinding] = []
        seen_ids: set[object] = set()
        seen_keys: set[tuple[str, int, datetime, datetime]] = set()

        for snapshot in snapshots:
            key = _snapshot_key(snapshot)
            if snapshot.source != expected_source:
                findings.append(
                    _finding_from_key(HistoricalOhlcCoverageFindingCode.SOURCE_MISMATCH, key)
                )
            snapshot_id = snapshot.snapshot_id.value
            if snapshot_id in seen_ids:
                findings.append(
                    _finding_from_key(
                        HistoricalOhlcCoverageFindingCode.DUPLICATE_SNAPSHOT_ID,
                        key,
                    )
                )
            else:
                seen_ids.add(snapshot_id)
            if key in seen_keys:
                findings.append(
                    _finding_from_key(
                        HistoricalOhlcCoverageFindingCode.DUPLICATE_INTERVAL,
                        key,
                    )
                )
            else:
                seen_keys.add(key)
            if key not in expected_set:
                findings.append(
                    _finding_from_key(
                        HistoricalOhlcCoverageFindingCode.UNEXPECTED_INTERVAL,
                        key,
                    )
                )

        for key in expected_keys:
            if key not in seen_keys:
                findings.append(
                    _finding_from_key(
                        HistoricalOhlcCoverageFindingCode.MISSING_INTERVAL,
                        key,
                    )
                )

        report = HistoricalOhlcCoverageReport(
            plan=plan,
            expected_source=expected_source,
            snapshot_count=len(snapshots),
            findings=tuple(sorted(findings, key=_finding_sort_key)),
        )
    except HistoricalMarketDataCertificationError as error:
        return Failure(error)
    return Success(report)
