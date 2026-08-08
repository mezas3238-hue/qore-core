from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.infrastructure.historical_market_data import (
    HistoricalOhlcPlanningPolicy,
    HistoricalOhlcRequestPlan,
    HistoricalOhlcWindow,
    plan_historical_ohlc_requests,
)
from qore.infrastructure.historical_market_data_certification import (
    HistoricalOhlcCoverageFindingCode,
    HistoricalOhlcCoverageReport,
    evaluate_historical_ohlc_coverage,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    OhlcSnapshot,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.market_data_certification_evidence import (
    MarketDataCertificationEvidenceStatus,
    build_market_data_certification_preparation_evidence,
)
from qore.infrastructure.market_data_certification_preparation import (
    MarketDataCertificationFindingCode,
    MarketDataCertificationPreparationPolicy,
    MarketDataCertificationPreparationReport,
    evaluate_market_data_certification_preparation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 8, 13, 30, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("fa000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("fa000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.oanda-practice"),
)
_OTHER_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("fb000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("fb000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.other"),
)


def _snapshot_id(seed: int) -> MarketDataSnapshotId:
    return MarketDataSnapshotId(UUID(int=10000 + seed))


def _plan(
    *,
    symbol: str = "EUR_USD",
    timeframe_seconds: int = 900,
    intervals: int = 2,
) -> HistoricalOhlcRequestPlan:
    timeframe = Timeframe(timeframe_seconds)
    window = HistoricalOhlcWindow(
        instrument=Instrument(symbol),
        timeframe=timeframe,
        opened_at=_BASE - timedelta(seconds=timeframe_seconds * intervals),
        closed_at=_BASE,
    )
    result = plan_historical_ohlc_requests(
        window,
        policy=HistoricalOhlcPlanningPolicy(maximum_intervals=intervals),
    )
    assert isinstance(result, Success)
    return result.value


def _snapshot(
    request: OhlcRequest,
    seed: int,
    *,
    source: ExternalSourceDescriptor = _SOURCE,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=_snapshot_id(seed),
        instrument=request.instrument,
        source=source,
        timeframe=request.timeframe,
        opened_at=request.opened_at,
        closed_at=request.closed_at,
        open=1.1000,
        high=1.1020,
        low=1.0990,
        close=1.1010,
    )


def _complete_coverage(
    plan: HistoricalOhlcRequestPlan,
    *,
    seed_start: int = 1,
) -> HistoricalOhlcCoverageReport:
    snapshots = tuple(
        _snapshot(request, seed_start + index)
        for index, request in enumerate(plan.requests)
    )
    result = evaluate_historical_ohlc_coverage(
        plan,
        snapshots,
        expected_source=_SOURCE,
    )
    assert isinstance(result, Success)
    assert result.value.is_complete is True
    return result.value


def _prepared_report(
    plan: HistoricalOhlcRequestPlan,
    *,
    quote_age_seconds: int = 1,
    max_quote_age_seconds: int = 5,
) -> MarketDataCertificationPreparationReport:
    snapshots = tuple(
        _snapshot(request, 100 + index)
        for index, request in enumerate(plan.requests)
    )
    quote = QuoteSnapshot(
        snapshot_id=_snapshot_id(90),
        instrument=plan.window.instrument,
        source=_SOURCE,
        observed_at=_BASE - timedelta(seconds=quote_age_seconds),
        bid=1.1000,
        ask=1.1002,
    )
    result = evaluate_market_data_certification_preparation(
        (quote,),
        snapshots,
        policy=MarketDataCertificationPreparationPolicy(
            expected_source=_SOURCE,
            required_symbols=(plan.window.instrument.symbol,),
            required_timeframes=(plan.window.timeframe,),
            max_quote_age=timedelta(seconds=max_quote_age_seconds),
        ),
        evaluated_at=_BASE,
    )
    assert isinstance(result, Success)
    return result.value


def test_historical_coverage_accepts_exact_plan_once() -> None:
    plan = _plan()
    snapshots = tuple(
        _snapshot(request, index + 1) for index, request in enumerate(plan.requests)
    )

    first = evaluate_historical_ohlc_coverage(
        plan,
        snapshots,
        expected_source=_SOURCE,
    )
    second = evaluate_historical_ohlc_coverage(
        plan,
        snapshots,
        expected_source=_SOURCE,
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.is_complete is True
    assert first.value.snapshot_count == 2
    assert first.value.findings == ()
    assert first.value.logical_values() == second.value.logical_values()


def test_historical_coverage_reports_missing_and_unexpected_intervals() -> None:
    plan = _plan()
    first_request = plan.requests[0]
    unexpected_request = OhlcRequest(
        instrument=first_request.instrument,
        timeframe=first_request.timeframe,
        opened_at=plan.window.closed_at,
        closed_at=plan.window.closed_at
        + timedelta(seconds=first_request.timeframe.seconds),
    )
    snapshots = (
        _snapshot(first_request, 1),
        _snapshot(unexpected_request, 2),
    )

    result = evaluate_historical_ohlc_coverage(
        plan,
        snapshots,
        expected_source=_SOURCE,
    )

    assert isinstance(result, Success)
    assert result.value.is_complete is False
    assert {item.code for item in result.value.findings} == {
        HistoricalOhlcCoverageFindingCode.MISSING_INTERVAL,
        HistoricalOhlcCoverageFindingCode.UNEXPECTED_INTERVAL,
    }


def test_historical_coverage_detects_duplicate_interval_id_and_wrong_source() -> None:
    plan = _plan(intervals=1)
    request = plan.requests[0]
    first = _snapshot(request, 1, source=_OTHER_SOURCE)
    duplicate = OhlcSnapshot(
        snapshot_id=first.snapshot_id,
        instrument=first.instrument,
        source=first.source,
        timeframe=first.timeframe,
        opened_at=first.opened_at,
        closed_at=first.closed_at,
        open=first.open,
        high=first.high,
        low=first.low,
        close=first.close,
    )

    result = evaluate_historical_ohlc_coverage(
        plan,
        (first, duplicate),
        expected_source=_SOURCE,
    )

    assert isinstance(result, Success)
    codes = tuple(item.code for item in result.value.findings)
    assert HistoricalOhlcCoverageFindingCode.SOURCE_MISMATCH in codes
    assert HistoricalOhlcCoverageFindingCode.DUPLICATE_SNAPSHOT_ID in codes
    assert HistoricalOhlcCoverageFindingCode.DUPLICATE_INTERVAL in codes


def test_preparation_evidence_is_deterministic_sanitized_and_not_certification() -> None:
    plan = _plan()
    report = _prepared_report(plan)
    coverage = _complete_coverage(plan)

    first = build_market_data_certification_preparation_evidence(
        report,
        (coverage,),
        generated_at=_BASE + timedelta(seconds=1),
    )
    second = build_market_data_certification_preparation_evidence(
        report,
        (coverage,),
        generated_at=_BASE + timedelta(seconds=1),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.status is MarketDataCertificationEvidenceStatus.PREPARED
    assert first.value.to_json() == second.value.to_json()
    payload = first.value.to_json()
    assert '"schema":"qore.market-data-certification-preparation-evidence.v1"' in payload
    assert '"status":"prepared"' in payload
    assert '"expected_intervals":2' in payload
    assert '"snapshot_count":2' in payload
    assert "authorization" not in payload.lower()
    assert "account_id" not in payload.lower()
    assert "token" not in payload.lower()
    assert '"status":"certified"' not in payload


def test_preparation_evidence_becomes_blocked_when_general_report_has_findings() -> None:
    plan = _plan()
    report = _prepared_report(
        plan,
        quote_age_seconds=30,
        max_quote_age_seconds=5,
    )
    coverage = _complete_coverage(plan)

    result = build_market_data_certification_preparation_evidence(
        report,
        (coverage,),
        generated_at=_BASE + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.status is MarketDataCertificationEvidenceStatus.BLOCKED
    assert tuple(item.code for item in report.findings) == (
        MarketDataCertificationFindingCode.QUOTE_STALE,
    )
    assert '"status":"blocked"' in result.value.to_json()
    assert "quote-stale" in result.value.to_json()


def test_preparation_evidence_becomes_blocked_when_historical_coverage_fails() -> None:
    plan = _plan()
    report = _prepared_report(plan)
    coverage_result = evaluate_historical_ohlc_coverage(
        plan,
        (_snapshot(plan.requests[0], 1),),
        expected_source=_SOURCE,
    )
    assert isinstance(coverage_result, Success)
    assert coverage_result.value.is_complete is False

    result = build_market_data_certification_preparation_evidence(
        report,
        (coverage_result.value,),
        generated_at=_BASE + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.status is MarketDataCertificationEvidenceStatus.BLOCKED
    assert "missing-interval" in result.value.to_json()


def test_preparation_evidence_requires_exact_symbol_timeframe_matrix() -> None:
    plan = _plan()
    snapshots = tuple(
        _snapshot(request, 200 + index)
        for index, request in enumerate(plan.requests)
    )
    quote = QuoteSnapshot(
        snapshot_id=_snapshot_id(190),
        instrument=Instrument("EUR_USD"),
        source=_SOURCE,
        observed_at=_BASE - timedelta(seconds=1),
        bid=1.1000,
        ask=1.1002,
    )
    report_result = evaluate_market_data_certification_preparation(
        (quote,),
        snapshots,
        policy=MarketDataCertificationPreparationPolicy(
            expected_source=_SOURCE,
            required_symbols=("EUR_USD",),
            required_timeframes=(Timeframe(300), Timeframe(900)),
            max_quote_age=timedelta(seconds=5),
        ),
        evaluated_at=_BASE,
    )
    assert isinstance(report_result, Success)
    coverage = _complete_coverage(plan)

    result = build_market_data_certification_preparation_evidence(
        report_result.value,
        (coverage,),
        generated_at=_BASE + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert "exact required symbol/timeframe matrix" in str(result.error)


def test_preparation_evidence_rejects_source_mismatch_and_backdated_generation() -> None:
    plan = _plan()
    report = _prepared_report(plan)
    snapshots = tuple(
        _snapshot(request, 300 + index, source=_OTHER_SOURCE)
        for index, request in enumerate(plan.requests)
    )
    coverage_result = evaluate_historical_ohlc_coverage(
        plan,
        snapshots,
        expected_source=_OTHER_SOURCE,
    )
    assert isinstance(coverage_result, Success)

    source_mismatch = build_market_data_certification_preparation_evidence(
        report,
        (coverage_result.value,),
        generated_at=_BASE + timedelta(seconds=1),
    )
    backdated = build_market_data_certification_preparation_evidence(
        report,
        (_complete_coverage(plan),),
        generated_at=_BASE - timedelta(seconds=1),
    )

    assert isinstance(source_mismatch, Failure)
    assert "source must match" in str(source_mismatch.error)
    assert isinstance(backdated, Failure)
    assert "must not precede" in str(backdated.error)
