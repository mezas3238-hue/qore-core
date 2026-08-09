from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

import qore.infrastructure.futures_adapter_contracts as futures
import qore.infrastructure.futures_cross_provider_certification as cross
import qore.infrastructure.futures_paper_e2e as paper
import qore.infrastructure.futures_shadow_core as shadow
import qore.infrastructure.hosting_reliability_drill as drill
from qore.functional.decisions import DecisionId

_BASE = datetime(2026, 8, 9, 16, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"69000000-0000-0000-0000-{suffix:012d}")


def _evidence(suffix: int) -> paper.FuturesPaperE2EEvidenceReference:
    return paper.FuturesPaperE2EEvidenceReference(_uuid(suffix))


def _environment(
    provider: futures.FuturesProviderName,
) -> futures.FuturesExecutionEnvironment:
    if provider == paper.IBKR_PROVIDER:
        return futures.FuturesExecutionEnvironment.PAPER
    return futures.FuturesExecutionEnvironment.SIMULATION


def _observation(
    request_id: futures.FuturesExecutionRequestId,
    state: futures.FuturesExecutionState,
    filled: int,
    *,
    suffix: int,
    observed_at: datetime,
) -> futures.FuturesExecutionObservation:
    provider_ref = None
    if state in {
        futures.FuturesExecutionState.ACKNOWLEDGED,
        futures.FuturesExecutionState.PARTIALLY_FILLED,
        futures.FuturesExecutionState.FILLED,
    }:
        provider_ref = futures.FuturesProviderOrderReference(f"e2e-{suffix}")
    return futures.FuturesExecutionObservation(
        observation_id=futures.FuturesExecutionObservationId(_uuid(suffix)),
        request_id=request_id,
        state=state,
        provider_order_ref=provider_ref,
        cumulative_filled_quantity=filled,
        observed_at=observed_at,
        evidence_ref=futures.FuturesExecutionEvidenceReference(_uuid(suffix + 1000)),
    )


def _case(
    provider: futures.FuturesProviderName,
    scenario: paper.FuturesPaperE2EScenario,
    *,
    suffix: int,
) -> paper.FuturesPaperE2ECaseResult:
    request_id = futures.FuturesExecutionRequestId(_uuid(suffix))
    at = _BASE + timedelta(seconds=suffix)
    if scenario is paper.FuturesPaperE2EScenario.PARTIAL_FILL_THEN_FILL:
        observations = (
            _observation(
                request_id,
                futures.FuturesExecutionState.ACKNOWLEDGED,
                0,
                suffix=suffix + 10,
                observed_at=at,
            ),
            _observation(
                request_id,
                futures.FuturesExecutionState.PARTIALLY_FILLED,
                1,
                suffix=suffix + 20,
                observed_at=at + timedelta(milliseconds=1),
            ),
            _observation(
                request_id,
                futures.FuturesExecutionState.FILLED,
                2,
                suffix=suffix + 30,
                observed_at=at + timedelta(milliseconds=2),
            ),
        )
    elif scenario is paper.FuturesPaperE2EScenario.REJECTED:
        observations = (
            _observation(
                request_id,
                futures.FuturesExecutionState.REJECTED,
                0,
                suffix=suffix + 40,
                observed_at=at,
            ),
        )
    else:
        observations = (
            _observation(
                request_id,
                futures.FuturesExecutionState.AMBIGUOUS,
                0,
                suffix=suffix + 50,
                observed_at=at,
            ),
        )
    reconciliation = futures.FuturesExecutionReconciliation(
        request_id=request_id,
        status=futures.FuturesExecutionReconciliationStatus.MATCHED,
        reconciled_at=observations[-1].observed_at + timedelta(milliseconds=1),
        evidence_refs=(
            futures.FuturesExecutionEvidenceReference(_uuid(suffix + 2000)),
        ),
    )
    return paper.FuturesPaperE2ECaseResult(
        provider=provider,
        environment=_environment(provider),
        scenario=scenario,
        decision_id=DecisionId(_uuid(suffix + 3000)),
        request_id=request_id,
        requested_quantity=2,
        observations=observations,
        reconciliation=reconciliation,
        provider_translation_evidence_ref=_evidence(suffix + 4000),
        completed_at=reconciliation.reconciled_at + timedelta(milliseconds=1),
        network_io_performed=False,
        production_execution_performed=False,
        automatic_redispatch_triggered=False,
    )


