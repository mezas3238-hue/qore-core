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
from decimal import Decimal, localcontext
from itertools import product

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
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
    capital_base = twin.capital_twin.total_realized_capital_usd
    if (
        not isinstance(capital_base, Decimal)
        or not capital_base.is_finite()
        or capital_base <= 0
    ):
        raise CiboCapitalManagementError(
            "Portfolio requires positive realized capital for robust risk pricing"
        )
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
        # Robust utility prices concentration non-linearly.  Expected edge,
        # provider cost and forecast uncertainty scale with exposure, while the
        # survival cost of concentrating stop-risk grows quadratically relative
        # to current realized capital.  This removes the old structural bias
        # where every positive utility was monotonically pushed to the maximum
        # multiplier until a hard capacity wall.
        with localcontext() as context:
            context.prec = 100
            robust_lines = tuple(
                (
                    net * mult
                    - (
                        (item.stop_risk_usd * mult)
                        * (item.stop_risk_usd * mult)
                        / capital_base
                    )
                )
                for item, net, mult in zip(
                    ordered, net_values, combo, strict=True
                )
            )
            trusted_velocity_utility = sum(
                (
                    robust
                    / item.expected_capital_minutes
                    for item, robust in zip(
                        ordered, robust_lines, strict=True
                    )
                    if item.expectation_basis
                    in {
                        CausalExpectationBasis.CAUSAL_MODEL_FORECAST,
                        CausalExpectationBasis.CURRENT_STATE_FORECAST,
                        CausalExpectationBasis.WALK_FORWARD_EMPIRICAL_FORECAST,
                    }
                ),
                Decimal(0),
            )
            expected_utility = sum(robust_lines, Decimal(0))
        key = (
            trusted_velocity_utility,
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



@dataclass(frozen=True, slots=True)
class CiboPositionOpportunityCompetitionLine:
    position_id: str
    continuation_utility_per_minute: Decimal
    releasable_stop_risk_usd: Decimal
    releasable_margin_usd: Decimal
    release_cost_usd: Decimal
    proposed_action: str

    def __post_init__(self) -> None:
        if not self.position_id:
            raise CiboCapitalManagementError(
                "position competition identity required"
            )
        if self.proposed_action not in {"KEEP", "RELEASE"}:
            raise CiboCapitalManagementError(
                "position competition action must be KEEP/RELEASE"
            )
        for name in (
            "continuation_utility_per_minute",
            "releasable_stop_risk_usd",
            "releasable_margin_usd",
            "release_cost_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"position competition {name} must be finite Decimal"
                )
        if (
            self.releasable_stop_risk_usd < 0
            or self.releasable_margin_usd < 0
            or self.release_cost_usd < 0
        ):
            raise CiboCapitalManagementError(
                "position competition capacity/cost cannot be negative"
            )


@dataclass(frozen=True, slots=True)
class CiboPositionOpportunityCompetitionPlan:
    twin_id: str
    opportunity_id: str
    fits_without_release: bool
    position_lines: tuple[CiboPositionOpportunityCompetitionLine, ...]
    released_stop_risk_usd: Decimal
    released_margin_usd: Decimal
    opportunity_net_utility_usd: Decimal
    displaced_continuation_value_usd: Decimal
    release_cost_usd: Decimal
    net_incremental_utility_usd: Decimal
    admit_opportunity: bool
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id or not self.opportunity_id:
            raise CiboCapitalManagementError(
                "position competition plan identity required"
            )
        if (
            self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "position competition cannot acquire downstream authority"
            )
        if self.net_incremental_utility_usd != (
            self.opportunity_net_utility_usd
            - self.displaced_continuation_value_usd
            - self.release_cost_usd
        ):
            raise CiboCapitalManagementError(
                "position competition net utility identity drift"
            )


def plan_position_opportunity_competition(
    twin: CiboObservedEconomicTwin,
    *,
    opportunity_id: str,
) -> CiboPositionOpportunityCompetitionPlan:
    """Compare a new causal opportunity against currently occupied capital."""

    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "position competition requires canonical Full Economic Twin"
        )
    opportunity = next(
        (item for item in twin.opportunities if item.option_id == opportunity_id),
        None,
    )
    if opportunity is None:
        raise CiboCapitalManagementError(
            "position competition opportunity not found"
        )
    eligible = (
        opportunity.known_at <= twin.captured_at
        and opportunity.earliest_action_at <= twin.captured_at
        and opportunity.expires_at > twin.captured_at
        and opportunity.context_allowed
        and opportunity.provider_viable
        and opportunity.capital_source_eligible
    )
    net_utility = (
        opportunity.expected_net_value_usd
        - opportunity.provider_cost_usd
        - opportunity.uncertainty_penalty
    )
    if not eligible or net_utility <= 0:
        return CiboPositionOpportunityCompetitionPlan(
            twin_id=twin.twin_id,
            opportunity_id=opportunity.option_id,
            fits_without_release=False,
            position_lines=tuple(
                CiboPositionOpportunityCompetitionLine(
                    position_id=item.signal_fingerprint,
                    continuation_utility_per_minute=(
                        item.expected_continuation_net_value_usd
                        - item.provider_cost_usd
                        - item.uncertainty_penalty
                    )
                    / item.expected_remaining_capital_minutes,
                    releasable_stop_risk_usd=Decimal(0),
                    releasable_margin_usd=Decimal(0),
                    release_cost_usd=item.release_cost_usd,
                    proposed_action="KEEP",
                )
                for item in twin.positions
            ),
            released_stop_risk_usd=Decimal(0),
            released_margin_usd=Decimal(0),
            opportunity_net_utility_usd=max(Decimal(0), net_utility),
            displaced_continuation_value_usd=Decimal(0),
            release_cost_usd=Decimal(0),
            net_incremental_utility_usd=max(Decimal(0), net_utility),
            admit_opportunity=False,
        )

    constraints = observed_twin_constraints(twin)
    need_risk = max(
        Decimal(0),
        opportunity.stop_risk_usd - constraints["stop_risk_headroom_usd"],
    )
    need_margin = max(
        Decimal(0),
        opportunity.margin_usd - constraints["margin_headroom_usd"],
    )
    fits = need_risk == 0 and need_margin == 0
    if fits:
        return CiboPositionOpportunityCompetitionPlan(
            twin_id=twin.twin_id,
            opportunity_id=opportunity.option_id,
            fits_without_release=True,
            position_lines=tuple(
                CiboPositionOpportunityCompetitionLine(
                    position_id=item.signal_fingerprint,
                    continuation_utility_per_minute=(
                        item.expected_continuation_net_value_usd
                        - item.provider_cost_usd
                        - item.uncertainty_penalty
                    )
                    / item.expected_remaining_capital_minutes,
                    releasable_stop_risk_usd=Decimal(0),
                    releasable_margin_usd=Decimal(0),
                    release_cost_usd=item.release_cost_usd,
                    proposed_action="KEEP",
                )
                for item in twin.positions
            ),
            released_stop_risk_usd=Decimal(0),
            released_margin_usd=Decimal(0),
            opportunity_net_utility_usd=net_utility,
            displaced_continuation_value_usd=Decimal(0),
            release_cost_usd=Decimal(0),
            net_incremental_utility_usd=net_utility,
            admit_opportunity=True,
        )

    candidates = []
    for item in twin.positions:
        continuation_value = (
            item.expected_continuation_net_value_usd
            - item.provider_cost_usd
            - item.uncertainty_penalty
        )
        per_minute = (
            continuation_value / item.expected_remaining_capital_minutes
        )
        if item.releasable and item.continuation_value_identified:
            candidates.append((per_minute, continuation_value, item))

    candidates.sort(
        key=lambda row: (
            row[0],
            row[1],
            row[2].signal_fingerprint,
        )
    )

    released_risk = Decimal(0)
    released_margin = Decimal(0)
    displaced = Decimal(0)
    release_cost = Decimal(0)
    released_ids: set[str] = set()
    for _, continuation_value, item in candidates:
        if released_risk >= need_risk and released_margin >= need_margin:
            break
        released_risk += item.current_stop_risk_usd
        released_margin += item.current_margin_usd
        displaced += max(Decimal(0), continuation_value)
        release_cost += item.release_cost_usd
        released_ids.add(item.signal_fingerprint)

    enough = released_risk >= need_risk and released_margin >= need_margin
    net_incremental = net_utility - displaced - release_cost
    admit = enough and net_incremental > 0

    lines = tuple(
        CiboPositionOpportunityCompetitionLine(
            position_id=item.signal_fingerprint,
            continuation_utility_per_minute=(
                item.expected_continuation_net_value_usd
                - item.provider_cost_usd
                - item.uncertainty_penalty
            )
            / item.expected_remaining_capital_minutes,
            releasable_stop_risk_usd=(
                item.current_stop_risk_usd
                if item.signal_fingerprint in released_ids and admit
                else Decimal(0)
            ),
            releasable_margin_usd=(
                item.current_margin_usd
                if item.signal_fingerprint in released_ids and admit
                else Decimal(0)
            ),
            release_cost_usd=(
                item.release_cost_usd
                if item.signal_fingerprint in released_ids and admit
                else Decimal(0)
            ),
            proposed_action=(
                "RELEASE"
                if item.signal_fingerprint in released_ids and admit
                else "KEEP"
            ),
        )
        for item in twin.positions
    )

    return CiboPositionOpportunityCompetitionPlan(
        twin_id=twin.twin_id,
        opportunity_id=opportunity.option_id,
        fits_without_release=False,
        position_lines=lines,
        released_stop_risk_usd=released_risk if admit else Decimal(0),
        released_margin_usd=released_margin if admit else Decimal(0),
        opportunity_net_utility_usd=net_utility,
        displaced_continuation_value_usd=displaced if enough else Decimal(0),
        release_cost_usd=release_cost if enough else Decimal(0),
        net_incremental_utility_usd=(
            net_incremental if enough else net_utility
        ),
        admit_opportunity=admit,
    )
