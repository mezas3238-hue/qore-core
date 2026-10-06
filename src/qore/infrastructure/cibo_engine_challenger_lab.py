"""CIBO native-engine challenger laboratory.

Research-only comparison of the current adapter/baseline allocation path against
the native account-wide portfolio/leverage engine.  Both paths consume the same
causal Full Economic Twin snapshot.  No realized future outcome is used for
promotion.  A native engine is eligible to replace a baseline only when it is
strictly better on causal utility/velocity or equal while using no more risk or
margin, and never violates observed constraints.

This laboratory does not change CMA, QORE Risk, Execution, LIVE or broker
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
    observed_twin_constraints,
)
from qore.infrastructure.cibo_maximum_capability_frontier import (
    EpochOption,
    optimize_epoch_multipliers,
)
from qore.infrastructure.cibo_portfolio_allocation_engine import (
    CiboPortfolioAllocationPlan,
    plan_account_wide_capital_allocation,
)


@dataclass(frozen=True, slots=True)
class CiboAllocationPathScore:
    path_id: str
    total_expected_net_utility_usd: Decimal
    velocity_utility: Decimal
    total_stop_risk_usd: Decimal
    total_margin_usd: Decimal
    selected_multiplier_count: int

    def __post_init__(self) -> None:
        if not self.path_id:
            raise CiboCapitalManagementError(
                "Challenger score path identity required"
            )
        for name in (
            "total_expected_net_utility_usd",
            "velocity_utility",
            "total_stop_risk_usd",
            "total_margin_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Challenger score {name} must be finite Decimal"
                )
        if self.total_stop_risk_usd < 0 or self.total_margin_usd < 0:
            raise CiboCapitalManagementError(
                "Challenger capacity use cannot be negative"
            )
        if (
            not isinstance(self.selected_multiplier_count, int)
            or isinstance(self.selected_multiplier_count, bool)
            or self.selected_multiplier_count < 0
        ):
            raise CiboCapitalManagementError(
                "Challenger selected multiplier count invalid"
            )


@dataclass(frozen=True, slots=True)
class CiboAllocationChallengerResult:
    twin_id: str
    baseline: CiboAllocationPathScore
    native: CiboAllocationPathScore
    native_plan: CiboPortfolioAllocationPlan
    native_strictly_better: bool
    native_equivalent_lower_capacity: bool
    promotion_eligible: bool
    reason: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id or not self.reason:
            raise CiboCapitalManagementError(
                "Challenger result identity/reason required"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Challenger laboratory cannot acquire productive authority"
            )
        if self.promotion_eligible != (
            self.native_strictly_better
            or self.native_equivalent_lower_capacity
        ):
            raise CiboCapitalManagementError(
                "Challenger promotion predicate drift"
            )


def _eligible_net(item, captured_at) -> tuple[int, Decimal]:
    eligible = (
        item.known_at <= captured_at
        and item.earliest_action_at <= captured_at
        and item.expires_at > captured_at
        and item.context_allowed
        and item.provider_viable
        and item.capital_source_eligible
    )
    net = (
        item.expected_net_value_usd
        - item.provider_cost_usd
        - item.uncertainty_penalty
    )
    return (item.maximum_multiplier if eligible and net > 0 else 0, net)


def _baseline_score(
    twin: CiboObservedEconomicTwin,
) -> CiboAllocationPathScore:
    constraints = observed_twin_constraints(twin)
    cognitive = dict(twin.cognitive_constraints)
    dynamic_default_cap = max(
        (item.maximum_multiplier for item in twin.opportunities),
        default=0,
    )
    try:
        cognitive_cap = int(
            cognitive.get("capital_intensity_cap", str(dynamic_default_cap))
        )
    except (TypeError, ValueError) as error:
        raise CiboCapitalManagementError(
            "Challenger cognitive capital cap must be a non-negative integer"
        ) from error
    if cognitive_cap < 0:
        raise CiboCapitalManagementError(
            "Challenger cognitive capital cap cannot be negative"
        )

    ordered = tuple(
        sorted(
            twin.opportunities,
            key=lambda item: (item.earliest_action_at, item.option_id),
        )
    )
    options = []
    nets = []
    for item in ordered:
        cap, net = _eligible_net(item, twin.captured_at)
        cap = min(cap, cognitive_cap)
        nets.append(net)
        options.append(
            EpochOption(
                signal_fingerprint=item.option_id,
                multiplier_cap=cap,
                expected_net_value_usd=net,
                expected_capital_minutes=item.expected_capital_minutes,
                risk_per_multiplier_usd=item.stop_risk_usd,
                margin_per_multiplier_usd=item.margin_usd,
            )
        )
    multipliers = optimize_epoch_multipliers(
        tuple(options),
        risk_headroom_usd=constraints["stop_risk_headroom_usd"],
        margin_headroom_usd=constraints["margin_headroom_usd"],
        portfolio_competition=True,
    )
    total_utility = sum(
        (
            net * mult
            for net, mult in zip(nets, multipliers, strict=True)
        ),
        Decimal(0),
    )
    velocity = sum(
        (
            net * mult / item.expected_capital_minutes
            for item, net, mult in zip(
                ordered, nets, multipliers, strict=True
            )
        ),
        Decimal(0),
    )
    return CiboAllocationPathScore(
        path_id="ADAPTER_BASELINE",
        total_expected_net_utility_usd=total_utility,
        velocity_utility=velocity,
        total_stop_risk_usd=sum(
            (
                item.stop_risk_usd * mult
                for item, mult in zip(
                    ordered, multipliers, strict=True
                )
            ),
            Decimal(0),
        ),
        total_margin_usd=sum(
            (
                item.margin_usd * mult
                for item, mult in zip(
                    ordered, multipliers, strict=True
                )
            ),
            Decimal(0),
        ),
        selected_multiplier_count=sum(multipliers),
    )


def _native_score(
    twin: CiboObservedEconomicTwin,
    plan: CiboPortfolioAllocationPlan,
) -> CiboAllocationPathScore:
    by_id = {item.option_id: item for item in twin.opportunities}
    velocity = sum(
        (
            line.expected_net_utility_usd
            / by_id[line.option_id].expected_capital_minutes
            for line in plan.lines
            if line.multiplier > 0
        ),
        Decimal(0),
    )
    return CiboAllocationPathScore(
        path_id="NATIVE_ACCOUNT_WIDE_ENGINE",
        total_expected_net_utility_usd=(
            plan.total_expected_net_utility_usd
        ),
        velocity_utility=velocity,
        total_stop_risk_usd=plan.total_stop_risk_usd,
        total_margin_usd=plan.total_margin_usd,
        selected_multiplier_count=sum(
            line.multiplier for line in plan.lines
        ),
    )


def compare_allocation_paths(
    twin: CiboObservedEconomicTwin,
) -> CiboAllocationChallengerResult:
    """Compare baseline vs native engine using only ex-ante causal evidence."""

    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "Challenger laboratory requires canonical Full Economic Twin"
        )
    baseline = _baseline_score(twin)
    native_plan = plan_account_wide_capital_allocation(twin)
    native = _native_score(twin, native_plan)

    strictly_better = (
        native.total_expected_net_utility_usd
        > baseline.total_expected_net_utility_usd
        and native.velocity_utility >= baseline.velocity_utility
        and native.total_stop_risk_usd <= baseline.total_stop_risk_usd
        and native.total_margin_usd <= baseline.total_margin_usd
    ) or (
        native.velocity_utility > baseline.velocity_utility
        and native.total_expected_net_utility_usd
        >= baseline.total_expected_net_utility_usd
        and native.total_stop_risk_usd <= baseline.total_stop_risk_usd
        and native.total_margin_usd <= baseline.total_margin_usd
    )
    equivalent_lower_capacity = (
        native.total_expected_net_utility_usd
        == baseline.total_expected_net_utility_usd
        and native.velocity_utility == baseline.velocity_utility
        and (
            native.total_stop_risk_usd
            < baseline.total_stop_risk_usd
            or native.total_margin_usd
            < baseline.total_margin_usd
        )
        and native.total_stop_risk_usd <= baseline.total_stop_risk_usd
        and native.total_margin_usd <= baseline.total_margin_usd
    )
    promotion = strictly_better or equivalent_lower_capacity
    if strictly_better:
        reason = "native engine improves causal utility/velocity without extra capacity"
    elif equivalent_lower_capacity:
        reason = "native engine preserves utility while consuming less capacity"
    else:
        reason = "baseline retained; native engine has not proven strict causal superiority"

    return CiboAllocationChallengerResult(
        twin_id=twin.twin_id,
        baseline=baseline,
        native=native,
        native_plan=native_plan,
        native_strictly_better=strictly_better,
        native_equivalent_lower_capacity=equivalent_lower_capacity,
        promotion_eligible=promotion,
        reason=reason,
    )
