from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.historical_market_data_certification import (
    HistoricalOhlcCoverageReport,
)
from qore.infrastructure.market_data_certification_preparation import (
    MarketDataCertificationPreparationReport,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_EVIDENCE_SCHEMA = "qore.market-data-certification-preparation-evidence.v1"


class MarketDataCertificationEvidenceError(ExternalPortError):
    """Base error for deterministic certification-preparation evidence."""

    __slots__ = ()


class MarketDataCertificationEvidenceValidationError(MarketDataCertificationEvidenceError):
    """Certification-preparation evidence violates a structural invariant."""

    __slots__ = ()


class MarketDataCertificationEvidenceStatus(StrEnum):
    """Closed preparation status; deliberately not an operational certification claim."""

    PREPARED = "prepared"
    BLOCKED = "blocked"


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketDataCertificationEvidenceValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketDataCertificationEvidenceValidationError(
            f"{field_name} must be timezone-aware"
        )


def _coverage_sort_key(report: HistoricalOhlcCoverageReport) -> tuple[str, int]:
    return report.series_key()


@dataclass(frozen=True, slots=True)
class MarketDataCertificationPreparationEvidence:
    """Sanitized deterministic package proving preparation only, never certification."""

    report: MarketDataCertificationPreparationReport
    historical_coverages: tuple[HistoricalOhlcCoverageReport, ...]
    generated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.report, MarketDataCertificationPreparationReport):
            raise MarketDataCertificationEvidenceValidationError(
                "evidence report must be MarketDataCertificationPreparationReport"
            )
        if not isinstance(self.historical_coverages, tuple) or any(
            not isinstance(item, HistoricalOhlcCoverageReport)
            for item in self.historical_coverages
        ):
            raise MarketDataCertificationEvidenceValidationError(
                "historical_coverages must be a tuple of HistoricalOhlcCoverageReport"
            )
        if self.historical_coverages != tuple(
            sorted(self.historical_coverages, key=_coverage_sort_key)
        ):
            raise MarketDataCertificationEvidenceValidationError(
                "historical_coverages must use stable series order"
            )
        _validate_aware_datetime(self.generated_at, field_name="evidence generated_at")
        if self.generated_at < self.report.evaluated_at:
            raise MarketDataCertificationEvidenceValidationError(
                "evidence generated_at must not precede report evaluated_at"
            )

        expected_source = self.report.policy.expected_source
        for coverage in self.historical_coverages:
            if coverage.expected_source != expected_source:
                raise MarketDataCertificationEvidenceValidationError(
                    "historical coverage source must match preparation report source"
                )

        expected_series = tuple(
            (symbol, timeframe.seconds)
            for symbol in self.report.policy.required_symbols
            for timeframe in self.report.policy.required_timeframes
        )
        actual_series = tuple(item.series_key() for item in self.historical_coverages)
        if actual_series != expected_series:
            raise MarketDataCertificationEvidenceValidationError(
                "historical coverages must match the exact required symbol/timeframe matrix"
            )

    @property
    def status(self) -> MarketDataCertificationEvidenceStatus:
        if self.report.is_prepared and all(
            coverage.is_complete for coverage in self.historical_coverages
        ):
            return MarketDataCertificationEvidenceStatus.PREPARED
        return MarketDataCertificationEvidenceStatus.BLOCKED

    def logical_values(self) -> tuple[object, ...]:
        return (
            _EVIDENCE_SCHEMA,
            self.status.value,
            self.generated_at.isoformat(),
            self.report.logical_values(),
            tuple(item.logical_values() for item in self.historical_coverages),
        )

    def public_payload(self) -> dict[str, object]:
        source = self.report.policy.expected_source
        findings = [
            {
                "code": finding.code.value,
                "instrument": finding.instrument,
                "timeframe_seconds": finding.timeframe_seconds,
                "observed_at": (
                    finding.observed_at.isoformat()
                    if finding.observed_at is not None
                    else None
                ),
            }
            for finding in self.report.findings
        ]
        coverage_payloads: list[dict[str, object]] = []
        for coverage in self.historical_coverages:
            window = coverage.plan.window
            coverage_payloads.append(
                {
                    "instrument": window.instrument.symbol,
                    "timeframe_seconds": window.timeframe.seconds,
                    "opened_at": window.opened_at.isoformat(),
                    "closed_at": window.closed_at.isoformat(),
                    "expected_intervals": window.interval_count,
                    "snapshot_count": coverage.snapshot_count,
                    "status": "complete" if coverage.is_complete else "blocked",
                    "findings": [
                        {
                            "code": finding.code.value,
                            "instrument": finding.instrument,
                            "timeframe_seconds": finding.timeframe_seconds,
                            "opened_at": finding.opened_at.isoformat(),
                            "closed_at": finding.closed_at.isoformat(),
                        }
                        for finding in coverage.findings
                    ],
                }
            )
        return {
            "schema": _EVIDENCE_SCHEMA,
            "status": self.status.value,
            "generated_at": self.generated_at.isoformat(),
            "evaluated_at": self.report.evaluated_at.isoformat(),
            "source": {
                "adapter_id": str(source.adapter_id.value),
                "source_id": str(source.source_id.value),
                "port_name": source.port_name.value,
            },
            "required_symbols": list(self.report.policy.required_symbols),
            "required_timeframes_seconds": [
                item.seconds for item in self.report.policy.required_timeframes
            ],
            "quote_count": self.report.quote_count,
            "ohlc_count": self.report.ohlc_count,
            "findings": findings,
            "historical_coverages": coverage_payloads,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.public_payload(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def build_market_data_certification_preparation_evidence(
    report: MarketDataCertificationPreparationReport,
    historical_coverages: tuple[HistoricalOhlcCoverageReport, ...],
    *,
    generated_at: datetime,
) -> Result[
    MarketDataCertificationPreparationEvidence,
    MarketDataCertificationEvidenceError,
]:
    """Build one sanitized package after deterministic preparation checks."""

    if not isinstance(report, MarketDataCertificationPreparationReport):
        return Failure(
            MarketDataCertificationEvidenceValidationError(
                "evidence build requires MarketDataCertificationPreparationReport"
            )
        )
    if not isinstance(historical_coverages, tuple) or any(
        not isinstance(item, HistoricalOhlcCoverageReport)
        for item in historical_coverages
    ):
        return Failure(
            MarketDataCertificationEvidenceValidationError(
                "evidence build requires tuple of HistoricalOhlcCoverageReport"
            )
        )
    try:
        evidence = MarketDataCertificationPreparationEvidence(
            report=report,
            historical_coverages=historical_coverages,
            generated_at=generated_at,
        )
    except MarketDataCertificationEvidenceError as error:
        return Failure(error)
    return Success(evidence)
