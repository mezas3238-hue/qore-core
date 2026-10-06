"""Frozen +2000% in 10 months examination for sovereign CIBO.

Pass condition:
- one shared account starts at exactly USD60;
- exact canonical seven Traders;
- native CIBO MAX intelligence on every decision;
- zero external AI/reasoning-provider calls;
- full CF01-CF19 causal semantics on every decision;
- continuous compound, shared portfolio, shared QORE Risk;
- zero capital/era resets;
- frozen Trader logic;
- no outcome-aware predecision tuning;
- ending capital >= USD1260, i.e. +2000% NET return from USD60;
- the complete examined decision window must not exceed 10 calendar months.

USD1260 is a frozen PASS threshold, never a tuning target.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_maximum_capability import (
    CIBO_MAXIMUM_CAPABILITY_TRADERS,
)


CIBO_2000_PERCENT_INITIAL_CAPITAL_USD = Decimal("60")
CIBO_2000_PERCENT_REQUIRED_NET_RETURN_PERCENT = Decimal("2000")
CIBO_2000_PERCENT_MINIMUM_ENDING_CAPITAL_USD = Decimal("1260")
CIBO_2000_PERCENT_MAXIMUM_CALENDAR_MONTHS = 10


def add_calendar_months(value: datetime, months: int) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            "2000-percent exam datetime must be timezone-aware"
        )
    if not isinstance(months, int) or isinstance(months, bool) or months < 0:
        raise CiboCapitalManagementError(
            "2000-percent exam months must be non-negative int"
        )

    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@dataclass(frozen=True, slots=True)
class CiboCompound2000PercentTenMonthExamContract:
    exam_id: str = "CIBO_COMPOUND_2000_PERCENT_10M_EXAM_V1"
    initial_capital_usd: Decimal = CIBO_2000_PERCENT_INITIAL_CAPITAL_USD
    minimum_ending_capital_usd: Decimal = (
        CIBO_2000_PERCENT_MINIMUM_ENDING_CAPITAL_USD
    )
    required_net_return_percent: Decimal = (
        CIBO_2000_PERCENT_REQUIRED_NET_RETURN_PERCENT
    )
    maximum_calendar_months: int = CIBO_2000_PERCENT_MAXIMUM_CALENDAR_MONTHS
    trader_ids: tuple[TraderLineage, ...] = CIBO_MAXIMUM_CAPABILITY_TRADERS
    account_count: int = 1
    trader_logic_frozen: bool = True
    native_max_intelligence_required: bool = True
    full_cf_semantics_required: bool = True
    continuous_compound_required: bool = True
    shared_portfolio_required: bool = True
    shared_qore_risk_required: bool = True
    capital_reset_allowed: bool = False
    threshold_used_for_tuning: bool = False
    external_ai_allowed: bool = False
    external_reasoning_provider_allowed: bool = False
    outcome_aware_predecision_allowed: bool = False
    fresh_oos_claimed: bool = False
    certification_claimed: bool = False
    live_authorized: bool = False
    production_authorized: bool = False
    real_capital_authorized: bool = False
    broker_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if self.initial_capital_usd != Decimal("60"):
            raise CiboCapitalManagementError(
                "2000-percent/10m exam must start from exactly USD60"
            )
        if self.minimum_ending_capital_usd != Decimal("1260"):
            raise CiboCapitalManagementError(
                "2000-percent/10m minimum ending capital must be USD1260"
            )
        if self.required_net_return_percent != Decimal("2000"):
            raise CiboCapitalManagementError(
                "2000-percent/10m net return threshold drift"
            )
        if self.maximum_calendar_months != 10:
            raise CiboCapitalManagementError(
                "2000-percent exam maximum duration must be exactly 10 calendar months"
            )
        if self.trader_ids != CIBO_MAXIMUM_CAPABILITY_TRADERS:
            raise CiboCapitalManagementError(
                "2000-percent/10m exam requires canonical seven Traders"
            )
        if self.account_count != 1:
            raise CiboCapitalManagementError(
                "2000-percent/10m exam requires one shared account"
            )
        if (
            not self.trader_logic_frozen
            or not self.native_max_intelligence_required
            or not self.full_cf_semantics_required
            or not self.continuous_compound_required
            or not self.shared_portfolio_required
            or not self.shared_qore_risk_required
            or self.capital_reset_allowed
            or self.threshold_used_for_tuning
            or self.external_ai_allowed
            or self.external_reasoning_provider_allowed
            or self.outcome_aware_predecision_allowed
            or self.fresh_oos_claimed
            or self.certification_claimed
            or self.live_authorized
            or self.production_authorized
            or self.real_capital_authorized
            or self.broker_mutation_authorized
        ):
            raise CiboCapitalManagementError(
                "2000-percent/10m exam governance drift"
            )


DEFAULT_CIBO_COMPOUND_2000_PERCENT_10M_EXAM = (
    CiboCompound2000PercentTenMonthExamContract()
)


@dataclass(frozen=True, slots=True)
class CiboCompound2000PercentTenMonthExamResult:
    contract: CiboCompound2000PercentTenMonthExamContract
    first_decision_at: datetime
    last_decision_at: datetime
    opportunity_decision_count: int
    native_max_intelligence_decision_count: int
    full_cf_semantic_decision_count: int
    external_ai_call_count: int
    account_reset_count: int
    economic_era_reset_count: int
    ending_capital_usd: Decimal
    peak_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    settled_operation_count: int
    outcome_used_for_predecision: bool = False
    trader_logic_modified_for_exam: bool = False
    broker_mutation: bool = False
    live: bool = False
    production: bool = False
    real_capital: bool = False
    certification_claimed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.contract,
            CiboCompound2000PercentTenMonthExamContract,
        ):
            raise CiboCapitalManagementError(
                "2000-percent/10m result requires canonical contract"
            )
        for name in ("first_decision_at", "last_decision_at"):
            value = getattr(self, name)
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise CiboCapitalManagementError(
                    f"2000-percent/10m {name} must be timezone-aware"
                )
        if self.last_decision_at < self.first_decision_at:
            raise CiboCapitalManagementError(
                "2000-percent/10m decision window is reversed"
            )
        deadline = add_calendar_months(
            self.first_decision_at,
            self.contract.maximum_calendar_months,
        )
        if self.last_decision_at > deadline:
            raise CiboCapitalManagementError(
                "2000-percent exam exceeded 10 calendar months"
            )

        for name in (
            "opportunity_decision_count",
            "native_max_intelligence_decision_count",
            "full_cf_semantic_decision_count",
            "external_ai_call_count",
            "account_reset_count",
            "economic_era_reset_count",
            "settled_operation_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"2000-percent/10m {name} must be non-negative int"
                )
        if self.opportunity_decision_count <= 0:
            raise CiboCapitalManagementError(
                "2000-percent/10m exam requires decisions"
            )
        if (
            self.native_max_intelligence_decision_count
            != self.opportunity_decision_count
            or self.full_cf_semantic_decision_count
            != self.opportunity_decision_count
        ):
            raise CiboCapitalManagementError(
                "2000-percent/10m requires native MAX + full CF semantics on every decision"
            )
        if self.external_ai_call_count != 0:
            raise CiboCapitalManagementError(
                "2000-percent/10m exam forbids external AI"
            )
        if self.account_reset_count != 0 or self.economic_era_reset_count != 0:
            raise CiboCapitalManagementError(
                "2000-percent/10m exam forbids capital/era resets"
            )

        for name in (
            "ending_capital_usd",
            "peak_capital_usd",
            "maximum_drawdown_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"2000-percent/10m {name} must be finite non-negative Decimal"
                )
        if self.peak_capital_usd < max(
            self.contract.initial_capital_usd,
            self.ending_capital_usd,
        ):
            raise CiboCapitalManagementError(
                "2000-percent/10m peak capital identity drift"
            )
        if self.maximum_drawdown_usd > self.peak_capital_usd:
            raise CiboCapitalManagementError(
                "2000-percent/10m drawdown exceeds peak capital"
            )
        if self.ending_capital_usd < self.contract.minimum_ending_capital_usd:
            raise CiboCapitalManagementError(
                "2000-percent/10m ending capital below USD1260"
            )

        for name in (
            "outcome_used_for_predecision",
            "trader_logic_modified_for_exam",
            "broker_mutation",
            "live",
            "production",
            "real_capital",
            "certification_claimed",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"2000-percent/10m {name} must be bool"
                )
        if any(
            (
                self.outcome_used_for_predecision,
                self.trader_logic_modified_for_exam,
                self.broker_mutation,
                self.live,
                self.production,
                self.real_capital,
                self.certification_claimed,
            )
        ):
            raise CiboCapitalManagementError(
                "2000-percent/10m exam governance contamination"
            )

    @property
    def deadline(self) -> datetime:
        return add_calendar_months(
            self.first_decision_at,
            self.contract.maximum_calendar_months,
        )

    @property
    def net_return_percent(self) -> Decimal:
        return (
            (self.ending_capital_usd - self.contract.initial_capital_usd)
            / self.contract.initial_capital_usd
        ) * Decimal("100")

    @property
    def capital_multiple(self) -> Decimal:
        return self.ending_capital_usd / self.contract.initial_capital_usd

    @property
    def passed(self) -> bool:
        return True
