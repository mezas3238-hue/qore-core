"""cTrader DEMO Phase20D forward observer composition.

This is the research-only integration seam from a complete decision epoch and
actual DEMO account state into the frozen V2 shadow policy. It may reconcile the
shadow Risk ledger after restart, but it cannot authorize or mutate broker
orders.
"""

from __future__ import annotations

from datetime import timedelta
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
from qore.infrastructure.cibo_ce2i_phase20_demo_shadow_risk import (
    build_demo_capability_risk_snapshot,
    observe_demo_capability_constraints,
)
from qore.infrastructure.cibo_ce2i_phase20_epoch_aggregator import (
    Phase20DecisionEpochBatch,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardKnownOptionEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    DurablePhase20ForwardPolicyStore,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    DurablePhase20ForwardEvidenceStore,
)
from qore.infrastructure.cibo_ce2i_phase20_shadow_observer import (
    Phase20ForwardShadowObservation,
    observe_phase20_forward_batch,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState


def observe_ctrader_demo_phase20_batch(
    *,
    batch: Phase20DecisionEpochBatch,
    evidence_store: DurablePhase20ForwardEvidenceStore,
    policy_store: DurablePhase20ForwardPolicyStore,
    account_identity: CiboAccountCapitalIdentity,
    account_state: CTraderDemoAccountState,
    risk: DurableAccountWideRiskEngine,
    executed_risk_book: VersionedPhase20ExecutedRiskBook,
    open_position_ids: tuple[int, ...],
    pending_broker_worst_case_loss_usd: Decimal,
    capital_state: VersionedCapitalSourceLedger,
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...],
    regime_state: CiboCapitalRegimeState,
    current_step: int,
    advanced_evidence_snapshot: AdvancedCe2iEvidenceSnapshot | None = None,
    known_options: tuple[Phase20ForwardKnownOptionEvidence, ...] = (),
) -> Phase20ForwardShadowObservation:
    """Observe one actual DEMO epoch without changing its execution path."""

    if not isinstance(batch, Phase20DecisionEpochBatch):
        raise CiboCapitalManagementError(
            "Phase20D DEMO observer requires canonical epoch batch"
        )
    if not isinstance(executed_risk_book, VersionedPhase20ExecutedRiskBook):
        raise CiboCapitalManagementError(
            "Phase20D DEMO observer requires durable executed-risk book"
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
        pending_broker_worst_case_loss_usd=(
            pending_broker_worst_case_loss_usd
        ),
    )
    if risk.recovery_required:
        risk.complete_boot_reconciliation(
            risk_snapshot,
            now=batch.decision_at,
            max_snapshot_age=timedelta(seconds=2),
        )
    constraints = observe_demo_capability_constraints(
        risk=risk,
        snapshot=risk_snapshot,
        observed_at=batch.decision_at,
    )
    return observe_phase20_forward_batch(
        batch=batch,
        evidence_store=evidence_store,
        policy_store=policy_store,
        account_identity=account_identity,
        account_snapshot=risk_snapshot,
        risk_constraints=constraints,
        capital_state=capital_state,
        capital_captured_at=account_state.observed_at,
        concentration_limit_by_group=concentration_limit_by_group,
        regime_state=regime_state,
        current_step=current_step,
        advanced_evidence_snapshot=advanced_evidence_snapshot,
        known_options=known_options,
    )
