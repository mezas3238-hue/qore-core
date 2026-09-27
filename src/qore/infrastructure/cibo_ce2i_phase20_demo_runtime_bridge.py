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
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
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
    observe_phase20_forward_batch,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot


@dataclass(frozen=True, slots=True)
class Phase20DemoM5RuntimeObservation:
    observation: Phase20ForwardShadowObservation
    regime_policy_id: str
    regime_policy_sha256: str
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
        if self.broker_mutation_performed or self.execution_authority:
            raise CiboCapitalManagementError(
                "Phase20D runtime bridge cannot mutate execution"
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
    account_identity: CiboAccountCapitalIdentity,
    account_state: CTraderDemoAccountState,
    risk: DurableAccountWideRiskEngine,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    open_position_ids: tuple[int, ...],
    pending_broker_worst_case_loss_usd: Decimal,
    capital_state: VersionedCapitalSourceLedger,
    highest_closed_balance: Decimal,
    current_step: int,
) -> Phase20DemoM5RuntimeObservation:
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
    observation = observe_phase20_forward_batch(
        batch=batch,
        evidence_store=evidence_store,
        policy_store=policy_store,
        account_identity=account_identity,
        account_snapshot=risk_snapshot,
        risk_constraints=constraints,
        capital_state=capital_state,
        capital_captured_at=account_state.observed_at,
        concentration_limit_by_group=(),
        regime_state=regime,
        current_step=current_step,
    )
    return Phase20DemoM5RuntimeObservation(
        observation=observation,
        regime_policy_id=PHASE20_DEMO_REGIME_POLICY_ID,
        regime_policy_sha256=phase20_demo_regime_policy_sha256(),
    )
