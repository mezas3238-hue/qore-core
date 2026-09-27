"""cTrader DEMO account-scoped CIBO sizing.

DEMO_CAPABILITY_DISCOVERY intentionally measures how much each valid Trader
opportunity can express when CIBO is allowed to maximize inside the observed
account/provider constraints. There is no per-Trader capital slice and no
Trader-owned risk fraction.

The returned request is still a CiboRiskRequest so the same execution boundary
and capital-provenance contracts are used across DEMO and production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import CiboRiskRequest
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
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
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


@dataclass(frozen=True, slots=True)
class CTraderDemoCiboSizing:
    plan: CiboCapitalActionPlan
    request: CiboRiskRequest
    mode: CiboAccountSizingMode
    account_capital_usd: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.plan, CiboCapitalActionPlan):
            raise CiboCapitalManagementError(
                "DEMO CIBO sizing plan must be canonical"
            )
        if not isinstance(self.request, CiboRiskRequest):
            raise CiboCapitalManagementError(
                "DEMO CIBO sizing request must be canonical"
            )
        if self.mode is not CiboAccountSizingMode.CAPABILITY_MAXIMUM:
            raise CiboCapitalManagementError(
                "DEMO CIBO sizing must use CAPABILITY_MAXIMUM"
            )
        if (
            not isinstance(self.account_capital_usd, Decimal)
            or not self.account_capital_usd.is_finite()
            or self.account_capital_usd <= 0
        ):
            raise CiboCapitalManagementError(
                "DEMO account capital must be finite positive Decimal"
            )


def build_ctrader_demo_cibo_sizing(
    *,
    request_id: str,
    opportunity: TraderOpportunityEnvelope,
    account_ref: str,
    account_state: CTraderDemoAccountState,
    requested_at: datetime,
    expires_at: datetime,
) -> CTraderDemoCiboSizing:
    """Use the full observed DEMO account envelope, never a Trader slice."""

    if not isinstance(account_state, CTraderDemoAccountState):
        raise CiboCapitalManagementError(
            "DEMO CIBO sizing requires canonical account state"
        )
    if not account_ref:
        raise CiboCapitalManagementError(
            "DEMO CIBO sizing account_ref is required"
        )
    mission = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-demo",
            account_ref=account_ref,
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )
    # DEMO capability discovery deliberately uses the whole observed account
    # equity as loss-capacity ceiling and free margin as the broker-capacity
    # ceiling. Cross-Trader attribution must not partition this envelope.
    capital = account_capital_state(
        assigned_capital_usd=account_state.equity,
        hard_risk_headroom_usd=account_state.equity,
        margin_headroom_usd=account_state.free_margin,
        survival_capital_usd=Decimal(0),
        protected_capital_usd=Decimal(0),
    )
    sizing = plan_account_sizing(
        opportunity=opportunity,
        capital=capital,
        mission_policy=mission,
        survival_capital_usd=Decimal(0),
        protected_capital_usd=Decimal(0),
    )
    request = build_cma_risk_request(
        request_id=request_id,
        opportunity=opportunity,
        plan=sizing.plan,
        requested_at=requested_at,
        expires_at=expires_at,
        capital_source_id=f"ctrader-demo:{account_ref}:capability-max",
    )
    return CTraderDemoCiboSizing(
        plan=sizing.plan,
        request=request,
        mode=sizing.mode,
        account_capital_usd=account_state.equity,
    )
