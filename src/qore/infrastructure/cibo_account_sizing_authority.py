"""Account-scoped CIBO sizing authority.

Traders own entry/exit geometry only. CIBO owns every runtime sizing decision.
The account mission selects how aggressively CIBO may deploy capital:

- DEMO_CAPABILITY_DISCOVERY: use the maximum executable size inside current
  account/provider constraints so capability can be measured.
- FUNDED_SURVIVAL_COMPOUND: use minimal seed until the account's survival
  capital is demonstrably protected; after protection, use the full remaining
  constrained capacity.
- PRODUCTION_SURVIVAL_COMPOUND follows the funded survival law.

QORE Risk remains an independent hard governor and may still ALLOW/REDUCE/REJECT
the CIBO request. This module has no broker mutation authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMission,
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    CapitalSourceLot,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
    plan_minimal_seed,
)


class CiboAccountSizingMode(StrEnum):
    SURVIVAL_MINIMAL_SEED = "SURVIVAL_MINIMAL_SEED"
    CAPABILITY_MAXIMUM = "CAPABILITY_MAXIMUM"
    PROTECTED_FULL_CAPACITY = "PROTECTED_FULL_CAPACITY"


@dataclass(frozen=True, slots=True)
class CiboAccountSizingDecision:
    mission: CiboCapitalMission
    mode: CiboAccountSizingMode
    base_protected: bool
    survival_capital_usd: Decimal
    protected_capital_usd: Decimal
    plan: CiboCapitalActionPlan

    def __post_init__(self) -> None:
        if type(self.mission) is not CiboCapitalMission:
            raise CiboCapitalManagementError("sizing mission must be canonical")
        if type(self.mode) is not CiboAccountSizingMode:
            raise CiboCapitalManagementError("sizing mode must be canonical")
        if type(self.base_protected) is not bool:
            raise CiboCapitalManagementError("base_protected must be bool")
        for name in ("survival_capital_usd", "protected_capital_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        if not isinstance(self.plan, CiboCapitalActionPlan):
            raise CiboCapitalManagementError("sizing plan must be canonical")
        if self.base_protected != (
            self.protected_capital_usd >= self.survival_capital_usd
        ):
            raise CiboCapitalManagementError(
                "base protection flag/economic evidence mismatch"
            )


def account_capital_state(
    *,
    assigned_capital_usd: Decimal,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
) -> CiboCapitalState:
    """Build one account-scoped capital state from observed economic facts."""

    for name, value in (
        ("assigned_capital_usd", assigned_capital_usd),
        ("hard_risk_headroom_usd", hard_risk_headroom_usd),
        ("margin_headroom_usd", margin_headroom_usd),
        ("survival_capital_usd", survival_capital_usd),
        ("protected_capital_usd", protected_capital_usd),
    ):
        if (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
        ):
            raise CiboCapitalManagementError(
                f"{name} must be finite non-negative Decimal"
            )
    if assigned_capital_usd <= 0:
        raise CiboCapitalManagementError(
            "assigned account capital must be positive"
        )
    base_at_risk = max(
        Decimal(0),
        survival_capital_usd - protected_capital_usd,
    )
    return CiboCapitalState(
        assigned_capital_usd=assigned_capital_usd,
        hard_risk_headroom_usd=hard_risk_headroom_usd,
        margin_headroom_usd=margin_headroom_usd,
        base_capital_at_risk_usd=base_at_risk,
        realized_net_profit_usd=protected_capital_usd,
        protected_open_economic_floor_usd=Decimal(0),
        proven_self_financing_capacity_usd=protected_capital_usd,
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )


def plan_account_sizing(
    *,
    opportunity: TraderOpportunityEnvelope,
    capital: CiboCapitalState,
    mission_policy: CiboCapitalMissionPolicy,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
    provider_cost_per_volume_usd: Decimal = Decimal(0),
) -> CiboAccountSizingDecision:
    """Choose size solely from account mission/capital facts and Trader geometry."""

    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "account sizing requires Trader opportunity envelope"
        )
    if not isinstance(capital, CiboCapitalState):
        raise CiboCapitalManagementError(
            "account sizing requires canonical capital state"
        )
    if not isinstance(mission_policy, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "account sizing requires canonical mission policy"
        )
    for name, value in (
        ("survival_capital_usd", survival_capital_usd),
        ("protected_capital_usd", protected_capital_usd),
        ("provider_cost_per_volume_usd", provider_cost_per_volume_usd),
    ):
        if (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
        ):
            raise CiboCapitalManagementError(
                f"{name} must be finite non-negative Decimal"
            )

    base_protected = protected_capital_usd >= survival_capital_usd

    if mission_policy.mission is CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY:
        plan = _maximum_capability_plan(
            opportunity=opportunity,
            capital=capital,
            provider_cost_per_volume_usd=provider_cost_per_volume_usd,
            reason=(
                "DEMO capability discovery: CIBO selected maximum executable "
                "account-constrained size with explicit base/profit provenance"
            ),
        )
        return CiboAccountSizingDecision(
            mission=mission_policy.mission,
            mode=CiboAccountSizingMode.CAPABILITY_MAXIMUM,
            base_protected=base_protected,
            survival_capital_usd=survival_capital_usd,
            protected_capital_usd=protected_capital_usd,
            plan=plan,
        )

    if mission_policy.mission in {
        CiboCapitalMission.FUNDED_SURVIVAL_COMPOUND,
        CiboCapitalMission.PRODUCTION_SURVIVAL_COMPOUND,
    }:
        if not base_protected:
            plan = plan_minimal_seed(opportunity, capital)
            mode = CiboAccountSizingMode.SURVIVAL_MINIMAL_SEED
        else:
            plan = _maximum_constrained_plan(
                opportunity=opportunity,
                capital=capital,
                provider_cost_per_volume_usd=provider_cost_per_volume_usd,
                action=CapitalAction.EXPAND,
                source=CapitalSource.REALIZED_PROFIT,
                reason=(
                    "realized closed profit covers survival capital: CIBO may "
                    "use full remaining account-constrained capacity"
                ),
            )
            mode = CiboAccountSizingMode.PROTECTED_FULL_CAPACITY
        return CiboAccountSizingDecision(
            mission=mission_policy.mission,
            mode=mode,
            base_protected=base_protected,
            survival_capital_usd=survival_capital_usd,
            protected_capital_usd=protected_capital_usd,
            plan=plan,
        )

    # TEST/SANDBOX remain conservative unless explicitly exercising DEMO.
    plan = plan_minimal_seed(opportunity, capital)
    return CiboAccountSizingDecision(
        mission=mission_policy.mission,
        mode=CiboAccountSizingMode.SURVIVAL_MINIMAL_SEED,
        base_protected=base_protected,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
        plan=plan,
    )


def _maximum_capability_plan(
    *,
    opportunity: TraderOpportunityEnvelope,
    capital: CiboCapitalState,
    provider_cost_per_volume_usd: Decimal,
    reason: str,
) -> CiboCapitalActionPlan:
    """Size capability discovery without mislabeling compounded profit as base.

    The volume law is identical to the ordinary maximum-constrained plan.
    This helper changes only capital-source provenance: original base funds at
    most the non-profit portion of assigned capital and any remaining risk is
    explicitly funded by proven REALIZED_PROFIT capacity.
    """

    provisional = _maximum_constrained_plan(
        opportunity=opportunity,
        capital=capital,
        provider_cost_per_volume_usd=provider_cost_per_volume_usd,
        action=CapitalAction.OPEN_CAPABILITY_MAX,
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        reason=reason,
    )
    risk = provisional.stop_risk_usd
    realized_profit_capacity = min(
        capital.realized_net_profit_usd,
        capital.proven_self_financing_capacity_usd,
    )
    original_base_capacity = max(
        Decimal(0),
        capital.assigned_capital_usd - capital.realized_net_profit_usd,
    )
    base_amount = min(risk, original_base_capacity)
    profit_amount = risk - base_amount
    if profit_amount > realized_profit_capacity:
        raise CiboCapitalManagementError(
            "capability sizing risk exceeds proven base/profit source capacity"
        )

    lots: list[CapitalSourceLot] = []
    if base_amount > 0:
        lots.append(
            CapitalSourceLot(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                amount_usd=base_amount,
                source_id="cibo:assigned-original-base",
            )
        )
    if profit_amount > 0:
        lots.append(
            CapitalSourceLot(
                source=CapitalSource.REALIZED_PROFIT,
                amount_usd=profit_amount,
                source_id="cibo:realized-profit-pool",
            )
        )
    if not lots:
        raise CiboCapitalManagementError(
            "capability sizing produced no capital-source provenance"
        )

    return CiboCapitalActionPlan(
        trader_id=provisional.trader_id,
        qore_symbol=provisional.qore_symbol,
        stage=provisional.stage,
        action=provisional.action,
        volume=provisional.volume,
        stop_risk_usd=provisional.stop_risk_usd,
        margin_usd=provisional.margin_usd,
        capital_source=(
            lots[0].source
            if len(lots) == 1
            else None
        ),
        capital_source_amount_usd=risk,
        reason=provisional.reason,
        capital_source_lots=tuple(lots),
    )


def _maximum_constrained_plan(
    *,
    opportunity: TraderOpportunityEnvelope,
    capital: CiboCapitalState,
    provider_cost_per_volume_usd: Decimal,
    action: CapitalAction,
    source: CapitalSource,
    reason: str,
) -> CiboCapitalActionPlan:
    if capital.hard_risk_headroom_usd <= 0 or capital.margin_headroom_usd <= 0:
        raise CiboCapitalManagementError(
            "CIBO account has no deployable risk/margin headroom"
        )
    if (
        not isinstance(provider_cost_per_volume_usd, Decimal)
        or not provider_cost_per_volume_usd.is_finite()
        or provider_cost_per_volume_usd < 0
    ):
        raise CiboCapitalManagementError(
            "provider cost per volume must be finite non-negative Decimal"
        )
    total_loss_per_volume = (
        opportunity.stop_loss_per_volume + provider_cost_per_volume_usd
    )
    by_risk = capital.hard_risk_headroom_usd / total_loss_per_volume
    by_margin = (
        capital.margin_headroom_usd / opportunity.margin_per_volume
    )
    raw = min(by_risk, by_margin, opportunity.maximum_volume)
    steps = (raw / opportunity.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    volume = steps * opportunity.volume_step
    minimum = minimum_seed_volume(opportunity)
    if volume < minimum:
        raise CiboCapitalManagementError(
            "maximum account-constrained capacity cannot express minimum seed"
        )
    risk = volume * opportunity.stop_loss_per_volume
    margin = volume * opportunity.margin_per_volume
    return CiboCapitalActionPlan(
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        stage=(
            capital_stage_for_action(action)
        ),
        action=action,
        volume=volume,
        stop_risk_usd=risk,
        margin_usd=margin,
        capital_source=source,
        capital_source_amount_usd=risk,
        reason=reason,
    )


def capital_stage_for_action(action: CapitalAction) -> CapitalStage:
    if action is CapitalAction.OPEN_CAPABILITY_MAX:
        return CapitalStage.CAPITALIZE
    if action is CapitalAction.EXPAND:
        return CapitalStage.CAPITALIZE
    return CapitalStage.MINIMAL_SEED
