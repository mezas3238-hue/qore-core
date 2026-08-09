from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_cross_provider_certification as cross
import qore.kernel.result as result
from qore.infrastructure.hosting_latency_safety import HostingLatencyDuration
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)

_NOW = datetime(2026, 8, 10, 13, 0, tzinfo=UTC)
_INSTRUMENT = Instrument("ESZ6")
_TIMEFRAME = Timeframe(60)


def _uuid(suffix: int) -> UUID:
    return UUID(f"65000000-0000-0000-0000-{suffix:012d}")


def _source(provider: str, *, suffix: int) -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(suffix)),
        source_id=SourceId(_uuid(suffix + 1)),
        port_name=PortName(f"market-data.{provider}-cross-certification"),
    )


def _ohlc(
    provider: str,
    *,
    suffix: int,
    open_price: float = 5000.0,
    high: float = 5005.0,
    low: float = 4995.0,
    close: float = 5001.0,
    instrument: Instrument = _INSTRUMENT,
) -> OhlcSnapshot:
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(suffix + 10)),
        instrument=instrument,
        source=_source(provider, suffix=suffix),
        timeframe=_TIMEFRAME,
        opened_at=_NOW,
        closed_at=_NOW + timedelta(minutes=1),
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


def _evidence(
    provider: futures.FuturesProviderName,
    *,
    suffix: int,
    market_data_status: cross.FuturesMarketDataCertificationStatus,
    execution_status: cross.FuturesExecutionCertificationStatus = (
        cross.FuturesExecutionCertificationStatus.CERTIFIED_PAPER_SIMULATION
    ),
    reconciliation: futures.FuturesExecutionReconciliationStatus = (
        futures.FuturesExecutionReconciliationStatus.MATCHED
    ),
    latency_ms: int = 20,
    close: float = 5001.0,
    instrument: Instrument = _INSTRUMENT,
) -> cross.FuturesProviderCertificationEvidence:
    return cross.FuturesProviderCertificationEvidence(
        provider=provider,
        ohlc=_ohlc(
            provider.value,
            suffix=suffix,
            close=close,
            instrument=instrument,
        ),
        market_data_status=market_data_status,
        execution_status=execution_status,
        execution_reconciliation=reconciliation,
        ingress_latency=HostingLatencyDuration.from_milliseconds(latency_ms),
        observed_at=_NOW + timedelta(minutes=1, seconds=1),
        evidence_refs=(
            cross.FuturesProviderCertificationEvidenceReference(_uuid(suffix + 20)),
        ),
    )


def _three_provider_evidence(
    *,
    ibkr_status: cross.FuturesMarketDataCertificationStatus = (
        cross.FuturesMarketDataCertificationStatus.CERTIFIED_REALTIME
    ),
    tastytrade_status: cross.FuturesMarketDataCertificationStatus = (
        cross.FuturesMarketDataCertificationStatus.CERTIFIED_DELAYED
    ),
) -> tuple[cross.FuturesProviderCertificationEvidence, ...]:
    tastytrade_latency_ms = (
        900_000
        if tastytrade_status
        is cross.FuturesMarketDataCertificationStatus.CERTIFIED_DELAYED
        else 20
    )
    return (
        _evidence(
            cross.TRADESTATION_PROVIDER,
            suffix=100,
            market_data_status=(
                cross.FuturesMarketDataCertificationStatus.CERTIFIED_REALTIME
            ),
        ),
        _evidence(
            cross.IBKR_PROVIDER,
            suffix=200,
            market_data_status=ibkr_status,
            close=5001.25,
        ),
        _evidence(
            cross.TASTYTRADE_PROVIDER,
            suffix=300,
            market_data_status=tastytrade_status,
            close=5000.75,
            latency_ms=tastytrade_latency_ms,
        ),
    )


def _policy() -> cross.FuturesCrossProviderPolicy:
    return cross.FuturesCrossProviderPolicy(
        max_ohlc_spread_basis_points=2,
        max_realtime_ingress_latency=HostingLatencyDuration.from_milliseconds(100),
    )


def _evaluate(
    evidence: tuple[cross.FuturesProviderCertificationEvidence, ...],
    *,
    suffix: int,
) -> result.Result[
    cross.FuturesCrossProviderAssessment,
    cross.FuturesCrossProviderCertificationError,
]:
    return cross.evaluate_futures_cross_provider_certification(
        evidence,
        _policy(),
        assessment_id=cross.FuturesCrossProviderAssessmentId(_uuid(suffix)),
        evaluated_at=_NOW + timedelta(minutes=1, seconds=2),
        evidence_ref=cross.FuturesProviderCertificationEvidenceReference(
            _uuid(suffix + 1)
        ),
    )


def test_cross_certification_requires_all_three_mandatory_providers() -> None:
    evidence = _three_provider_evidence()[:2]
    assessed = _evaluate(evidence, suffix=400)

    assert isinstance(assessed, result.Failure)
    assert isinstance(assessed.error, cross.FuturesCrossProviderValidationError)


