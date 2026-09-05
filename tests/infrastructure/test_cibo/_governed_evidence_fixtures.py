"""Shared deterministic fixtures for the CIBO governed-evidence boundary.

Correction 003 removes the authority-rooted *attestation* claim entirely: a
publicly constructible producer value record (a resolved ``risk.`` decision, a
qualified market observation, or a research economic result) is not proof that an
owning authority emitted it, so it can never confer governed sufficiency.

These fixtures therefore provide two things:

- ``dependent_evidence(kind)``: the only evidence-bearing conclusion a CIBO
  Function may construct -- an explicit ``EVIDENCE_DEPENDENT`` assessment naming
  exactly one external-authority dependency kind plus seam reasons.
- ``build_forged_*``: deterministic *forged* producer records used only by the
  adversarial closure tests to prove that a directly constructed public record
  cannot manufacture governed Risk / Market / Economic sufficiency.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalEvidence,
    CiboGovernedEvidenceKind,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketPrice,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderPrice,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_economic_evidence import (
    ResearchEconomicEvidenceReference,
    ResearchEconomicResultId,
    ResearchExecutionIntentEvidence,
    ResearchExecutionIntentEvidenceId,
    ResearchFillEvidence,
    ResearchFillId,
    ResearchGrossEconomicResult,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
)
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    ResearchTransactionCostModelId,
    build_research_run_evidence,
)
from qore.kernel.result import Success

DEFAULT_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)
_USD = CurrencyCode("USD")
# The economic record's internal fill chain is anchored one day before DEFAULT_NOW
# so its derived instant remains within the temporal provenance horizon of the
# CIBO assessment ``as_of`` used by the test suite.
_ECON_BASE = datetime(2026, 8, 8, 0, 0, tzinfo=UTC)
_ECON_VALUED_AT = _ECON_BASE + timedelta(minutes=3)
_ECON_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID(int=0x3301)),
    source_id=SourceId(UUID(int=0x3302)),
    port_name=PortName("market-data.research-economic-test"),
)
_ECON_FILL_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID(int=0x3303)),
    source_id=SourceId(UUID(int=0x3304)),
    port_name=PortName("execution.research-test"),
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


_RISK_DEFAULT_DECISION_ID = UUID(int=0x3001)
_MARKET_DEFAULT_OBSERVATION_ID = UUID(int=0x3101)
_ECONOMIC_DEFAULT_RESULT_ID = UUID(int=0x3201)

_DEPENDENCY_REASON = "external.authority.required"


def dependent_evidence(
    kind: CiboGovernedEvidenceKind,
    *,
    evidence_refs: tuple[CiboEvidenceRef, ...] = (
        CiboEvidenceRef("evidence:governed"),
    ),
    as_of: datetime = DEFAULT_NOW,
    reasons: tuple[str, ...] = (_DEPENDENCY_REASON,),
) -> CiboFunctionalEvidence:
    """Build the only evidence-bearing conclusion a CIBO Function may construct.

    The assessment is ``EVIDENCE_DEPENDENT`` and names exactly one external
    authority dependency kind; it can never be inferred to SUFFICIENT.
    """
    return CiboFunctionalEvidence(
        status=CiboEvidenceStatus.EVIDENCE_DEPENDENT,
        evidence_refs=evidence_refs,
        as_of=as_of,
        dependency_kind=kind,
        reasons=reasons,
    )


def build_forged_risk_decision(
    *,
    decision_id: UUID = _RISK_DEFAULT_DECISION_ID,
    certified_at: datetime = DEFAULT_NOW,
    decision_type: str = "risk.allocation-governance",
) -> FunctionalDecision:
    """Build a directly constructed resolved risk-namespace decision.

    This is a *publicly constructible value record* -- any caller can build it with
    ``DecisionType("risk.*")`` + ``DecisionStatus.RESOLVED``. It is not an
    authority-rooted receipt and must never confer governed Risk sufficiency.
    """
    return FunctionalDecision(
        decision_id=DecisionId(decision_id),
        timestamp=certified_at,
        decision_type=DecisionType(decision_type),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=CorrelationId(_uuid(0x3002))),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("risk.within-concentration-limits"),
                summary="resolved risk decision",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def build_forged_market_observation(
    *,
    observation_id: UUID = _MARKET_DEFAULT_OBSERVATION_ID,
    observed_at: datetime = DEFAULT_NOW,
) -> QualifiedQuoteTickObservation:
    """Build a directly constructed qualified market-data quote observation.

    A public value record, not an authority-rooted receipt.
    """
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(observation_id),
        instrument=Instrument("EURUSD"),
        source=ExternalSourceDescriptor(
            adapter_id=AdapterId(_uuid(0x3102)),
            source_id=SourceId(_uuid(0x3103)),
            port_name=PortName("market-data.test"),
        ),
        observed_at=observed_at,
        bid=MarketPrice(Decimal("1.10000")),
        ask=MarketPrice(Decimal("1.10010")),
        evidence_ref=MarketObservationEvidenceReference(_uuid(0x3104)),
    )


def build_forged_economic_result(
    *,
    result_id: UUID = _ECONOMIC_DEFAULT_RESULT_ID,
    valued_at: datetime = _ECON_VALUED_AT,
) -> ResearchGrossEconomicResult:
    """Build a minimal valid research gross economic result.

    A public value record (however heavyweight its internal validation), not an
    authority-rooted receipt.
    """
    run = _economic_run()
    built = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(result_id),
        run=run,
        entry_fills=(_economic_fill(run, OrderSide.BUY, suffix=0x3202, price="100"),),
        exit_fills=(
            _economic_fill(
                run,
                OrderSide.SELL,
                suffix=0x3212,
                price="102",
                seconds=10,
            ),
        ),
        gross_pnl=MoneyAmount(currency=_USD, amount=Decimal("250")),
        valued_at=valued_at,
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(0x3222)),
    )
    assert isinstance(built, Success)
    return built.value


def _economic_run() -> ResearchRunEvidence:
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    scope = HistoricalOhlcDatasetScope(
        source=_ECON_MARKET_SOURCE,
        window=HistoricalOhlcWindow(
            instrument=instrument,
            timeframe=timeframe,
            opened_at=_ECON_BASE,
            closed_at=_ECON_BASE + timedelta(minutes=15),
        ),
    )
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(0x3340)),
        instrument=instrument,
        source=_ECON_MARKET_SOURCE,
        timeframe=timeframe,
        opened_at=_ECON_BASE,
        closed_at=_ECON_BASE + timedelta(minutes=5),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    replay = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(0x3341)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(0x3342)),
    )
    dataset = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(0x3343)),
        revision_id=HistoricalDatasetRevisionId(_uuid(0x3344)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_ECON_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
        observations=(replay,),
    )
    assert isinstance(dataset, Success)
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(0x3345)),
        created_at=_ECON_BASE + timedelta(days=2),
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_ECON_BASE,
        simulated_end=_ECON_BASE + timedelta(minutes=5),
        strategy_configuration_id=ResearchStrategyConfigurationId(_uuid(0x3346)),
        software_revision=ResearchSoftwareRevision("2f4e578f"),
        execution_model_id=ResearchExecutionModelId(_uuid(0x3347)),
        transaction_cost_model_id=ResearchTransactionCostModelId(_uuid(0x3348)),
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _economic_decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(0x3350)),
        timestamp=_ECON_BASE + timedelta(minutes=1),
        decision_type=DecisionType("core.trade"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=CorrelationId(_uuid(0x3351))),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.test"),
                summary="research execution evidence",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _economic_intent(side: OrderSide) -> OrderIntent:
    suffix = 0x3360 if side is OrderSide.BUY else 0x3361
    return OrderIntent(
        intent_id=OrderIntentId(_uuid(suffix)),
        idempotency_key=ExecutionIdempotencyKey(_uuid(suffix + 1)),
        instrument=ExecutionInstrument("EUR_USD"),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_ECON_BASE + timedelta(minutes=1, seconds=1),
        metadata=ExternalRequestMetadata(correlation_id=CorrelationId(_uuid(suffix + 2))),
    )


def _economic_intent_evidence(
    run: ResearchRunEvidence,
    side: OrderSide,
) -> ResearchExecutionIntentEvidence:
    suffix = 0x3370 if side is OrderSide.BUY else 0x3371
    built = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(_uuid(suffix)),
        run=run,
        decision=_economic_decision(),
        intent=_economic_intent(side),
        evidenced_at=_ECON_BASE + timedelta(minutes=1, seconds=2),
    )
    assert isinstance(built, Success)
    return built.value


def _economic_fill(
    run: ResearchRunEvidence,
    side: OrderSide,
    *,
    suffix: int,
    price: str,
    seconds: int = 0,
) -> ResearchFillEvidence:
    built = build_research_fill_evidence(
        fill_id=ResearchFillId(_uuid(suffix)),
        intent_evidence=_economic_intent_evidence(run, side),
        source=_ECON_FILL_SOURCE,
        price=OrderPrice(Decimal(price)),
        quantity=OrderQuantity(Decimal("1")),
        filled_at=_ECON_BASE + timedelta(minutes=2, seconds=seconds),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(suffix + 102)),
    )
    assert isinstance(built, Success)
    return built.value
