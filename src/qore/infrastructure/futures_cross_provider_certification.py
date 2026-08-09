from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from uuid import UUID

from qore.infrastructure.futures_adapter_contracts import (
    FuturesExecutionReconciliationStatus,
    FuturesProviderName,
)
from qore.infrastructure.hosting_latency_safety import HostingLatencyDuration
from qore.infrastructure.market_data import OhlcSnapshot
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

TRADESTATION_PROVIDER = FuturesProviderName("tradestation")
IBKR_PROVIDER = FuturesProviderName("ibkr")
TASTYTRADE_PROVIDER = FuturesProviderName("tastytrade")
MANDATORY_FUTURES_PROVIDERS = frozenset(
    {TRADESTATION_PROVIDER, IBKR_PROVIDER, TASTYTRADE_PROVIDER}
)
_BASIS_POINTS = 10_000.0


class FuturesCrossProviderCertificationError(InfrastructureError):
    """Base error for three-provider Futures certification evidence."""

    __slots__ = ()


class FuturesCrossProviderValidationError(FuturesCrossProviderCertificationError):
    """Violation of cross-provider certification invariants."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise FuturesCrossProviderValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise FuturesCrossProviderValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise FuturesCrossProviderValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class FuturesProviderCertificationEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="provider certification evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesCrossProviderAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="cross-provider assessment id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class FuturesMarketDataCertificationStatus(StrEnum):
    CERTIFIED_REALTIME = "certified_realtime"
    CERTIFIED_DELAYED = "certified_delayed"
    NOT_CERTIFIED = "not_certified"
    UNKNOWN = "unknown"


class FuturesExecutionCertificationStatus(StrEnum):
    CERTIFIED_PAPER_SIMULATION = "certified_paper_simulation"
    NOT_CERTIFIED = "not_certified"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FuturesProviderCertificationEvidence:
    """One provider's immutable certification evidence for one exact OHLC interval."""

    provider: FuturesProviderName
    ohlc: OhlcSnapshot
    market_data_status: FuturesMarketDataCertificationStatus
    execution_status: FuturesExecutionCertificationStatus
    execution_reconciliation: FuturesExecutionReconciliationStatus
    ingress_latency: HostingLatencyDuration
    observed_at: datetime
    evidence_refs: tuple[FuturesProviderCertificationEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.provider, FuturesProviderName):
            raise FuturesCrossProviderValidationError(
                "provider must be FuturesProviderName"
            )
        if not isinstance(self.ohlc, OhlcSnapshot):
            raise FuturesCrossProviderValidationError("ohlc must be canonical OhlcSnapshot")
        if not isinstance(
            self.market_data_status,
            FuturesMarketDataCertificationStatus,
        ):
            raise FuturesCrossProviderValidationError(
                "market_data_status must be FuturesMarketDataCertificationStatus"
            )
        if not isinstance(
            self.execution_status,
            FuturesExecutionCertificationStatus,
        ):
            raise FuturesCrossProviderValidationError(
                "execution_status must be FuturesExecutionCertificationStatus"
            )
        if not isinstance(
            self.execution_reconciliation,
            FuturesExecutionReconciliationStatus,
        ):
            raise FuturesCrossProviderValidationError(
                "execution_reconciliation must be FuturesExecutionReconciliationStatus"
            )
        if not isinstance(self.ingress_latency, HostingLatencyDuration):
            raise FuturesCrossProviderValidationError(
                "ingress_latency must be HostingLatencyDuration"
            )
        _validate_timestamp(self.observed_at, field_name="provider observed_at")
        if self.observed_at < self.ohlc.closed_at:
            raise FuturesCrossProviderValidationError(
                "provider certification evidence cannot predate OHLC close"
            )
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, FuturesProviderCertificationEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise FuturesCrossProviderValidationError(
                "provider certification requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise FuturesCrossProviderValidationError(
                "provider certification evidence refs must be unique"
            )

    @property
    def market_data_certified(self) -> bool:
        return self.market_data_status in {
            FuturesMarketDataCertificationStatus.CERTIFIED_REALTIME,
            FuturesMarketDataCertificationStatus.CERTIFIED_DELAYED,
        }

    @property
    def execution_certified(self) -> bool:
        return self.execution_status is (
            FuturesExecutionCertificationStatus.CERTIFIED_PAPER_SIMULATION
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.ohlc.logical_values(),
            self.market_data_status.value,
            self.execution_status.value,
            self.execution_reconciliation.value,
            self.ingress_latency.logical_values(),
            self.observed_at.isoformat(),
            tuple(ref.logical_values() for ref in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class FuturesCrossProviderPolicy:
    """Comparison tolerance plus realtime ingress ceiling; grants no switch authority."""

    max_ohlc_spread_basis_points: int
    max_realtime_ingress_latency: HostingLatencyDuration

    def __post_init__(self) -> None:
        if (
            type(self.max_ohlc_spread_basis_points) is not int
            or self.max_ohlc_spread_basis_points <= 0
        ):
            raise FuturesCrossProviderValidationError(
                "max_ohlc_spread_basis_points must be a positive integer"
            )
        if not isinstance(self.max_realtime_ingress_latency, HostingLatencyDuration):
            raise FuturesCrossProviderValidationError(
                "max_realtime_ingress_latency must be HostingLatencyDuration"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.max_ohlc_spread_basis_points,
            self.max_realtime_ingress_latency.logical_values(),
        )


class FuturesCrossProviderState(StrEnum):
    CERTIFIED = "certified"
    DELAY_AWARE_CERTIFIED = "delay_aware_certified"
    DISAGREEMENT = "disagreement"
    BLOCKED = "blocked"


class FuturesCrossProviderReason(StrEnum):
    THREE_PROVIDER_REALTIME_ALIGNED = "three_provider_realtime_aligned"
    ALIGNED_WITH_DELAYED_PROVIDER = "aligned_with_delayed_provider"
    PROVIDER_EVIDENCE_NOT_CERTIFIED = "provider_evidence_not_certified"
    EXECUTION_RECONCILIATION_NOT_MATCHED = "execution_reconciliation_not_matched"
    REALTIME_INGRESS_OUTSIDE_POLICY = "realtime_ingress_outside_policy"
    OHLC_SCOPE_MISMATCH = "ohlc_scope_mismatch"
    OHLC_DISAGREEMENT = "ohlc_disagreement"


@dataclass(frozen=True, slots=True)
class FuturesOhlcSpreadEvidence:
    open_basis_points: float
    high_basis_points: float
    low_basis_points: float
    close_basis_points: float

    def __post_init__(self) -> None:
        values = (
            self.open_basis_points,
            self.high_basis_points,
            self.low_basis_points,
            self.close_basis_points,
        )
        if any(type(value) is not float or not isfinite(value) or value < 0.0 for value in values):
            raise FuturesCrossProviderValidationError(
                "OHLC spread basis-points values must be finite non-negative floats"
            )

    @property
    def maximum_basis_points(self) -> float:
        return max(
            self.open_basis_points,
            self.high_basis_points,
            self.low_basis_points,
            self.close_basis_points,
        )

    def logical_values(self) -> tuple[float, ...]:
        return (
            self.open_basis_points,
            self.high_basis_points,
            self.low_basis_points,
            self.close_basis_points,
        )


@dataclass(frozen=True, slots=True)
class FuturesCrossProviderAssessment:
    """Three-provider comparison evidence; never a provider-switch or trading decision."""

    assessment_id: FuturesCrossProviderAssessmentId
    state: FuturesCrossProviderState
    reason: FuturesCrossProviderReason
    provider_evidence: tuple[FuturesProviderCertificationEvidence, ...]
    spread_evidence: FuturesOhlcSpreadEvidence | None
    evaluated_at: datetime
    evidence_ref: FuturesProviderCertificationEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, FuturesCrossProviderAssessmentId):
            raise FuturesCrossProviderValidationError(
                "assessment_id must be FuturesCrossProviderAssessmentId"
            )
        if not isinstance(self.state, FuturesCrossProviderState):
            raise FuturesCrossProviderValidationError(
                "state must be FuturesCrossProviderState"
            )
        if not isinstance(self.reason, FuturesCrossProviderReason):
            raise FuturesCrossProviderValidationError(
                "reason must be FuturesCrossProviderReason"
            )
        if not isinstance(self.provider_evidence, tuple) or any(
            not isinstance(item, FuturesProviderCertificationEvidence)
            for item in self.provider_evidence
        ):
            raise FuturesCrossProviderValidationError(
                "provider_evidence must be immutable certification evidence tuple"
            )
        providers = {item.provider for item in self.provider_evidence}
        if not MANDATORY_FUTURES_PROVIDERS.issubset(providers):
            raise FuturesCrossProviderValidationError(
                "assessment requires TradeStation, IBKR and tastytrade evidence"
            )
        if len(providers) != len(self.provider_evidence):
            raise FuturesCrossProviderValidationError(
                "assessment provider evidence must be unique by provider"
            )
        if self.spread_evidence is not None and not isinstance(
            self.spread_evidence,
            FuturesOhlcSpreadEvidence,
        ):
            raise FuturesCrossProviderValidationError(
                "spread_evidence must be FuturesOhlcSpreadEvidence or None"
            )
        _validate_timestamp(self.evaluated_at, field_name="cross-provider evaluated_at")
        if not isinstance(
            self.evidence_ref,
            FuturesProviderCertificationEvidenceReference,
        ):
            raise FuturesCrossProviderValidationError(
                "evidence_ref must be FuturesProviderCertificationEvidenceReference"
            )

    @property
    def three_provider_realtime_certified(self) -> bool:
        return self.state is FuturesCrossProviderState.CERTIFIED

    @property
    def provider_switch_authorized(self) -> bool:
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.state.value,
            self.reason.value,
            tuple(item.logical_values() for item in self.provider_evidence),
            self.spread_evidence.logical_values() if self.spread_evidence else None,
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def _spread_basis_points(values: tuple[float, ...]) -> float:
    minimum = min(values)
    maximum = max(values)
    return (maximum - minimum) / minimum * _BASIS_POINTS


def _ohlc_spreads(
    evidence: tuple[FuturesProviderCertificationEvidence, ...],
) -> FuturesOhlcSpreadEvidence:
    return FuturesOhlcSpreadEvidence(
        open_basis_points=_spread_basis_points(tuple(item.ohlc.open for item in evidence)),
        high_basis_points=_spread_basis_points(tuple(item.ohlc.high for item in evidence)),
        low_basis_points=_spread_basis_points(tuple(item.ohlc.low for item in evidence)),
        close_basis_points=_spread_basis_points(tuple(item.ohlc.close for item in evidence)),
    )


def _same_ohlc_scope(
    evidence: tuple[FuturesProviderCertificationEvidence, ...],
) -> bool:
    first = evidence[0].ohlc
    return all(
        item.ohlc.instrument == first.instrument
        and item.ohlc.timeframe == first.timeframe
        and item.ohlc.opened_at == first.opened_at
        and item.ohlc.closed_at == first.closed_at
        for item in evidence[1:]
    )


def evaluate_futures_cross_provider_certification(
    provider_evidence: tuple[FuturesProviderCertificationEvidence, ...],
    policy: FuturesCrossProviderPolicy,
    *,
    assessment_id: FuturesCrossProviderAssessmentId,
    evaluated_at: datetime,
    evidence_ref: FuturesProviderCertificationEvidenceReference,
) -> Result[FuturesCrossProviderAssessment, FuturesCrossProviderCertificationError]:
    """Compare three providers without selecting, switching or mutating any provider."""

    if not isinstance(provider_evidence, tuple) or not provider_evidence or any(
        not isinstance(item, FuturesProviderCertificationEvidence)
        for item in provider_evidence
    ):
        return Failure(
            FuturesCrossProviderValidationError(
                "provider_evidence must be a non-empty immutable evidence tuple"
            )
        )
    providers = {item.provider for item in provider_evidence}
    if not MANDATORY_FUTURES_PROVIDERS.issubset(providers):
        return Failure(
            FuturesCrossProviderValidationError(
                "TradeStation, IBKR and tastytrade evidence are mandatory"
            )
        )
    if len(providers) != len(provider_evidence):
        return Failure(
            FuturesCrossProviderValidationError(
                "provider evidence must be unique by provider"
            )
        )
    if not isinstance(policy, FuturesCrossProviderPolicy):
        return Failure(
            FuturesCrossProviderValidationError(
                "policy must be FuturesCrossProviderPolicy"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="cross-provider evaluated_at")
    except FuturesCrossProviderValidationError as validation_error:
        return Failure(validation_error)
    ordered = tuple(sorted(provider_evidence, key=lambda item: item.provider.value))

    if not _same_ohlc_scope(ordered):
        return Success(
            FuturesCrossProviderAssessment(
                assessment_id=assessment_id,
                state=FuturesCrossProviderState.BLOCKED,
                reason=FuturesCrossProviderReason.OHLC_SCOPE_MISMATCH,
                provider_evidence=ordered,
                spread_evidence=None,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    if any(not item.market_data_certified or not item.execution_certified for item in ordered):
        return Success(
            FuturesCrossProviderAssessment(
                assessment_id=assessment_id,
                state=FuturesCrossProviderState.BLOCKED,
                reason=FuturesCrossProviderReason.PROVIDER_EVIDENCE_NOT_CERTIFIED,
                provider_evidence=ordered,
                spread_evidence=None,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    if any(
        item.execution_reconciliation is not FuturesExecutionReconciliationStatus.MATCHED
        for item in ordered
    ):
        return Success(
            FuturesCrossProviderAssessment(
                assessment_id=assessment_id,
                state=FuturesCrossProviderState.BLOCKED,
                reason=FuturesCrossProviderReason.EXECUTION_RECONCILIATION_NOT_MATCHED,
                provider_evidence=ordered,
                spread_evidence=None,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    if any(
        item.market_data_status is FuturesMarketDataCertificationStatus.CERTIFIED_REALTIME
        and item.ingress_latency > policy.max_realtime_ingress_latency
        for item in ordered
    ):
        return Success(
            FuturesCrossProviderAssessment(
                assessment_id=assessment_id,
                state=FuturesCrossProviderState.BLOCKED,
                reason=FuturesCrossProviderReason.REALTIME_INGRESS_OUTSIDE_POLICY,
                provider_evidence=ordered,
                spread_evidence=None,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )

    spreads = _ohlc_spreads(ordered)
    if spreads.maximum_basis_points > float(policy.max_ohlc_spread_basis_points):
        return Success(
            FuturesCrossProviderAssessment(
                assessment_id=assessment_id,
                state=FuturesCrossProviderState.DISAGREEMENT,
                reason=FuturesCrossProviderReason.OHLC_DISAGREEMENT,
                provider_evidence=ordered,
                spread_evidence=spreads,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )

    has_delayed = any(
        item.market_data_status is FuturesMarketDataCertificationStatus.CERTIFIED_DELAYED
        for item in ordered
    )
    return Success(
        FuturesCrossProviderAssessment(
            assessment_id=assessment_id,
            state=(
                FuturesCrossProviderState.DELAY_AWARE_CERTIFIED
                if has_delayed
                else FuturesCrossProviderState.CERTIFIED
            ),
            reason=(
                FuturesCrossProviderReason.ALIGNED_WITH_DELAYED_PROVIDER
                if has_delayed
                else FuturesCrossProviderReason.THREE_PROVIDER_REALTIME_ALIGNED
            ),
            provider_evidence=ordered,
            spread_evidence=spreads,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )
    )
