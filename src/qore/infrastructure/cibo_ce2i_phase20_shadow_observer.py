"""Canonical non-mutating bridge from a sealed decision epoch into Phase20D.

The bridge accepts only canonical account/Risk/capital state, derives
content-bound snapshot identities, and persists the observational V2 decision.
It has no broker mutation path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskCapitalConstraintEnvelope,
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
from qore.infrastructure.cibo_ce2i_phase20_epoch_aggregator import (
    Phase20DecisionEpochBatch,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_epoch import (
    Phase20ForwardCollectedEpoch,
    collect_phase20_forward_observed_epoch,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_evidence import (
    Phase20ForwardKnownOptionEvidence,
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
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
)


@dataclass(frozen=True, slots=True)
class Phase20ForwardShadowObservation:
    """Auditable shadow result with explicit no-mutation governance."""

    collected: Phase20ForwardCollectedEpoch
    broker_mutation_performed: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.collected, Phase20ForwardCollectedEpoch):
            raise CiboCapitalManagementError(
                "Phase20D shadow observation must contain canonical collection"
            )
        if (
            self.broker_mutation_performed
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Phase20D shadow observer cannot gain operational authority"
            )


def observe_phase20_forward_batch(
    *,
    batch: Phase20DecisionEpochBatch,
    evidence_store: DurablePhase20ForwardEvidenceStore,
    policy_store: DurablePhase20ForwardPolicyStore,
    account_identity: CiboAccountCapitalIdentity,
    account_snapshot: AccountRiskSnapshot,
    risk_constraints: RiskCapitalConstraintEnvelope,
    capital_state: VersionedCapitalSourceLedger,
    capital_captured_at: datetime,
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...],
    regime_state: CiboCapitalRegimeState,
    current_step: int,
    advanced_evidence_snapshot: AdvancedCe2iEvidenceSnapshot | None = None,
    known_options: tuple[Phase20ForwardKnownOptionEvidence, ...] = (),
) -> Phase20ForwardShadowObservation:
    """Persist one complete portfolio epoch without changing execution."""

    if not isinstance(batch, Phase20DecisionEpochBatch):
        raise CiboCapitalManagementError(
            "Phase20D shadow observer requires canonical epoch batch"
        )
    if regime_state.opportunity_count != len(batch.opportunities):
        raise CiboCapitalManagementError(
            "Phase20D regime count must match sealed batch candidates"
        )
    snapshots = build_phase20_forward_snapshot_bundle(
        account_snapshot=account_snapshot,
        risk_constraints=risk_constraints,
        capital_state=capital_state,
        captured_at=capital_captured_at,
    )
    collected = collect_phase20_forward_observed_epoch(
        evidence_store=evidence_store,
        policy_store=policy_store,
        decision_epoch_id=batch.decision_epoch_id,
        decision_at=batch.decision_at,
        account_identity=account_identity,
        snapshots=snapshots,
        concentration_limit_by_group=concentration_limit_by_group,
        regime_state=regime_state,
        current_step=current_step,
        population_slots=batch.population_slots,
        opportunities=batch.opportunities,
        advanced_evidence_snapshot=advanced_evidence_snapshot,
        known_options=known_options,
    )
    return Phase20ForwardShadowObservation(collected=collected)
