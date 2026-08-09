from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.functional.decisions import DecisionId
from qore.infrastructure.futures_adapter_contracts import (
    FuturesExecutionEnvironment,
    FuturesExecutionObservation,
    FuturesExecutionReconciliation,
    FuturesExecutionReconciliationStatus,
    FuturesExecutionRequestId,
    FuturesExecutionState,
    FuturesProviderName,
)
from qore.infrastructure.futures_cross_provider_certification import (
    FuturesCrossProviderState,
)
from qore.infrastructure.futures_shadow_core import FuturesShadowCertificationStatus
from qore.infrastructure.hosting_reliability_drill import (
    HostingReliabilityDrillCertificationStatus,
)
from qore.kernel.errors import InfrastructureError

TRADESTATION_PROVIDER = FuturesProviderName("tradestation")
IBKR_PROVIDER = FuturesProviderName("ibkr")
TASTYTRADE_PROVIDER = FuturesProviderName("tastytrade")


class FuturesPaperE2EError(InfrastructureError):
    """Base error for deterministic Paper Futures E2E certification."""

    __slots__ = ()


class FuturesPaperE2EValidationError(FuturesPaperE2EError):
    """Violation of a deterministic Paper Futures E2E invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise FuturesPaperE2EValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise FuturesPaperE2EValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise FuturesPaperE2EValidationError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class FuturesPaperE2EEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="Paper Futures E2E evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesPaperE2EReportId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="Paper Futures E2E report id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesPaperE2EPrerequisiteSnapshot:
    """Evidence gate proving the deterministic pre-Paper requirements were satisfied."""

    shadow_status: FuturesShadowCertificationStatus
    reliability_drill_status: HostingReliabilityDrillCertificationStatus
    cross_provider_state: FuturesCrossProviderState
    evaluated_at: datetime
    evidence_refs: tuple[FuturesPaperE2EEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.shadow_status, FuturesShadowCertificationStatus):
            raise FuturesPaperE2EValidationError(
                "shadow_status must be FuturesShadowCertificationStatus"
            )
        if not isinstance(
            self.reliability_drill_status,
            HostingReliabilityDrillCertificationStatus,
        ):
            raise FuturesPaperE2EValidationError(
                "reliability_drill_status must be HostingReliabilityDrillCertificationStatus"
            )
        if not isinstance(self.cross_provider_state, FuturesCrossProviderState):
            raise FuturesPaperE2EValidationError(
                "cross_provider_state must be FuturesCrossProviderState"
            )
        if self.shadow_status not in {
            FuturesShadowCertificationStatus.CERTIFIED_OFFLINE,
            FuturesShadowCertificationStatus.CERTIFIED_READ_ONLY_OPERATIONAL,
        }:
            raise FuturesPaperE2EValidationError(
                "Paper E2E requires certified Shadow Core evidence"
            )
        if self.reliability_drill_status is not (
            HostingReliabilityDrillCertificationStatus.CERTIFIED_OFFLINE
        ):
            raise FuturesPaperE2EValidationError(
                "Paper E2E requires certified reliability drill evidence"
            )
        if self.cross_provider_state not in {
            FuturesCrossProviderState.CERTIFIED,
            FuturesCrossProviderState.DELAY_AWARE_CERTIFIED,
        }:
            raise FuturesPaperE2EValidationError(
                "Paper E2E requires certified cross-provider evidence"
            )
        _validate_timestamp(self.evaluated_at, field_name="Paper E2E prerequisites evaluated_at")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, FuturesPaperE2EEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise FuturesPaperE2EValidationError(
                "Paper E2E prerequisites require immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise FuturesPaperE2EValidationError(
                "Paper E2E prerequisite evidence refs must be unique"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.shadow_status.value,
            self.reliability_drill_status.value,
            self.cross_provider_state.value,
            self.evaluated_at.isoformat(),
            tuple(ref.logical_values() for ref in self.evidence_refs),
        )


class FuturesPaperE2EScenario(StrEnum):
    PARTIAL_FILL_THEN_FILL = "partial_fill_then_fill"
    REJECTED = "rejected"
    LOST_ACK_RECONCILED = "lost_ack_reconciled"


_REQUIRED_PROVIDER_ENVIRONMENTS: dict[
    FuturesProviderName,
    FuturesExecutionEnvironment,
] = {
    TRADESTATION_PROVIDER: FuturesExecutionEnvironment.SIMULATION,
    IBKR_PROVIDER: FuturesExecutionEnvironment.PAPER,
    TASTYTRADE_PROVIDER: FuturesExecutionEnvironment.SIMULATION,
}

_REQUIRED_CASES = frozenset(
    (provider, scenario)
    for provider in _REQUIRED_PROVIDER_ENVIRONMENTS
    for scenario in FuturesPaperE2EScenario
)


@dataclass(frozen=True, slots=True)
class FuturesPaperE2ECaseResult:
    """One isolated provider/scenario case; no provider I/O is performed here."""

    provider: FuturesProviderName
    environment: FuturesExecutionEnvironment
    scenario: FuturesPaperE2EScenario
    decision_id: DecisionId
    request_id: FuturesExecutionRequestId
    requested_quantity: int
    observations: tuple[FuturesExecutionObservation, ...]
    reconciliation: FuturesExecutionReconciliation
    provider_translation_evidence_ref: FuturesPaperE2EEvidenceReference
    completed_at: datetime
    network_io_performed: bool
    production_execution_performed: bool
    automatic_redispatch_triggered: bool

    def __post_init__(self) -> None:
        if not isinstance(self.provider, FuturesProviderName):
            raise FuturesPaperE2EValidationError("provider must be FuturesProviderName")
        expected_environment = _REQUIRED_PROVIDER_ENVIRONMENTS.get(self.provider)
        if expected_environment is None:
            raise FuturesPaperE2EValidationError(
                "Paper E2E provider must be TradeStation, IBKR or tastytrade"
            )
        if self.environment is not expected_environment:
            raise FuturesPaperE2EValidationError(
                "Paper E2E provider environment does not match certified adapter boundary"
            )
        if not isinstance(self.scenario, FuturesPaperE2EScenario):
            raise FuturesPaperE2EValidationError(
                "scenario must be FuturesPaperE2EScenario"
            )
        if not isinstance(self.decision_id, DecisionId) or not isinstance(
            self.decision_id.value, UUID
        ):
            raise FuturesPaperE2EValidationError(
                "decision_id must be UUID-backed canonical DecisionId"
            )
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise FuturesPaperE2EValidationError(
                "request_id must be FuturesExecutionRequestId"
            )
        if type(self.requested_quantity) is not int or self.requested_quantity <= 0:
            raise FuturesPaperE2EValidationError(
                "requested_quantity must be a positive integer"
            )
        if not isinstance(self.observations, tuple) or not self.observations or any(
            not isinstance(item, FuturesExecutionObservation)
            for item in self.observations
        ):
            raise FuturesPaperE2EValidationError(
                "observations must be a non-empty immutable execution observation tuple"
            )
        if any(item.request_id != self.request_id for item in self.observations):
            raise FuturesPaperE2EValidationError(
                "all observations must bind exact Paper E2E request id"
            )
        if tuple(item.observed_at for item in self.observations) != tuple(
            sorted(item.observed_at for item in self.observations)
        ):
            raise FuturesPaperE2EValidationError(
                "Paper E2E observations must be chronological"
            )
        if not isinstance(self.reconciliation, FuturesExecutionReconciliation):
            raise FuturesPaperE2EValidationError(
                "reconciliation must be FuturesExecutionReconciliation"
            )
        if self.reconciliation.request_id != self.request_id:
            raise FuturesPaperE2EValidationError(
                "reconciliation must bind exact Paper E2E request id"
            )
        if self.reconciliation.status is not FuturesExecutionReconciliationStatus.MATCHED:
            raise FuturesPaperE2EValidationError(
                "Paper E2E case requires final MATCHED reconciliation"
            )
        if self.reconciliation.reconciled_at < self.observations[-1].observed_at:
            raise FuturesPaperE2EValidationError(
                "Paper E2E reconciliation cannot predate final observation"
            )
        if not isinstance(
            self.provider_translation_evidence_ref,
            FuturesPaperE2EEvidenceReference,
        ):
            raise FuturesPaperE2EValidationError(
                "provider_translation_evidence_ref must be FuturesPaperE2EEvidenceReference"
            )
        _validate_timestamp(self.completed_at, field_name="Paper E2E completed_at")
        if self.completed_at < self.reconciliation.reconciled_at:
            raise FuturesPaperE2EValidationError(
                "Paper E2E case cannot complete before reconciliation"
            )
        for field_name, value in (
            ("network_io_performed", self.network_io_performed),
            ("production_execution_performed", self.production_execution_performed),
            ("automatic_redispatch_triggered", self.automatic_redispatch_triggered),
        ):
            if type(value) is not bool:
                raise FuturesPaperE2EValidationError(f"{field_name} must be bool")
            if value:
                raise FuturesPaperE2EValidationError(
                    f"{field_name} must remain false in deterministic Paper E2E"
                )
        self._validate_scenario_evidence()

    def _validate_scenario_evidence(self) -> None:
        states = tuple(item.state for item in self.observations)
        fills = tuple(item.cumulative_filled_quantity for item in self.observations)
        if self.scenario is FuturesPaperE2EScenario.PARTIAL_FILL_THEN_FILL:
            if states != (
                FuturesExecutionState.ACKNOWLEDGED,
                FuturesExecutionState.PARTIALLY_FILLED,
                FuturesExecutionState.FILLED,
            ):
                raise FuturesPaperE2EValidationError(
                    "partial-fill case requires ACK -> PARTIAL -> FILLED evidence"
                )
            if not 0 < fills[1] < self.requested_quantity:
                raise FuturesPaperE2EValidationError(
                    "partial-fill evidence must remain below requested quantity"
                )
            if fills[0] != 0 or fills[2] != self.requested_quantity:
                raise FuturesPaperE2EValidationError(
                    "fill case must finish at exact requested quantity"
                )
        elif self.scenario is FuturesPaperE2EScenario.REJECTED:
            if states != (FuturesExecutionState.REJECTED,) or fills != (0,):
                raise FuturesPaperE2EValidationError(
                    "rejected case requires one zero-fill REJECTED observation"
                )
        elif states != (FuturesExecutionState.AMBIGUOUS,) or fills != (0,):
            raise FuturesPaperE2EValidationError(
                "lost-ACK case requires one zero-fill AMBIGUOUS observation before reconciliation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.environment.value,
            self.scenario.value,
            str(self.decision_id.value),
            self.request_id.logical_values(),
            self.requested_quantity,
            tuple(item.logical_values() for item in self.observations),
            self.reconciliation.logical_values(),
            self.provider_translation_evidence_ref.logical_values(),
            self.completed_at.isoformat(),
            self.network_io_performed,
            self.production_execution_performed,
            self.automatic_redispatch_triggered,
        )


class FuturesPaperE2ECertificationStatus(StrEnum):
    CERTIFIED_OFFLINE = "certified_offline"


@dataclass(frozen=True, slots=True)
class FuturesPaperE2EReport:
    report_id: FuturesPaperE2EReportId
    prerequisites: FuturesPaperE2EPrerequisiteSnapshot
    cases: tuple[FuturesPaperE2ECaseResult, ...]
    started_at: datetime
    ended_at: datetime
    reported_at: datetime
    evidence_ref: FuturesPaperE2EEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, FuturesPaperE2EReportId):
            raise FuturesPaperE2EValidationError(
                "report_id must be FuturesPaperE2EReportId"
            )
        if not isinstance(self.prerequisites, FuturesPaperE2EPrerequisiteSnapshot):
            raise FuturesPaperE2EValidationError(
                "prerequisites must be FuturesPaperE2EPrerequisiteSnapshot"
            )
        if not isinstance(self.cases, tuple) or any(
            not isinstance(item, FuturesPaperE2ECaseResult) for item in self.cases
        ):
            raise FuturesPaperE2EValidationError(
                "cases must be immutable FuturesPaperE2ECaseResult tuple"
            )
        case_keys = {(item.provider, item.scenario) for item in self.cases}
        if case_keys != _REQUIRED_CASES:
            raise FuturesPaperE2EValidationError(
                "Paper E2E report requires all 3 providers x all 3 scenarios"
            )
        if len(case_keys) != len(self.cases):
            raise FuturesPaperE2EValidationError(
                "Paper E2E report requires exactly one result per provider/scenario"
            )
        decision_ids = tuple(item.decision_id for item in self.cases)
        request_ids = tuple(item.request_id for item in self.cases)
        if len(decision_ids) != len(set(decision_ids)):
            raise FuturesPaperE2EValidationError(
                "each Paper E2E provider/scenario case requires a unique Core DecisionId"
            )
        if len(request_ids) != len(set(request_ids)):
            raise FuturesPaperE2EValidationError(
                "each Paper E2E provider/scenario case requires a unique request id"
            )
        _validate_timestamp(self.started_at, field_name="Paper E2E started_at")
        _validate_timestamp(self.ended_at, field_name="Paper E2E ended_at")
        _validate_timestamp(self.reported_at, field_name="Paper E2E reported_at")
        if self.ended_at <= self.started_at:
            raise FuturesPaperE2EValidationError(
                "Paper E2E ended_at must be after started_at"
            )
        if self.reported_at < self.ended_at:
            raise FuturesPaperE2EValidationError(
                "Paper E2E report cannot predate end"
            )
        if self.started_at < self.prerequisites.evaluated_at:
            raise FuturesPaperE2EValidationError(
                "Paper E2E cannot start before prerequisite evidence"
            )
        if any(item.completed_at > self.ended_at for item in self.cases):
            raise FuturesPaperE2EValidationError(
                "all Paper E2E cases must complete inside report window"
            )
        if not isinstance(self.evidence_ref, FuturesPaperE2EEvidenceReference):
            raise FuturesPaperE2EValidationError(
                "report evidence_ref must be FuturesPaperE2EEvidenceReference"
            )

    @property
    def certification_status(self) -> FuturesPaperE2ECertificationStatus:
        return FuturesPaperE2ECertificationStatus.CERTIFIED_OFFLINE

    @property
    def network_orders_submitted(self) -> int:
        return 0

    @property
    def production_orders_submitted(self) -> int:
        return 0

    @property
    def automatic_redispatches(self) -> int:
        return 0

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.report_id.logical_values(),
            self.prerequisites.logical_values(),
            tuple(item.logical_values() for item in self.cases),
            self.started_at.isoformat(),
            self.ended_at.isoformat(),
            self.reported_at.isoformat(),
            self.evidence_ref.logical_values(),
        )
