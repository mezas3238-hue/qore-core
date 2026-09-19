"""VT08 Index R64 canonical economic binding for frozen R58/R59.

This module converts the exact consumed R58/R59 trade ledger into canonical
QORE research-economic objects. It does not retune the strategy, suppress a
signal, or claim a fresh holdout.

The underlying qualified markets remain NAS100, SP500 and US30. VT08INDEX is
only the normalized portfolio accounting instrument used for R-return evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

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
from qore.infrastructure.historical_dataset import (
    HistoricalCoverageGap,
    HistoricalDatasetDigest,
    HistoricalDatasetDigestAlgorithm,
    HistoricalDatasetId,
    HistoricalDatasetManifest,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import Instrument, Timeframe
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
from qore.infrastructure.research_economic_evidence import (
    ResearchEconomicEvidenceReference,
    ResearchEconomicResultId,
    ResearchExecutionIntentEvidenceId,
    ResearchFillEvidence,
    ResearchFillId,
    ResearchReturnObservation,
    ResearchReturnObservationId,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
    build_research_return_observation,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsSnapshot,
    build_research_performance_statistics,
)
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import vt08_index_r59_candidate_freeze as freeze
from qore.infrastructure.trader_lab import (
    vt08_index_r60_core_robustness_suite as r60,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    build_trader_lab_candidate_binding,
)
from qore.infrastructure.traders import vt08_index_specialist_contract as specialist
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.kernel.result import Failure

SCHEMA = "qore.trader_lab.vt08_index_r64_canonical_economic_binding.v1"
IDENTITY = "VT08_INDEX_R64_CANONICAL_ECONOMIC_BINDING_001"
SECONDARY_STRESS = Decimal("0.10")
EXPECTED_SAMPLE = 3465
EXPECTED_TOTAL_R = (
    Decimal(str(freeze.FIVE_YEAR["secondary_total_r"]))
    + Decimal(str(freeze.RECENT_TWO_YEAR["secondary_total_r"]))
)

PROCESS_FROZEN_AT = datetime(2026, 9, 19, 20, 10, tzinfo=UTC)
PROCESS_RUN_CREATED_AT = datetime(2026, 9, 19, 20, 11, tzinfo=UTC)
PROCESS_EVIDENCE_AT = datetime(2026, 9, 19, 20, 12, tzinfo=UTC)
PROCESS_PERFORMANCE_AT = datetime(2026, 9, 19, 20, 13, tzinfo=UTC)

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("77600000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("77600000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.vt08-index-r64"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("77600000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("77600000-0000-0000-0000-000000000004")),
    port_name=PortName("execution.vt08-index-r64"),
)
_USD = CurrencyCode("USD")
_CAPITAL = MoneyAmount(currency=_USD, amount=Decimal("1"))


def _uid(namespace: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"qore:vt08-index:r64:{specialist.CONFIG_FINGERPRINT}:{namespace}",
    )


def _bar_payload(symbol: str, bars: tuple[Any, ...]) -> bytes:
    payload = {
        "schema": "qore.vt08-index.r64.retained-m15.v1",
        "symbol": symbol,
        "bars": [
            {
                "opened_at": bar.opened_at.astimezone(UTC).isoformat(
                    timespec="microseconds"
                ),
                "closed_at": bar.closed_at.astimezone(UTC).isoformat(
                    timespec="microseconds"
                ),
                "open": str(bar.open),
                "high": str(bar.high),
                "low": str(bar.low),
                "close": str(bar.close),
            }
            for bar in bars
        ],
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _gaps(
    bars: tuple[Any, ...],
    *,
    requested_start: datetime,
    requested_end: datetime,
) -> tuple[HistoricalCoverageGap, ...]:
    gaps: list[HistoricalCoverageGap] = []
    first = bars[0].opened_at.astimezone(UTC)
    if first > requested_start:
        gaps.append(HistoricalCoverageGap(requested_start, first))
    previous = bars[0].closed_at.astimezone(UTC)
    for bar in bars[1:]:
        opened = bar.opened_at.astimezone(UTC)
        closed = bar.closed_at.astimezone(UTC)
        if opened > previous:
            gaps.append(HistoricalCoverageGap(previous, opened))
        previous = closed
    if previous < requested_end:
        gaps.append(HistoricalCoverageGap(previous, requested_end))
    return tuple(gaps)


def _dataset_manifest(
    symbol: str,
    bars: tuple[Any, ...],
    *,
    requested_start: datetime,
    requested_end: datetime,
) -> HistoricalDatasetManifest:
    return HistoricalDatasetManifest(
        dataset_id=HistoricalDatasetId(_uid(f"dataset:{symbol}")),
        revision_id=HistoricalDatasetRevisionId(_uid(f"revision:{symbol}")),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(
            source=_SOURCE,
            window=HistoricalOhlcWindow(
                instrument=Instrument(symbol),
                timeframe=Timeframe(900),
                opened_at=requested_start,
                closed_at=requested_end,
            ),
        ),
        assembled_at=PROCESS_RUN_CREATED_AT,
        schema_version=HistoricalDatasetSchemaVersion(
            "vt08-index-retained-m15-v1"
        ),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "cibo-r64-m15-v1"
        ),
        observation_count=len(bars),
        actual_opened_at=bars[0].opened_at.astimezone(UTC),
        actual_closed_at=bars[-1].closed_at.astimezone(UTC),
        gaps=_gaps(
            bars,
            requested_start=requested_start,
            requested_end=requested_end,
        ),
        digest_algorithm=HistoricalDatasetDigestAlgorithm.SHA256,
        evidence_digest=HistoricalDatasetDigest(
            sha256(_bar_payload(symbol, bars)).hexdigest()
        ),
    )


def _strategy_binding(
    *,
    manifests: tuple[HistoricalDatasetManifest, ...],
    simulated_start: datetime,
    simulated_end: datetime,
) -> ResearchRunStrategyBinding:
    configuration_id = ResearchStrategyConfigurationId(
        _uid("strategy-configuration")
    )
    run = build_research_run_evidence(
        run_id=ResearchRunId(_uid("research-run")),
        created_at=PROCESS_RUN_CREATED_AT,
        datasets=manifests,
        replay_policy_version=ResearchReplayPolicyVersion(
            "point-in-time-vt08-index-r64-v1"
        ),
        simulated_start=simulated_start,
        simulated_end=simulated_end,
        strategy_configuration_id=configuration_id,
        software_revision=ResearchSoftwareRevision(freeze.SOURCE_HEAD_SHA),
        execution_model_id=ResearchExecutionModelId(
            _uid("execution-model")
        ),
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    if isinstance(run, Failure):
        raise ValueError(f"R64 research run failed: {run.error}")

    parameters = tuple(
        ResearchStrategyParameter(name, value)
        for name, value in specialist.manifest_parameters()
    ) + (
        ResearchStrategyParameter(
            "vt08.source_candidate_id",
            specialist.CANDIDATE_ID,
        ),
        ResearchStrategyParameter("vt08.freeze_id", specialist.FREEZE_ID),
        ResearchStrategyParameter(
            "vt08.secondary_stress_r",
            SECONDARY_STRESS,
        ),
    )
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion(
            "vt08-index-r58-specialist-v1"
        ),
        parameters=parameters,
        frozen_at=PROCESS_FROZEN_AT,
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            _uid("strategy-freeze")
        ),
    )
    if isinstance(manifest, Failure):
        raise ValueError(f"R64 strategy manifest failed: {manifest.error}")
    binding = build_research_run_strategy_binding(
        run=run.value,
        manifest=manifest.value,
    )
    if isinstance(binding, Failure):
        raise ValueError(f"R64 strategy binding failed: {binding.error}")
    return binding.value


def _candidate(binding: ResearchRunStrategyBinding) -> TraderLabCandidateBinding:
    candidate = build_trader_lab_candidate_binding(
        candidate_id=TraderLabCandidateId(_uid("trader-lab-candidate")),
        version=TraderLabCandidateVersion(specialist.TRADER_VERSION),
        strategy_binding=binding,
    )
    if isinstance(candidate, Failure):
        raise ValueError(f"R64 candidate binding failed: {candidate.error}")
    return candidate.value


def _decision(at: datetime, *, token: str, symbol: str) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uid(f"decision:{token}")),
        timestamp=at,
        decision_type=DecisionType("core.trade"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(_uid(f"correlation:{token}"))
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.vt08-index-r58"),
                summary=f"R58 retained normalized return for {symbol}",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _fill(
    *,
    run: Any,
    token: str,
    symbol: str,
    side: OrderSide,
    decision_at: datetime,
    fill_at: datetime,
) -> ResearchFillEvidence:
    intent_at = decision_at + timedelta(microseconds=1)
    evidenced_at = intent_at + timedelta(microseconds=1)
    intent = OrderIntent(
        intent_id=OrderIntentId(_uid(f"intent:{token}")),
        idempotency_key=ExecutionIdempotencyKey(
            _uid(f"idempotency:{token}")
        ),
        instrument=ExecutionInstrument(specialist.PORTFOLIO_INSTRUMENT),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=intent_at,
        metadata=ExternalRequestMetadata(
            correlation_id=CorrelationId(
                _uid(f"intent-correlation:{token}")
            )
        ),
    )
    intent_evidence = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(
            _uid(f"intent-evidence:{token}")
        ),
        run=run,
        decision=_decision(
            decision_at,
            token=token,
            symbol=symbol,
        ),
        intent=intent,
        evidenced_at=evidenced_at,
    )
    if isinstance(intent_evidence, Failure):
        raise ValueError(
            f"R64 intent evidence failed: {intent_evidence.error}"
        )
    fill = build_research_fill_evidence(
        fill_id=ResearchFillId(_uid(f"fill:{token}")),
        intent_evidence=intent_evidence.value,
        source=_EXECUTION_SOURCE,
        price=OrderPrice(Decimal("1")),
        quantity=OrderQuantity(Decimal("1")),
        filled_at=fill_at,
        evidence_ref=ResearchEconomicEvidenceReference(
            _uid(f"fill-ref:{token}")
        ),
    )
    if isinstance(fill, Failure):
        raise ValueError(f"R64 fill failed: {fill.error}")
    return fill.value


def _observation(
    *,
    run: Any,
    item: Any,
    window: str,
    evidence_ordinal: int,
) -> ResearchReturnObservation:
    token = f"{window}:{item.symbol}:{item.trade_id}"
    signal_at = item.signal_at.astimezone(UTC)
    exited_at = item.exited_at.astimezone(UTC)
    entry_fill_at = signal_at + timedelta(microseconds=3)
    exit_decision_at = exited_at - timedelta(microseconds=3)
    if exit_decision_at <= entry_fill_at:
        raise ValueError("R64 retained trade chronology is invalid")

    entry_side = (
        OrderSide.BUY
        if item.opportunity.signal.side is DemoTradingSetupSide.LONG
        else OrderSide.SELL
    )
    exit_side = (
        OrderSide.SELL if entry_side is OrderSide.BUY else OrderSide.BUY
    )
    entry_fill = _fill(
        run=run,
        token=f"{token}:entry",
        symbol=item.symbol,
        side=entry_side,
        decision_at=signal_at,
        fill_at=entry_fill_at,
    )
    exit_fill = _fill(
        run=run,
        token=f"{token}:exit",
        symbol=item.symbol,
        side=exit_side,
        decision_at=exit_decision_at,
        fill_at=exited_at,
    )
    realized = (
        item.outcome.r_multiple - SECONDARY_STRESS
    ) * item.weight
    gross = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(
            _uid(f"economic-result:{token}")
        ),
        run=run,
        entry_fills=(entry_fill,),
        exit_fills=(exit_fill,),
        gross_pnl=MoneyAmount(currency=_USD, amount=realized),
        valued_at=exited_at,
        evidence_ref=ResearchEconomicEvidenceReference(
            _uid(f"economic-ref:{token}")
        ),
    )
    if isinstance(gross, Failure):
        raise ValueError(f"R64 gross result failed: {gross.error}")
    observation = build_research_return_observation(
        observation_id=ResearchReturnObservationId(
            _uid(f"return:{token}")
        ),
        source_result=gross.value,
        capital_basis=_CAPITAL,
        observed_at=PROCESS_EVIDENCE_AT + timedelta(
            microseconds=evidence_ordinal
        ),
    )
    if isinstance(observation, Failure):
        raise ValueError(
            f"R64 return observation failed: {observation.error}"
        )
    return observation.value


def build_binding(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> tuple[
    TraderLabCandidateBinding,
    ResearchPerformanceStatisticsSnapshot,
    dict[str, object],
]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R64 R59/R58 dependency drift")
    if specialist.CONFIG_FINGERPRINT != freeze.CANDIDATE_RULE_FINGERPRINT:
        raise ValueError("R64 R63 specialist identity drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    five = r60._candidate(five_stream, bars_by_symbol=five_bars)
    two = r60._candidate(two_stream, bars_by_symbol=two_bars)

    if len(five) != int(str(freeze.FIVE_YEAR["sample"])):
        raise ValueError("R64 5Y sample drift")
    if len(two) != int(str(freeze.RECENT_TWO_YEAR["sample"])):
        raise ValueError("R64 2Y sample drift")

    combined_bars: dict[str, tuple[Any, ...]] = {}
    for symbol in specialist.MARKETS:
        combined_bars[symbol] = tuple(
            sorted(
                (*five_bars[symbol], *two_bars[symbol]),
                key=lambda bar: bar.opened_at.astimezone(UTC),
            )
        )

    all_items = [("5y", item) for item in five] + [
        ("2y", item) for item in two
    ]
    requested_start = min(
        min(bars[0].opened_at.astimezone(UTC) for bars in combined_bars.values()),
        min(item.signal_at.astimezone(UTC) for _window, item in all_items),
    )
    requested_end = max(
        max(bars[-1].closed_at.astimezone(UTC) for bars in combined_bars.values()),
        max(item.exited_at.astimezone(UTC) for _window, item in all_items),
    ) + timedelta(minutes=15)

    manifests = tuple(
        _dataset_manifest(
            symbol,
            combined_bars[symbol],
            requested_start=requested_start,
            requested_end=requested_end,
        )
        for symbol in specialist.MARKETS
    )
    binding = _strategy_binding(
        manifests=manifests,
        simulated_start=requested_start,
        simulated_end=requested_end,
    )
    candidate = _candidate(binding)

    all_items.sort(
        key=lambda row: (
            row[1].exited_at.astimezone(UTC),
            row[1].symbol,
            row[1].trade_id,
            row[0],
        )
    )
    observations = tuple(
        _observation(
            run=binding.run,
            item=item,
            window=window,
            evidence_ordinal=index,
        )
        for index, (window, item) in enumerate(all_items)
    )
    performance = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(
            _uid("performance-snapshot")
        ),
        observations=observations,
        observed_at=PROCESS_PERFORMANCE_AT,
    )
    if isinstance(performance, Failure):
        raise ValueError(
            f"R64 performance snapshot failed: {performance.error}"
        )
    total = sum(
        (item.return_rate for item in performance.value.observations),
        Decimal(),
    )
    if performance.value.sample_size != EXPECTED_SAMPLE:
        raise ValueError("R64 combined sample drift")
    if total != EXPECTED_TOTAL_R:
        raise ValueError(
            f"R64 total R drift: {total} != {EXPECTED_TOTAL_R}"
        )

    details: dict[str, object] = {
        "five_year_sample": len(five),
        "recent_two_year_sample": len(two),
        "combined_sample": performance.value.sample_size,
        "total_r": str(total),
        "expected_total_r": str(EXPECTED_TOTAL_R),
        "datasets": {
            manifest.scope.window.instrument.symbol: {
                "observation_count": manifest.observation_count,
                "gap_count": len(manifest.gaps),
                "evidence_digest": manifest.evidence_digest.value,
            }
            for manifest in manifests
        },
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
    }
    return candidate, performance.value, details


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, object]:
    candidate, performance, details = build_binding(
        nas100_root=nas100_root,
        sp500_root=sp500_root,
        us30_root=us30_root,
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_candidate": {
            "candidate_id": specialist.CANDIDATE_ID,
            "config_fingerprint": specialist.CONFIG_FINGERPRINT,
            "freeze_id": specialist.FREEZE_ID,
            "methodology_fingerprint": specialist.METHODOLOGY_FINGERPRINT,
        },
        "canonical_binding": {
            "candidate_fingerprint": candidate.fingerprint.value,
            "strategy_binding_fingerprint": (
                candidate.strategy_binding.binding_fingerprint.value
            ),
            "run_input_fingerprint": (
                candidate.strategy_binding.run.input_fingerprint.value
            ),
            "portfolio_instrument": specialist.PORTFOLIO_INSTRUMENT,
            "markets": list(specialist.MARKETS),
            "timeframes": list(specialist.TIMEFRAMES),
        },
        "performance": {
            "basis": performance.basis.value,
            "sample_size": performance.sample_size,
            "positive_count": performance.positive_count,
            "negative_count": performance.negative_count,
            "flat_count": performance.flat_count,
            "mean_return": str(performance.mean_return),
            "minimum_return": str(performance.minimum_return),
            "maximum_return": str(performance.maximum_return),
            "win_rate": str(performance.win_rate),
            "population_variance": str(performance.population_variance),
            "total_r": details["total_r"],
        },
        "reconciliation": {
            "five_year_sample": details["five_year_sample"],
            "recent_two_year_sample": details["recent_two_year_sample"],
            "combined_sample": details["combined_sample"],
            "expected_total_r": details["expected_total_r"],
            "total_r_exact_match": (
                details["total_r"] == details["expected_total_r"]
            ),
            "r59_dependency_match": True,
            "r63_specialist_contract_match": True,
        },
        "datasets": details["datasets"],
        "provenance": details["provenance"],
        "decision": "PASS_R64_CANONICAL_BINDING_CONTINUE_LIFECYCLE",
        "governance": {
            "binding_only": True,
            "candidate_retuned": False,
            "signals_suppressed": False,
            "fresh_holdout_claim": False,
            "consumed_evidence_only": True,
            "trader_certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "next_gate": (
            "R65_CANONICAL_LIFECYCLE_THROUGH_MONTE_CARLO_AND_AUTHORITIES"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "decision": report["decision"],
                "canonical_binding": report["canonical_binding"],
                "performance": report["performance"],
                "reconciliation": report["reconciliation"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
