"""Operationally passive cTrader DEMO M5 Phase20D observation bridge.

This module composes the already-frozen causal pieces into one call suitable
for the resident DEMO runtime.  It owns no sizing, Risk authorization, order
submission or broker mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_advanced_evidence import (
    AdvancedCe2iEvidenceSnapshot,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_regime import (
    PHASE20_DEMO_REGIME_POLICY_ID,
    build_phase20_demo_regime_state,
    phase20_demo_regime_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_shadow_risk import (
    build_demo_capability_risk_snapshot,
    observe_demo_capability_constraints,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardCollectedEpoch,
    Phase20ForwardEpochResult,
    seal_phase20_forward_observed_epoch_from_snapshots,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_snapshots import (
    build_phase20_forward_snapshot_bundle,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_m5_shadow_batch import (
    Phase20M5ShadowTerminal,
    build_ctrader_demo_m5_phase20_batch,
)
from qore.infrastructure.cibo_ce2i_phase20_shadow_observer import (
    Phase20ForwardShadowObservation,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_runtime_shadow import (
    Phase20T12RuntimeShadowSeal,
    seal_phase20_t12_runtime_shadow,
)
from qore.infrastructure.cibo_ce2i_phase20_t12_shadow_store import (
    DurableT12ShadowDecisionStore,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_runtime_shadow import (
    Phase20T13RuntimeShadowSeal,
    seal_phase20_t13_runtime_shadow,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_store import (
    DurableT13ShadowDecisionStore,
)
from qore.infrastructure.cibo_ce2i_phase20_t13_shadow_treatment_store import (
    DurableT13ShadowTreatmentStore,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot


@dataclass(frozen=True, slots=True)
class Phase20DemoM5PreparedShadow:
    """Pre-execution sealed causal evidence plus deterministic policy record."""

    result: Phase20ForwardEpochResult
    regime_policy_id: str
    regime_policy_sha256: str
    broker_mutation_performed: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.result, Phase20ForwardEpochResult):
            raise CiboCapitalManagementError(
                "Phase20D prepared shadow result must be canonical"
            )
        if self.regime_policy_id != PHASE20_DEMO_REGIME_POLICY_ID:
            raise CiboCapitalManagementError(
                "Phase20D prepared shadow regime policy drift"
            )
        if (
            not self.regime_policy_sha256.startswith("sha256:")
            or len(self.regime_policy_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase20D prepared shadow regime digest invalid"
            )
        if self.broker_mutation_performed or self.execution_authority:
            raise CiboCapitalManagementError(
                "Phase20D prepared shadow cannot mutate execution"
            )


@dataclass(frozen=True, slots=True)
class Phase20DemoM5RuntimeObservation:
    observation: Phase20ForwardShadowObservation
    regime_policy_id: str
    regime_policy_sha256: str
    t12_shadow: Phase20T12RuntimeShadowSeal | None = None
    t13_shadow: Phase20T13RuntimeShadowSeal | None = None
    broker_mutation_performed: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.observation, Phase20ForwardShadowObservation):
            raise CiboCapitalManagementError(
                "Phase20D runtime bridge observation must be canonical"
            )
        if self.regime_policy_id != PHASE20_DEMO_REGIME_POLICY_ID:
            raise CiboCapitalManagementError(
                "Phase20D runtime bridge regime policy drift"
            )
        if (
            not self.regime_policy_sha256.startswith("sha256:")
            or len(self.regime_policy_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Phase20D runtime bridge regime digest invalid"
            )
        if self.t12_shadow is not None:
            if not isinstance(
                self.t12_shadow,
                Phase20T12RuntimeShadowSeal,
            ):
                raise CiboCapitalManagementError(
                    "Phase20D runtime bridge T12 shadow must be canonical"
                )
            if (
                self.t12_shadow.decision_evidence_sha256
                != self.observation.collected.result.decision_record.evidence_sha256
            ):
                raise CiboCapitalManagementError(
                    "Phase20D runtime bridge T12 evidence binding drift"
                )
        if self.t13_shadow is not None:
            if not isinstance(
                self.t13_shadow,
                Phase20T13RuntimeShadowSeal,
            ):
                raise CiboCapitalManagementError(
                    "Phase20D runtime bridge T13 shadow must be canonical"
                )
            if (
                self.t13_shadow.decision_evidence_sha256
                != self.observation.collected.result.decision_record.evidence_sha256
            ):
                raise CiboCapitalManagementError(
                    "Phase20D runtime bridge T13 evidence binding drift"
                )
        if self.broker_mutation_performed or self.execution_authority:
            raise CiboCapitalManagementError(
                "Phase20D runtime bridge cannot mutate execution"
            )


def prepare_ctrader_demo_m5_phase20_epoch(
    *,
    epoch_scope: str,
    opened_at: datetime,
    deadline_at: datetime,
    terminals: tuple[Phase20M5ShadowTerminal, ...],
    decision_at: datetime | None = None,
    snapshots: tuple[M5BoundarySnapshot, ...],
    provider_specs: tuple[CTraderDemoSymbolSpecification, ...],
    evidence_store: DurablePhase20ForwardEvidenceStore,
    account_identity: CiboAccountCapitalIdentity,
    account_state: CTraderDemoAccountState,
    risk: DurableAccountWideRiskEngine,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    open_position_ids: tuple[int, ...],
    pending_broker_worst_case_loss_usd: Decimal,
    capital_state: VersionedCapitalSourceLedger,
    highest_closed_balance: Decimal,
    current_step: int,
    advanced_evidence_snapshot: AdvancedCe2iEvidenceSnapshot | None = None,
    collector_git_sha: str | None = None,
) -> Phase20DemoM5PreparedShadow:
    """Seal one complete M5 shadow epoch without changing the execution path."""

    batch = build_ctrader_demo_m5_phase20_batch(
        epoch_scope=epoch_scope,
        opened_at=opened_at,
        deadline_at=deadline_at,
        terminals=terminals,
        decision_at=decision_at,
    )
    open_ids = set(open_position_ids)
    open_risks = tuple(
        item
        for item in executed_risk_book.evidences
        if item.position_id in open_ids
    )
    risk_snapshot = build_demo_capability_risk_snapshot(
        account_binding_id=account_identity.account_ref,
        account_state=account_state,
        open_position_ids=open_position_ids,
        open_executed_risks=open_risks,
        pending_broker_worst_case_loss_usd=pending_broker_worst_case_loss_usd,
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(
            risk_snapshot,
            now=batch.decision_at,
        )
    constraints = observe_demo_capability_constraints(
        risk=risk,
        snapshot=risk_snapshot,
        observed_at=batch.decision_at,
    )
    regime = build_phase20_demo_regime_state(
        decision_at=batch.decision_at,
        opportunity_count=len(batch.opportunities),
        snapshots=snapshots,
        provider_specs=provider_specs,
        account_state=account_state,
        risk_snapshot=risk_snapshot,
        risk_constraints=constraints,
        highest_closed_balance=highest_closed_balance,
    )
    snapshots_bundle = build_phase20_forward_snapshot_bundle(
        account_snapshot=risk_snapshot,
        risk_constraints=constraints,
        capital_state=capital_state,
        captured_at=account_state.observed_at,
    )
    result = seal_phase20_forward_observed_epoch_from_snapshots(
        store=evidence_store,
        decision_epoch_id=batch.decision_epoch_id,
        decision_at=batch.decision_at,
        account_identity=account_identity,
        snapshots=snapshots_bundle,
        concentration_limit_by_group=(),
        regime_state=regime,
        current_step=current_step,
        population_slots=batch.population_slots,
        opportunities=batch.opportunities,
        advanced_evidence_snapshot=advanced_evidence_snapshot,
        seal_deadline_at=batch.deadline_at,
        collector_git_sha=collector_git_sha,
    )
    return Phase20DemoM5PreparedShadow(
        result=result,
        regime_policy_id=PHASE20_DEMO_REGIME_POLICY_ID,
        regime_policy_sha256=phase20_demo_regime_policy_sha256(),
    )


def finalize_ctrader_demo_m5_phase20_policy(
    *,
    prepared: Phase20DemoM5PreparedShadow,
    evidence_store: DurablePhase20ForwardEvidenceStore,
    policy_store: DurablePhase20ForwardPolicyStore,
    t12_shadow_store: DurableT12ShadowDecisionStore | None = None,
    t13_recommendation_store: DurableT13ShadowDecisionStore | None = None,
    t13_treatment_store: DurableT13ShadowTreatmentStore | None = None,
) -> Phase20DemoM5RuntimeObservation:
    """Persist the already-computed policy record without rereading markets/outcomes."""

    if not isinstance(prepared, Phase20DemoM5PreparedShadow):
        raise CiboCapitalManagementError(
            "Phase20D finalization requires prepared shadow evidence"
        )
    if (t13_recommendation_store is None) != (
        t13_treatment_store is None
    ):
        raise CiboCapitalManagementError(
            "Phase20D T13 runtime stores must be provided together"
        )
    current_policy = policy_store.load()
    policy_book = policy_store.seal_policy_decision(
        prepared.result.decision_record,
        evidence_store=evidence_store,
        expected_generation=current_policy.generation,
    )
    t12_shadow = None
    if t12_shadow_store is not None:
        t12_shadow = seal_phase20_t12_runtime_shadow(
            evidence=prepared.result.evidence,
            decision_record=prepared.result.decision_record,
            evidence_book=evidence_store.load(),
            policy_book=policy_book,
            shadow_store=t12_shadow_store,
        )
    t13_shadow = None
    if (
        t13_recommendation_store is not None
        and t13_treatment_store is not None
    ):
        t13_shadow = seal_phase20_t13_runtime_shadow(
            evidence=prepared.result.evidence,
            decision_record=prepared.result.decision_record,
            evidence_book=evidence_store.load(),
            policy_book=policy_book,
            recommendation_store=t13_recommendation_store,
            treatment_store=t13_treatment_store,
        )
    collected = Phase20ForwardCollectedEpoch(
        evidence_generation=prepared.result.sealed_generation,
        policy_generation=policy_book.generation,
        result=prepared.result,
    )
    return Phase20DemoM5RuntimeObservation(
        observation=Phase20ForwardShadowObservation(collected=collected),
        regime_policy_id=prepared.regime_policy_id,
        regime_policy_sha256=prepared.regime_policy_sha256,
        t12_shadow=t12_shadow,
        t13_shadow=t13_shadow,
    )


def observe_ctrader_demo_m5_phase20_epoch(
    *,
    epoch_scope: str,
    opened_at: datetime,
    deadline_at: datetime,
    terminals: tuple[Phase20M5ShadowTerminal, ...],
    decision_at: datetime | None = None,
    snapshots: tuple[M5BoundarySnapshot, ...],
    provider_specs: tuple[CTraderDemoSymbolSpecification, ...],
    evidence_store: DurablePhase20ForwardEvidenceStore,
    policy_store: DurablePhase20ForwardPolicyStore,
    t12_shadow_store: DurableT12ShadowDecisionStore | None = None,
    t13_recommendation_store: DurableT13ShadowDecisionStore | None = None,
    t13_treatment_store: DurableT13ShadowTreatmentStore | None = None,
    account_identity: CiboAccountCapitalIdentity,
    account_state: CTraderDemoAccountState,
    risk: DurableAccountWideRiskEngine,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    open_position_ids: tuple[int, ...],
    pending_broker_worst_case_loss_usd: Decimal,
    capital_state: VersionedCapitalSourceLedger,
    highest_closed_balance: Decimal,
    current_step: int,
    advanced_evidence_snapshot: AdvancedCe2iEvidenceSnapshot | None = None,
    collector_git_sha: str | None = None,
) -> Phase20DemoM5RuntimeObservation:
    """Convenience composition; runtime may split prepare/finalize around submit."""

    prepared = prepare_ctrader_demo_m5_phase20_epoch(
        epoch_scope=epoch_scope,
        opened_at=opened_at,
        deadline_at=deadline_at,
        terminals=terminals,
        decision_at=decision_at,
        snapshots=snapshots,
        provider_specs=provider_specs,
        evidence_store=evidence_store,
        account_identity=account_identity,
        account_state=account_state,
        risk=risk,
        executed_risk_book=executed_risk_book,
        open_position_ids=open_position_ids,
        pending_broker_worst_case_loss_usd=pending_broker_worst_case_loss_usd,
        capital_state=capital_state,
        highest_closed_balance=highest_closed_balance,
        current_step=current_step,
        advanced_evidence_snapshot=advanced_evidence_snapshot,
        collector_git_sha=collector_git_sha,
    )
    return finalize_ctrader_demo_m5_phase20_policy(
        prepared=prepared,
        evidence_store=evidence_store,
        policy_store=policy_store,
        t12_shadow_store=t12_shadow_store,
        t13_recommendation_store=t13_recommendation_store,
        t13_treatment_store=t13_treatment_store,
    )