def test_current_three_provider_evidence_is_delay_aware_not_falsely_realtime() -> None:
    assessed = _evaluate(_three_provider_evidence(), suffix=410)

    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.DELAY_AWARE_CERTIFIED
    assert assessed.value.reason is (
        cross.FuturesCrossProviderReason.ALIGNED_WITH_DELAYED_PROVIDER
    )
    assert assessed.value.three_provider_realtime_certified is False
    assert assessed.value.provider_switch_authorized is False


def test_delayed_provider_latency_is_not_compared_to_realtime_ingress_ceiling() -> None:
    evidence = _three_provider_evidence()
    tastytrade = next(
        item for item in evidence if item.provider == cross.TASTYTRADE_PROVIDER
    )

    assert tastytrade.market_data_status is (
        cross.FuturesMarketDataCertificationStatus.CERTIFIED_DELAYED
    )
    assert tastytrade.ingress_latency > _policy().max_realtime_ingress_latency

    assessed = _evaluate(evidence, suffix=420)
    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.DELAY_AWARE_CERTIFIED


def test_realtime_provider_outside_ingress_policy_blocks_cross_certification() -> None:
    evidence = list(_three_provider_evidence())
    evidence[1] = replace(
        evidence[1],
        ingress_latency=HostingLatencyDuration.from_milliseconds(150),
    )
    assessed = _evaluate(tuple(evidence), suffix=430)

    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.BLOCKED
    assert assessed.value.reason is (
        cross.FuturesCrossProviderReason.REALTIME_INGRESS_OUTSIDE_POLICY
    )


def test_unmatched_execution_reconciliation_blocks_cross_certification() -> None:
    evidence = list(_three_provider_evidence())
    evidence[0] = replace(
        evidence[0],
        execution_reconciliation=futures.FuturesExecutionReconciliationStatus.AMBIGUOUS,
    )
    assessed = _evaluate(tuple(evidence), suffix=440)

    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.BLOCKED
    assert assessed.value.reason is (
        cross.FuturesCrossProviderReason.EXECUTION_RECONCILIATION_NOT_MATCHED
    )


def test_uncertified_provider_evidence_blocks_without_switching_provider() -> None:
    evidence = list(_three_provider_evidence())
    evidence[0] = replace(
        evidence[0],
        execution_status=cross.FuturesExecutionCertificationStatus.NOT_CERTIFIED,
    )
    assessed = _evaluate(tuple(evidence), suffix=450)

    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.BLOCKED
    assert assessed.value.reason is (
        cross.FuturesCrossProviderReason.PROVIDER_EVIDENCE_NOT_CERTIFIED
    )
    assert assessed.value.provider_switch_authorized is False


def test_ohlc_scope_mismatch_blocks_before_value_comparison() -> None:
    evidence = list(_three_provider_evidence())
    evidence[2] = replace(
        evidence[2],
        ohlc=_ohlc(
            "tastytrade",
            suffix=500,
            instrument=Instrument("NQZ6"),
        ),
    )
    assessed = _evaluate(tuple(evidence), suffix=460)

    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.BLOCKED
    assert assessed.value.reason is cross.FuturesCrossProviderReason.OHLC_SCOPE_MISMATCH
    assert assessed.value.spread_evidence is None


def test_material_ohlc_disagreement_is_evidence_not_provider_switch_authority() -> None:
    evidence = list(_three_provider_evidence())
    evidence[1] = replace(
        evidence[1],
        ohlc=_ohlc(
            "ibkr",
            suffix=600,
            close=5010.0,
            high=5012.0,
        ),
    )
    assessed = _evaluate(tuple(evidence), suffix=470)

    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.DISAGREEMENT
    assert assessed.value.reason is cross.FuturesCrossProviderReason.OHLC_DISAGREEMENT
    assert assessed.value.spread_evidence is not None
    assert assessed.value.spread_evidence.maximum_basis_points > 2.0
    assert assessed.value.provider_switch_authorized is False


def test_all_realtime_aligned_evidence_can_be_fully_certified_when_proven() -> None:
    evidence = _three_provider_evidence(
        tastytrade_status=cross.FuturesMarketDataCertificationStatus.CERTIFIED_REALTIME
    )
    assessed = _evaluate(evidence, suffix=480)

    assert isinstance(assessed, result.Success)
    assert assessed.value.state is cross.FuturesCrossProviderState.CERTIFIED
    assert assessed.value.reason is (
        cross.FuturesCrossProviderReason.THREE_PROVIDER_REALTIME_ALIGNED
    )
    assert assessed.value.three_provider_realtime_certified is True


def test_cross_provider_contract_exposes_no_order_or_provider_switch_methods() -> None:
    prohibited = {
        "buy",
        "sell",
        "submit_order",
        "retry_order",
        "redispatch",
        "switch_provider",
        "activate_provider",
        "core_decision",
    }
    for surface in (
        cross.FuturesProviderCertificationEvidence,
        cross.FuturesCrossProviderPolicy,
        cross.FuturesCrossProviderAssessment,
    ):
        assert prohibited.isdisjoint(set(dir(surface)))
