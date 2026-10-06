"""FundedNext CIBO account-scoped sizing bridge.

Risk exposes hard account constraints. CIBO owns every runtime sizing decision.
Before the account survival capital is protected, CIBO opens only the minimum
executable seed. Once closed/protected capital covers the survival capital,
CIBO may use the full remaining Risk/provider-constrained capacity.

No Trader sizing input is accepted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    CiboRiskRequest,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
)
from qore.infrastructure.cibo_account_capital_mission import (
    derive_cibo_capital_mission,
    fundednext_stellar_instant_identity,
)
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingMode,
    account_capital_state,
    plan_account_sizing,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request


@dataclass(frozen=True, slots=True)
class FundedNextCiboSizing:
    plan: CiboCapitalActionPlan
    request: CiboRiskRequest
    mode: CiboAccountSizingMode
    base_protected: bool
    survival_capital_usd: Decimal
    protected_capital_usd: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.plan, CiboCapitalActionPlan):
            raise CiboCapitalManagementError(
                "FundedNext CIBO sizing plan must be canonical"
            )
        if not isinstance(self.request, CiboRiskRequest):
            raise CiboCapitalManagementError(
                "FundedNext CIBO sizing request must be canonical"
            )
        if type(self.mode) is not CiboAccountSizingMode:
            raise CiboCapitalManagementError(
                "FundedNext CIBO sizing mode must be canonical"
            )
        if type(self.base_protected) is not bool:
            raise CiboCapitalManagementError(
                "FundedNext CIBO base_protected must be bool"
            )


def build_fundednext_cibo_seed(
    *,
    request_id: str,
    opportunity: TraderOpportunityEnvelope,
    risk: DurableAccountWideRiskEngine,
    snapshot: AccountRiskSnapshot,
    assigned_capital_usd: Decimal,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
    requested_at: datetime,
    expires_at: datetime,
) -> FundedNextCiboSizing:
    """Build the account-scoped CIBO size strictly inside sovereign Risk constraints."""

    if risk.recovery_required:
        risk.complete_boot_reconciliation(snapshot, now=requested_at)
    constraints = risk.capital_constraint_envelope(
        snapshot,
        now=requested_at,
    )
    if constraints.survival_blocked:
        raise CiboCapitalManagementError(
            f"Risk survival envelope blocks new sizing: {constraints.reason}"
        )
    mission = derive_cibo_capital_mission(
        fundednext_stellar_instant_identity(
            account_ref=snapshot.account_binding_id,
        )
    )
    capital = account_capital_state(
        assigned_capital_usd=assigned_capital_usd,
        hard_risk_headroom_usd=constraints.hard_risk_headroom_usd,
        margin_headroom_usd=constraints.margin_headroom_usd,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
    )
    sizing = plan_account_sizing(
        opportunity=opportunity,
        capital=capital,
        mission_policy=mission,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
    )
    request = build_cma_risk_request(
        request_id=request_id,
        opportunity=opportunity,
        plan=sizing.plan,
        requested_at=requested_at,
        expires_at=expires_at,
        capital_source_id=(
            f"fundednext:{snapshot.account_binding_id}:"
            f"{sizing.mode.value.lower()}"
        ),
    )
    return FundedNextCiboSizing(
        plan=sizing.plan,
        request=request,
        mode=sizing.mode,
        base_protected=sizing.base_protected,
        survival_capital_usd=sizing.survival_capital_usd,
        protected_capital_usd=sizing.protected_capital_usd,
    )