def _prerequisites() -> paper.FuturesPaperE2EPrerequisiteSnapshot:
    return paper.FuturesPaperE2EPrerequisiteSnapshot(
        shadow_status=shadow.FuturesShadowCertificationStatus.CERTIFIED_OFFLINE,
        reliability_drill_status=(
            drill.HostingReliabilityDrillCertificationStatus.CERTIFIED_OFFLINE
        ),
        cross_provider_state=cross.FuturesCrossProviderState.DELAY_AWARE_CERTIFIED,
        evaluated_at=_BASE,
        evidence_refs=(_evidence(9000),),
    )


def _cases() -> tuple[paper.FuturesPaperE2ECaseResult, ...]:
    values: list[paper.FuturesPaperE2ECaseResult] = []
    suffix = 100
    for provider in (
        paper.TRADESTATION_PROVIDER,
        paper.IBKR_PROVIDER,
        paper.TASTYTRADE_PROVIDER,
    ):
        for scenario in paper.FuturesPaperE2EScenario:
            values.append(_case(provider, scenario, suffix=suffix))
            suffix += 10
    return tuple(values)


def test_complete_three_provider_matrix_is_certified_offline() -> None:
    report = paper.FuturesPaperE2EReport(
        report_id=paper.FuturesPaperE2EReportId(_uuid(9100)),
        prerequisites=_prerequisites(),
        cases=_cases(),
        started_at=_BASE,
        ended_at=_BASE + timedelta(minutes=10),
        reported_at=_BASE + timedelta(minutes=11),
        evidence_ref=_evidence(9101),
    )

    assert len(report.cases) == 9
    assert report.certification_status is (
        paper.FuturesPaperE2ECertificationStatus.CERTIFIED_OFFLINE
    )
    assert report.network_orders_submitted == 0
    assert report.production_orders_submitted == 0
    assert report.automatic_redispatches == 0


def test_lost_ack_requires_final_matched_reconciliation() -> None:
    case = _case(
        paper.IBKR_PROVIDER,
        paper.FuturesPaperE2EScenario.LOST_ACK_RECONCILED,
        suffix=500,
    )
    unresolved = replace(
        case.reconciliation,
        status=futures.FuturesExecutionReconciliationStatus.AMBIGUOUS,
    )
    with pytest.raises(paper.FuturesPaperE2EValidationError):
        replace(case, reconciliation=unresolved)


def test_provider_environment_and_prerequisite_certification_fail_closed() -> None:
    case = _case(
        paper.IBKR_PROVIDER,
        paper.FuturesPaperE2EScenario.REJECTED,
        suffix=520,
    )
    with pytest.raises(paper.FuturesPaperE2EValidationError):
        replace(case, environment=futures.FuturesExecutionEnvironment.SIMULATION)

    with pytest.raises(paper.FuturesPaperE2EValidationError):
        replace(
            _prerequisites(),
            cross_provider_state=cross.FuturesCrossProviderState.DISAGREEMENT,
        )


def test_report_requires_every_provider_scenario_exactly_once() -> None:
    cases = _cases()
    with pytest.raises(paper.FuturesPaperE2EValidationError):
        paper.FuturesPaperE2EReport(
            report_id=paper.FuturesPaperE2EReportId(_uuid(9200)),
            prerequisites=_prerequisites(),
            cases=cases[:-1],
            started_at=_BASE,
            ended_at=_BASE + timedelta(minutes=10),
            reported_at=_BASE + timedelta(minutes=11),
            evidence_ref=_evidence(9201),
        )
