"""Research-only Risk snapshot for cTrader DEMO capability discovery.

cTrader DEMO has no FundedNext-style maximum-loss rule. Phase20D therefore
must not fabricate one. This profile exposes only solvency/margin constraints
from the actual DEMO account plus fully reconciled open/pending risk.

It is a shadow observation surface. It does not authorize execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    DurableAccountWideRiskEngine,
    RiskCapitalConstraintEnvelope,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.ctrader_demo_gateway import CTraderDemoAccountState

DEMO_CAPABILITY_SHADOW_RISK_POLICY_ID = (
    "CIBO_DEMO_CAPABILITY_SOLVENCY_ONLY_RISK_V1"
)


@dataclass(slots=True)
class CiboDemoCapabilitySolvencyBudget:
    """Protocol-compatible provider budget derived only from actual solvency."""

    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool

    def __post_init__(self) -> None:
        for name in (
            "provider_headroom",
            "max_risk_at_any_time",
            "active_mll",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"DEMO shadow Risk {name} must be finite non-negative"
                )
        if type(self.hard_breach) is not bool:
            raise CiboCapitalManagementError(
                "DEMO shadow Risk hard_breach must be bool"
            )


def demo_capability_shadow_risk_policy_sha256() -> str:
    payload = {
        "policy_id": DEMO_CAPABILITY_SHADOW_RISK_POLICY_ID,
        "provider_rule": "NO_PROP_FIRM_RULES_DEMO",
        "provider_headroom": "CURRENT_EQUITY",
        "max_risk_at_any_time": "CURRENT_EQUITY",
        "active_mll": "ZERO_SOLVENCY_FLOOR",
        "margin_headroom": "CURRENT_FREE_MARGIN",
        "open_risk": "SUM_RECONCILED_EXECUTED_INITIAL_STOP_RISK_CONSERVATIVE",
        "pending_risk": "EXPLICIT_RECONCILED_PENDING_BROKER_WORST_CASE",
        "execution_authority": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def build_demo_capability_risk_snapshot(
    *,
    account_binding_id: str,
    account_state: CTraderDemoAccountState,
    open_position_ids: tuple[int, ...],
    open_executed_risks: tuple[Phase20ExecutedRiskEvidence, ...],
    pending_broker_worst_case_loss_usd: Decimal,
    provider_hard_breach: bool = False,
) -> AccountRiskSnapshot:
    """Build a current DEMO Risk snapshot without fictitious provider limits."""

    if not account_binding_id:
        raise CiboCapitalManagementError(
            "DEMO shadow Risk account binding is required"
        )
    if not isinstance(account_state, CTraderDemoAccountState):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk account state must be canonical"
        )
    if (
        not isinstance(pending_broker_worst_case_loss_usd, Decimal)
        or not pending_broker_worst_case_loss_usd.is_finite()
        or pending_broker_worst_case_loss_usd < 0
    ):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk pending broker risk must be finite non-negative"
        )
    if type(provider_hard_breach) is not bool:
        raise CiboCapitalManagementError(
            "DEMO shadow Risk provider_hard_breach must be bool"
        )

    if len(open_position_ids) != len(set(open_position_ids)) or any(
        not isinstance(item, int)
        or isinstance(item, bool)
        or item <= 0
        for item in open_position_ids
    ):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk open position ids must be unique positive ints"
        )
    if any(
        not isinstance(item, Phase20ExecutedRiskEvidence)
        for item in open_executed_risks
    ):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk open risk evidence must be canonical"
        )
    evidence_ids = tuple(item.position_id for item in open_executed_risks)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk duplicate open-position risk evidence"
        )
    if set(evidence_ids) != set(open_position_ids):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk requires exact risk evidence for every open position"
        )
    if any(
        item.observed_at > account_state.observed_at
        for item in open_executed_risks
    ):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk evidence cannot postdate account snapshot"
        )

    equity = account_state.equity
    if equity < 0:
        raise CiboCapitalManagementError(
            "DEMO shadow Risk account equity cannot be negative"
        )
    open_stop_risk = sum(
        (
            item.executed_initial_stop_risk_usd
            for item in open_executed_risks
        ),
        Decimal(0),
    )
    floating_loss = max(
        Decimal(0),
        account_state.balance - account_state.equity,
    )
    budget = CiboDemoCapabilitySolvencyBudget(
        provider_headroom=equity,
        max_risk_at_any_time=equity,
        active_mll=Decimal(0),
        hard_breach=(provider_hard_breach or equity <= 0),
    )
    return AccountRiskSnapshot(
        account_binding_id=account_binding_id,
        equity=equity,
        margin_used=account_state.margin,
        free_margin=account_state.free_margin,
        open_stop_worst_case_loss=open_stop_risk,
        open_floating_loss=floating_loss,
        pending_broker_worst_case_loss=(
            pending_broker_worst_case_loss_usd
        ),
        qore_authorizable_headroom=equity,
        provider_budget=budget,
        reconciled_at=account_state.observed_at,
    )


def observe_demo_capability_constraints(
    *,
    risk: DurableAccountWideRiskEngine,
    snapshot: AccountRiskSnapshot,
    observed_at: datetime,
) -> RiskCapitalConstraintEnvelope:
    """Read the sovereign hard-constraint envelope without authorizing exposure."""

    if not isinstance(risk, DurableAccountWideRiskEngine):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk requires durable account-wide engine"
        )
    if not isinstance(snapshot, AccountRiskSnapshot):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk requires canonical account snapshot"
        )
    if (
        not isinstance(observed_at, datetime)
        or observed_at.tzinfo is None
        or observed_at.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            "DEMO shadow Risk observed_at must be timezone-aware"
        )
    if observed_at < snapshot.reconciled_at:
        raise CiboCapitalManagementError(
            "DEMO shadow Risk observation cannot predate snapshot"
        )
    return risk.capital_constraint_envelope(
        snapshot,
        now=observed_at,
    )
