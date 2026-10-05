"""Prepare and execute one causal single-account CIBO ceiling epoch.

This seam joins the account-state builder, explicit provider Risk snapshot and
Native MAX sovereign executor. It remains strictly predecision: no settlement
or outcome surface is accepted by this API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    ProviderRiskBudget,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_single_account_ceiling_risk import (
    build_ceiling_risk_snapshot,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingAccountState,
    CiboCeilingEpochState,
    CiboCeilingOpportunityEvidence,
    build_ceiling_epoch_state,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_executor import (
    CiboSovereignCeilingEpochResult,
    execute_sovereign_ceiling_epoch,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef


@dataclass(frozen=True, slots=True)
class CiboPreparedSovereignCeilingEpoch:
    epoch_state: CiboCeilingEpochState
    risk_snapshot: AccountRiskSnapshot
    execution: CiboSovereignCeilingEpochResult


def run_predecision_sovereign_ceiling_epoch(
    *,
    decision_epoch_id: str,
    decision_at: datetime,
    expires_at: datetime,
    account: CiboCeilingAccountState,
    opportunities: tuple[CiboCeilingOpportunityEvidence, ...],
    regime_state: CiboCapitalRegimeState,
    evidence_ref: CiboEvidenceRef,
    mission_policy: CiboCapitalMissionPolicy,
    risk_engine: AccountWideRiskEngine,
    provider_budget: ProviderRiskBudget,
    provider_free_margin_usd: Decimal,
    open_floating_loss_usd: Decimal,
    pending_broker_worst_case_loss_usd: Decimal,
    qore_authorizable_headroom_usd: Decimal,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
) -> CiboPreparedSovereignCeilingEpoch:
    """Run one full simultaneous Native MAX surface with no outcome access."""

    epoch = build_ceiling_epoch_state(
        account=account,
        captured_at=decision_at,
        expires_at=expires_at,
        opportunities=opportunities,
    )
    snapshot = build_ceiling_risk_snapshot(
        account=epoch.account,
        provider_budget=provider_budget,
        reconciled_at=decision_at,
        provider_free_margin_usd=provider_free_margin_usd,
        open_floating_loss_usd=open_floating_loss_usd,
        pending_broker_worst_case_loss_usd=(
            pending_broker_worst_case_loss_usd
        ),
        qore_authorizable_headroom_usd=qore_authorizable_headroom_usd,
    )
    envelopes = tuple(item.opportunity for item in opportunities)
    option_id_by_signal = tuple(
        (
            item.signal_fingerprint,
            "ceiling:" + item.signal_fingerprint,
        )
        for item in envelopes
    )
    execution = execute_sovereign_ceiling_epoch(
        decision_epoch_id=decision_epoch_id,
        decision_at=decision_at,
        expires_at=expires_at,
        opportunities=envelopes,
        option_id_by_signal=option_id_by_signal,
        twin=epoch.twin,
        capital=epoch.capital,
        regime_state=regime_state,
        evidence_ref=evidence_ref,
        mission_policy=mission_policy,
        risk_snapshot=snapshot,
        risk_engine=risk_engine,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
    )
    return CiboPreparedSovereignCeilingEpoch(
        epoch_state=epoch,
        risk_snapshot=snapshot,
        execution=execution,
    )
