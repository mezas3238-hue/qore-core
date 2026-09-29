"""Descriptive fresh population for GEN-C7 profit-preservation shadow.

Coverage is not utility. This module summarizes durable pre-outcome GEN-C7
decisions and never claims economic value, causal benefit or certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_profit_preservation_shadow import Genc7Action
from qore.infrastructure.cibo_profit_preservation_store import (
    VersionedGenc7ShadowBook,
)


class Genc7PopulationStatus(StrEnum):
    EMPTY = "EMPTY"
    DESCRIPTIVE_AVAILABLE = "DESCRIPTIVE_AVAILABLE"


@dataclass(frozen=True, slots=True)
class Genc7FreshPopulation:
    status: Genc7PopulationStatus
    decision_epoch_count: int
    treatment_control_divergence_count: int
    blocked_decision_count: int
    protect_count: int
    harvest_count: int
    opportunity_reserve_count: int
    compound_count: int
    hold_count: int
    account_keys: tuple[str, ...]
    decision_calendar_days: int
    calendar_span_days: int
    minimum_evaluation_horizon_minutes: int | None
    maximum_evaluation_horizon_minutes: int | None
    mean_giveback_amount_usd: Decimal | None
    mean_profit_retention_ratio: Decimal | None
    mean_base_drawdown_usd: Decimal | None
    mean_compound_drawdown_usd: Decimal | None
    floor_growth_observed_count: int
    mean_floor_growth_rate: Decimal | None
    blockers: tuple[str, ...]
    descriptive_only: bool = True
    economic_utility_ready: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not Genc7PopulationStatus:
            raise CiboCompoundCapitalError(
                "GEN-C7 population status is invalid"
            )
        for name in (
            "decision_epoch_count",
            "treatment_control_divergence_count",
            "blocked_decision_count",
            "protect_count",
            "harvest_count",
            "opportunity_reserve_count",
            "compound_count",
            "hold_count",
            "decision_calendar_days",
            "calendar_span_days",
            "floor_growth_observed_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C7 population {name} must be non-negative int"
                )
        if self.treatment_control_divergence_count > self.decision_epoch_count:
            raise CiboCompoundCapitalError(
                "GEN-C7 population divergence count exceeds decisions"
            )
        if self.blocked_decision_count > self.decision_epoch_count:
            raise CiboCompoundCapitalError(
                "GEN-C7 population blocked count exceeds decisions"
            )
        action_total = (
            self.protect_count
            + self.harvest_count
            + self.opportunity_reserve_count
            + self.compound_count
            + self.hold_count
        )
        if action_total != self.decision_epoch_count:
            raise CiboCompoundCapitalError(
                "GEN-C7 population action counts drift"
            )
        if len(self.account_keys) != len(set(self.account_keys)):
            raise CiboCompoundCapitalError(
                "GEN-C7 population account keys must be unique"
            )
        if self.decision_epoch_count == 0:
            if self.status is not Genc7PopulationStatus.EMPTY:
                raise CiboCompoundCapitalError(
                    "GEN-C7 empty population status drift"
                )
            if (
                self.minimum_evaluation_horizon_minutes is not None
                or self.maximum_evaluation_horizon_minutes is not None
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C7 empty population cannot have horizons"
                )
        else:
            if self.status is not Genc7PopulationStatus.DESCRIPTIVE_AVAILABLE:
                raise CiboCompoundCapitalError(
                    "GEN-C7 populated status drift"
                )
            if (
                self.minimum_evaluation_horizon_minutes is None
                or self.maximum_evaluation_horizon_minutes is None
                or self.minimum_evaluation_horizon_minutes <= 0
                or self.maximum_evaluation_horizon_minutes
                < self.minimum_evaluation_horizon_minutes
            ):
                raise CiboCompoundCapitalError(
                    "GEN-C7 population horizon range is invalid"
                )
        for name in (
            "mean_giveback_amount_usd",
            "mean_profit_retention_ratio",
            "mean_base_drawdown_usd",
            "mean_compound_drawdown_usd",
            "mean_floor_growth_rate",
        ):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise CiboCompoundCapitalError(
                    f"GEN-C7 population {name} must be finite Decimal"
                )
        if len(self.blockers) != len(set(self.blockers)):
            raise CiboCompoundCapitalError(
                "GEN-C7 population blockers must be unique"
            )
        for name in (
            "descriptive_only",
            "economic_utility_ready",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"GEN-C7 population {name} must be bool"
                )
        if (
            not self.descriptive_only
            or self.economic_utility_ready
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "GEN-C7 population cannot claim economic readiness"
            )


def describe_genc7_fresh_population(
    *,
    book: VersionedGenc7ShadowBook,
) -> Genc7FreshPopulation:
    if not isinstance(book, VersionedGenc7ShadowBook):
        raise CiboCompoundCapitalError(
            "GEN-C7 population requires canonical durable book"
        )

    seals_list = []
    for record in book.records:
        seal = book.seal_for_decision(record.decision_id)
        if seal is None:
            raise CiboCompoundCapitalError(
                "GEN-C7 population durable decision seal missing"
            )
        seals_list.append(seal)
    seals = tuple(seals_list)
    if not seals:
        return Genc7FreshPopulation(
            status=Genc7PopulationStatus.EMPTY,
            decision_epoch_count=0,
            treatment_control_divergence_count=0,
            blocked_decision_count=0,
            protect_count=0,
            harvest_count=0,
            opportunity_reserve_count=0,
            compound_count=0,
            hold_count=0,
            account_keys=(),
            decision_calendar_days=0,
            calendar_span_days=0,
            minimum_evaluation_horizon_minutes=None,
            maximum_evaluation_horizon_minutes=None,
            mean_giveback_amount_usd=None,
            mean_profit_retention_ratio=None,
            mean_base_drawdown_usd=None,
            mean_compound_drawdown_usd=None,
            floor_growth_observed_count=0,
            mean_floor_growth_rate=None,
            blockers=("NO_GENC7_DECISIONS",),
            descriptive_only=True,
            economic_utility_ready=False,
            certification_ready=False,
        )

    actions = tuple(item.treatment_action for item in seals)
    dates = tuple(item.decision_at.date() for item in seals)
    horizons = tuple(item.evaluation_horizon_minutes for item in seals)
    floor_rates = tuple(
        item.floor_growth_rate
        for item in seals
        if item.floor_growth_rate is not None
    )
    blockers: list[str] = []
    divergence_count = sum(
        1 for item in seals if item.treatment_differs_from_control
    )
    if divergence_count == 0:
        blockers.append("NO_TREATMENT_CONTROL_DIVERGENCE")
    blockers.append("ECONOMIC_GATE_NOT_YET_PREREGISTERED")
    blockers.append("OUTCOME_BINDING_NOT_EVALUATED")

    return Genc7FreshPopulation(
        status=Genc7PopulationStatus.DESCRIPTIVE_AVAILABLE,
        decision_epoch_count=len(seals),
        treatment_control_divergence_count=divergence_count,
        blocked_decision_count=sum(1 for item in seals if item.blocker_codes),
        protect_count=actions.count(Genc7Action.PROTECT),
        harvest_count=actions.count(
            Genc7Action.HARVEST_TO_STRATEGIC_RESERVE
        ),
        opportunity_reserve_count=actions.count(
            Genc7Action.RESERVE_OPPORTUNITY_CAPACITY
        ),
        compound_count=actions.count(Genc7Action.COMPOUND),
        hold_count=actions.count(Genc7Action.HOLD_CURRENT_CAPITAL_STATE),
        account_keys=tuple(
            sorted(
                {
                    f"{item.account_provider_key}:{item.account_ref}"
                    for item in seals
                }
            )
        ),
        decision_calendar_days=len(set(dates)),
        calendar_span_days=_calendar_span_days(dates),
        minimum_evaluation_horizon_minutes=min(horizons),
        maximum_evaluation_horizon_minutes=max(horizons),
        mean_giveback_amount_usd=_mean(
            tuple(item.giveback_amount_usd for item in seals)
        ),
        mean_profit_retention_ratio=_mean(
            tuple(item.profit_retention_ratio for item in seals)
        ),
        mean_base_drawdown_usd=_mean(
            tuple(item.base_drawdown_usd for item in seals)
        ),
        mean_compound_drawdown_usd=_mean(
            tuple(item.compound_drawdown_usd for item in seals)
        ),
        floor_growth_observed_count=len(floor_rates),
        mean_floor_growth_rate=(
            None if not floor_rates else _mean(floor_rates)
        ),
        blockers=tuple(blockers),
        descriptive_only=True,
        economic_utility_ready=False,
        certification_ready=False,
    )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCompoundCapitalError(
            "GEN-C7 population cannot average empty values"
        )
    return sum(values, Decimal("0")) / Decimal(len(values))


def _calendar_span_days(values: tuple[date, ...]) -> int:
    if not values:
        return 0
    return (max(values) - min(values)).days + 1
