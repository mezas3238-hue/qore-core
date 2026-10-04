"""Native account-wide portfolio allocation and adaptive leverage engine.

This is a real CIBO decision engine, not a frontier adapter.  It consumes the
canonical Full Economic Digital Twin and evaluates 0x..4x capital intensity
jointly across all currently known opportunities subject to observed capital,
risk, margin, context, provider and cognition constraints.

It proposes capital allocation only.  CMA and QORE Risk remain downstream
authorities.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import product

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
    observed_twin_constraints,
)


@dataclass(frozen=True, slots=True)
class CiboPortfolioAllocationLine:
    option_id: str
    multiplier: int
    expected_net_utility_usd: Decimal
    expected_capital_minutes: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal

    def __post_init__(self) -> None:
        if not self.option_id:
            raise CiboCapitalManagementError(
                "Portfolio allocation option identity required"
            )
        if self.multiplier not in {0, 1, 2, 3, 4}:
            raise CiboCapitalManagementError(
                "Portfolio allocation multiplier must be 0..4"
            )
        for name in (
            "expected_net_utility_usd",
            "expected_capital_minutes",
            "stop_risk_usd",
            "margin_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Portfolio allocation {name} must be finite Decimal"
                )
        if self.expected_capital_minutes <= 0:
            raise CiboCapitalManagementError(
                "Portfolio expected capital minutes must be positive"
            )
        if self.stop_risk_usd < 0 or self.margin_usd < 0:
            raise CiboCapitalManagementError(
                "Portfolio capacity use cannot be negative"
            )


@dataclass(frozen=True, slots=True)
class CiboPortfolioAllocationPlan:
    twin_id: str
    lines: tuple[CiboPortfolioAllocationLine, ...]
    total_expected_net_utility_usd: Decimal
    total_stop_risk_usd: Decimal
    total_margin_usd: Decimal
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id:
            raise CiboCapitalManagementError(
                "Portfolio allocation twin identity required"
            )
        ids = tuple(item.option_id for item in self.lines)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "Portfolio allocation options must be unique"
            )
        if (
            self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "Portfolio engine cannot acquire downstream authority"
            )


def plan_account_wide_capital_allocation(
    twin: CiboObservedEconomicTwin,
    *,
    fixed_multiplier: int | None = None,
) -> CiboPortfolioAllocationPlan:
    """Optimize the whole current opportunity set using only causal Twin state."""

    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "Portfolio engine requires canonical Full Economic Twin"
        )
    if fixed_multiplier is not None and fixed_multiplier not in {1, 2, 3, 4}:
        raise CiboCapitalManagementError(
            "Portfolio fixed multiplier must be 1..4"
        )

    constraints = observed_twin_constraints(twin)
    cognitive = dict(twin.cognitive_constraints)
    try:
        cognitive_cap = int(cognitive.get("capital_intensity_cap", "4"))
    except (TypeError, ValueError) as error:
        raise CiboCapitalManagementError(
            "Portfolio cognitive capital cap must be integer 0..4"
        ) from error
    if cognitive_cap not in {0, 1, 2, 3, 4}:
        raise CiboCapitalManagementError(
            "Portfolio cognitive capital cap outside 0..4"
        )

    ordered = tuple(
        sorted(
            twin.opportunities,
            key=lambda item: (item.earliest_action_at, item.option_id),
        )
    )
    ranges: list[range] = []
    net_values: list[Decimal] = []
    for item in ordered:
        eligible = (
            item.known_at <= twin.captured_at
            and item.earliest_action_at <= twin.captured_at
            and item.expires_at > twin.captured_at
            and item.context_allowed
            and item.provider_viable
            and item.capital_source_eligible
        )
        net = (
            item.expected_net_value_usd
            - item.provider_cost_usd
            - item.uncertainty_penalty
        )
        net_values.append(net)
        cap = (
            min(item.maximum_multiplier, cognitive_cap)
            if eligible and net > 0
            else 0
        )
        if fixed_multiplier is not None:
            cap = min(cap, fixed_multiplier)
        ranges.append(range(cap + 1))

    best_key: tuple[
        Decimal,
        Decimal,
        Decimal,
        Decimal,
        tuple[int, ...],
    ] | None = None
    best_combo: tuple[int, ...] = tuple(0 for _ in ordered)
    for combo in product(*ranges):
        risk = sum(
            (
                item.stop_risk_usd * mult
                for item, mult in zip(ordered, combo, strict=True)
            ),
            Decimal(0),
        )
        margin = sum(
            (
                item.margin_usd * mult
                for item, mult in zip(ordered, combo, strict=True)
            ),
            Decimal(0),
        )
        if (
            risk > constraints["stop_risk_headroom_usd"]
            or margin > constraints["margin_headroom_usd"]
        ):
            continue
        velocity_utility = sum(
            (
                net * mult / item.expected_capital_minutes
                for item, net, mult in zip(
                    ordered, net_values, combo, strict=True
                )
            ),
            Decimal(0),
        )
        expected_utility = sum(
            (
                net * mult
                for net, mult in zip(net_values, combo, strict=True)
            ),
            Decimal(0),
        )
        key = (
            velocity_utility,
            expected_utility,
            -risk,
            -margin,
            tuple(-value for value in combo),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_combo = combo

    lines = tuple(
        CiboPortfolioAllocationLine(
            option_id=item.option_id,
            multiplier=mult,
            expected_net_utility_usd=net * mult,
            expected_capital_minutes=item.expected_capital_minutes,
            stop_risk_usd=item.stop_risk_usd * mult,
            margin_usd=item.margin_usd * mult,
        )
        for item, net, mult in zip(
            ordered, net_values, best_combo, strict=True
        )
    )
    return CiboPortfolioAllocationPlan(
        twin_id=twin.twin_id,
        lines=lines,
        total_expected_net_utility_usd=sum(
            (item.expected_net_utility_usd for item in lines),
            Decimal(0),
        ),
        total_stop_risk_usd=sum(
            (item.stop_risk_usd for item in lines),
            Decimal(0),
        ),
        total_margin_usd=sum(
            (item.margin_usd for item in lines),
            Decimal(0),
        ),
    )
