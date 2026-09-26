"""CE2I T11 execution-efficient capitalization.

Research-only deterministic cost curve. It caps expansion when the next unit of
exposure has non-positive expected net contribution after spread, commission,
slippage and nonlinear market-impact reserve.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)


@dataclass(frozen=True, slots=True)
class ExecutionCostCurveInput:
    evidence_id: str
    volume_step: Decimal
    maximum_volume: Decimal
    gross_edge_per_volume_usd: Decimal
    spread_cost_per_volume_usd: Decimal
    commission_cost_per_volume_usd: Decimal
    slippage_cost_per_volume_usd: Decimal
    impact_cost_per_volume_squared_usd: Decimal

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise CiboCapitalManagementError("execution evidence_id required")
        for name in ("volume_step", "maximum_volume", "gross_edge_per_volume_usd"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise CiboCapitalManagementError(
                    f"{name} must be finite positive Decimal"
                )
        for name in (
            "spread_cost_per_volume_usd",
            "commission_cost_per_volume_usd",
            "slippage_cost_per_volume_usd",
            "impact_cost_per_volume_squared_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )
        if self.maximum_volume < self.volume_step:
            raise CiboCapitalManagementError(
                "maximum_volume cannot be below volume_step"
            )


@dataclass(frozen=True, slots=True)
class ExecutionEfficientCap:
    evidence_id: str
    volume_cap: Decimal
    gross_expectancy_usd: Decimal
    execution_cost_usd: Decimal
    net_expectancy_usd: Decimal
    marginal_next_step_net_usd: Decimal | None
    reason: str


def execution_efficient_volume_cap(
    curve: ExecutionCostCurveInput,
) -> ExecutionEfficientCap:
    """Return the largest step-aligned volume with positive marginal net edge."""

    if not isinstance(curve, ExecutionCostCurveInput):
        raise CiboCapitalManagementError(
            "curve must be ExecutionCostCurveInput"
        )

    linear_cost = (
        curve.spread_cost_per_volume_usd
        + curve.commission_cost_per_volume_usd
        + curve.slippage_cost_per_volume_usd
    )
    base_net_per_volume = curve.gross_edge_per_volume_usd - linear_cost
    max_steps = int(
        (curve.maximum_volume / curve.volume_step).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )

    if base_net_per_volume <= 0:
        next_net = _marginal_step_net(curve, Decimal(0))
        return ExecutionEfficientCap(
            evidence_id=curve.evidence_id,
            volume_cap=Decimal(0),
            gross_expectancy_usd=Decimal(0),
            execution_cost_usd=Decimal(0),
            net_expectancy_usd=Decimal(0),
            marginal_next_step_net_usd=next_net,
            reason="linear execution cost already consumes gross edge",
        )

    if curve.impact_cost_per_volume_squared_usd == 0:
        steps = max_steps
    else:
        ratio = (
            base_net_per_volume
            / (
                curve.impact_cost_per_volume_squared_usd
                * curve.volume_step
            )
        )
        approximate = int(
            ((ratio + Decimal(1)) / Decimal(2)).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        steps = min(max_steps, max(0, approximate + 1))
        while (
            steps > 0
            and _marginal_step_net(
                curve,
                curve.volume_step * Decimal(steps - 1),
            )
            <= 0
        ):
            steps -= 1
        while (
            steps < max_steps
            and _marginal_step_net(
                curve,
                curve.volume_step * Decimal(steps),
            )
            > 0
        ):
            steps += 1

    volume = curve.volume_step * Decimal(steps)
    gross = curve.gross_edge_per_volume_usd * volume
    execution_cost = (
        linear_cost * volume
        + curve.impact_cost_per_volume_squared_usd * volume * volume
    )
    net = gross - execution_cost
    next_marginal = (
        _marginal_step_net(curve, volume)
        if steps < max_steps
        else None
    )
    return ExecutionEfficientCap(
        evidence_id=curve.evidence_id,
        volume_cap=volume,
        gross_expectancy_usd=gross,
        execution_cost_usd=execution_cost,
        net_expectancy_usd=net,
        marginal_next_step_net_usd=next_marginal,
        reason=(
            "capped where next exposure step loses marginal net edge"
            if steps < max_steps
            else "maximum tested volume retains positive marginal net edge"
        ),
    )


def cap_expansion_plan_by_execution(
    *,
    plan: CiboCapitalActionPlan,
    opportunity: TraderOpportunityEnvelope,
    cap: ExecutionEfficientCap,
) -> CiboCapitalActionPlan:
    """Reduce an expansion plan to the execution-efficient volume cap."""

    if not isinstance(plan, CiboCapitalActionPlan):
        raise CiboCapitalManagementError("plan must be CiboCapitalActionPlan")
    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "opportunity must be TraderOpportunityEnvelope"
        )
    if not isinstance(cap, ExecutionEfficientCap):
        raise CiboCapitalManagementError("cap must be ExecutionEfficientCap")
    if plan.action is not CapitalAction.EXPAND:
        raise CiboCapitalManagementError(
            "execution-efficient cap only applies to EXPAND plans"
        )
    if (
        plan.trader_id is not opportunity.trader_id
        or plan.qore_symbol != opportunity.qore_symbol
    ):
        raise CiboCapitalManagementError(
            "plan/opportunity identity mismatch"
        )

    volume = min(plan.volume, cap.volume_cap)
    steps = (volume / opportunity.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    volume = steps * opportunity.volume_step
    if volume < opportunity.minimum_volume:
        return CiboCapitalActionPlan(
            trader_id=plan.trader_id,
            qore_symbol=plan.qore_symbol,
            stage=CapitalStage.BASE_RECOVERED,
            action=CapitalAction.HOLD,
            volume=Decimal(0),
            stop_risk_usd=Decimal(0),
            margin_usd=Decimal(0),
            capital_source=None,
            capital_source_amount_usd=Decimal(0),
            reason="execution economics reject executable expansion minimum",
        )

    risk = volume * opportunity.stop_loss_per_volume
    margin = volume * opportunity.margin_per_volume
    return CiboCapitalActionPlan(
        trader_id=plan.trader_id,
        qore_symbol=plan.qore_symbol,
        stage=plan.stage,
        action=CapitalAction.EXPAND,
        volume=volume,
        stop_risk_usd=risk,
        margin_usd=margin,
        capital_source=plan.capital_source,
        capital_source_amount_usd=risk,
        reason=(
            "expansion capped by positive marginal execution economics"
            if volume < plan.volume
            else plan.reason
        ),
    )


def _marginal_step_net(
    curve: ExecutionCostCurveInput,
    current_volume: Decimal,
) -> Decimal:
    next_volume = current_volume + curve.volume_step
    gross_delta = curve.gross_edge_per_volume_usd * curve.volume_step
    linear_delta = (
        curve.spread_cost_per_volume_usd
        + curve.commission_cost_per_volume_usd
        + curve.slippage_cost_per_volume_usd
    ) * curve.volume_step
    impact_delta = curve.impact_cost_per_volume_squared_usd * (
        next_volume * next_volume - current_volume * current_volume
    )
    return gross_delta - linear_delta - impact_delta
