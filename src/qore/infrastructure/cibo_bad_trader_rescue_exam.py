"""Frozen Bad-Trader Rescue Exam for sovereign CIBO.

Purpose
-------
Prove that CIBO can take a fixed population of weak/poorly performing Traders
and make every Trader's *managed contribution* positive while the shared
single account survives and grows.

This exam evaluates CIBO, not Trader redesign.

Frozen laws
-----------
- exactly one USD60 account;
- exact canonical seven Traders;
- Trader methodology/configuration is frozen for the exam;
- no Trader is modified or optimized to improve exam outcome;
- CIBO native maximum intelligence is mandatory on every decision;
- zero external-AI/reasoning-provider calls;
- CF01-CF19 full causal semantic surface is mandatory;
- no capital reset between eras;
- CIBO may abstain, reduce, delay, allocate, size, leverage, compound,
  reallocate and protect capital;
- QORE Risk remains sovereign;
- no future/outcome-aware predecision tuning;
- every Trader's managed net contribution must be strictly positive;
- portfolio/account net result must be strictly positive;
- this burned/reusable exam is research evidence, never Fresh OOS certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_maximum_capability import (
    CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
    CIBO_MAXIMUM_CAPABILITY_TRADERS,
)


@dataclass(frozen=True, slots=True)
class CiboBadTraderRescueExamContract:
    exam_id: str = "CIBO_BAD_TRADER_RESCUE_EXAM_V1"
    initial_capital_usd: Decimal = CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD
    trader_ids: tuple[TraderLineage, ...] = CIBO_MAXIMUM_CAPABILITY_TRADERS
    account_count: int = 1
    trader_methodology_frozen: bool = True
    trader_optimization_for_exam_allowed: bool = False
    native_max_intelligence_required: bool = True
    full_cf01_cf19_semantics_required: bool = True
    external_ai_allowed: bool = False
    external_reasoning_provider_allowed: bool = False
    capital_reset_allowed: bool = False
    continuous_compound_required: bool = True
    shared_portfolio_required: bool = True
    shared_qore_risk_required: bool = True
    all_traders_positive_required: bool = True
    account_positive_required: bool = True
    outcome_aware_predecision_allowed: bool = False
    fresh_oos_claimed: bool = False
    certification_claimed: bool = False
    live_authorized: bool = False
    production_authorized: bool = False
    real_capital_authorized: bool = False
    broker_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.exam_id:
            raise CiboCapitalManagementError("rescue exam id is required")
        if self.initial_capital_usd != Decimal("60"):
            raise CiboCapitalManagementError(
                "rescue exam V1 must start from exactly USD60"
            )
        if self.account_count != 1:
            raise CiboCapitalManagementError(
                "rescue exam requires exactly one shared account"
            )
        if self.trader_ids != CIBO_MAXIMUM_CAPABILITY_TRADERS:
            raise CiboCapitalManagementError(
                "rescue exam requires exact canonical seven Traders"
            )
        if len(set(self.trader_ids)) != 7:
            raise CiboCapitalManagementError(
                "rescue exam requires seven unique Traders"
            )
        if (
            not self.trader_methodology_frozen
            or self.trader_optimization_for_exam_allowed
            or not self.native_max_intelligence_required
            or not self.full_cf01_cf19_semantics_required
            or self.external_ai_allowed
            or self.external_reasoning_provider_allowed
            or self.capital_reset_allowed
            or not self.continuous_compound_required
            or not self.shared_portfolio_required
            or not self.shared_qore_risk_required
            or not self.all_traders_positive_required
            or not self.account_positive_required
            or self.outcome_aware_predecision_allowed
            or self.fresh_oos_claimed
            or self.certification_claimed
            or self.live_authorized
            or self.production_authorized
            or self.real_capital_authorized
            or self.broker_mutation_authorized
        ):
            raise CiboCapitalManagementError(
                "rescue exam governance drift"
            )


DEFAULT_CIBO_BAD_TRADER_RESCUE_EXAM = CiboBadTraderRescueExamContract()


@dataclass(frozen=True, slots=True)
class CiboManagedTraderContribution:
    trader_id: TraderLineage
    opportunity_count: int
    selected_count: int
    abstained_count: int
    reduced_count: int
    rejected_count: int
    settled_count: int
    gross_profit_usd: Decimal
    gross_loss_usd: Decimal
    net_contribution_usd: Decimal

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "rescue exam trader contribution requires canonical lineage"
            )
        for name in (
            "opportunity_count",
            "selected_count",
            "abstained_count",
            "reduced_count",
            "rejected_count",
            "settled_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"rescue exam {name} must be non-negative int"
                )
        if self.selected_count + self.abstained_count != self.opportunity_count:
            raise CiboCapitalManagementError(
                "rescue exam selected/abstained identity drift"
            )
        if self.settled_count > self.selected_count:
            raise CiboCapitalManagementError(
                "rescue exam settled count exceeds selected count"
            )
        for name in (
            "gross_profit_usd",
            "gross_loss_usd",
            "net_contribution_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"rescue exam {name} must be finite Decimal"
                )
        if self.gross_profit_usd < 0 or self.gross_loss_usd < 0:
            raise CiboCapitalManagementError(
                "rescue exam gross profit/loss must be non-negative"
            )
        if (
            self.net_contribution_usd
            != self.gross_profit_usd - self.gross_loss_usd
        ):
            raise CiboCapitalManagementError(
                "rescue exam trader P/L identity drift"
            )


@dataclass(frozen=True, slots=True)
class CiboBadTraderRescueExamResult:
    contract: CiboBadTraderRescueExamContract
    opportunity_decision_count: int
    native_max_intelligence_decision_count: int
    full_cf_semantic_decision_count: int
    external_ai_call_count: int
    account_reset_count: int
    economic_era_reset_count: int
    ending_capital_usd: Decimal
    peak_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    trader_contributions: tuple[CiboManagedTraderContribution, ...]
    outcome_used_for_predecision: bool = False
    trader_logic_modified_for_exam: bool = False
    broker_mutation: bool = False
    live: bool = False
    production: bool = False
    real_capital: bool = False
    certification_claimed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.contract, CiboBadTraderRescueExamContract):
            raise CiboCapitalManagementError(
                "rescue result requires canonical exam contract"
            )
        for name in (
            "opportunity_decision_count",
            "native_max_intelligence_decision_count",
            "full_cf_semantic_decision_count",
            "external_ai_call_count",
            "account_reset_count",
            "economic_era_reset_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"rescue exam {name} must be non-negative int"
                )
        if self.opportunity_decision_count <= 0:
            raise CiboCapitalManagementError(
                "rescue exam requires decisions"
            )
        if (
            self.native_max_intelligence_decision_count
            != self.opportunity_decision_count
        ):
            raise CiboCapitalManagementError(
                "every rescue-exam decision must use native MAX intelligence"
            )
        if (
            self.full_cf_semantic_decision_count
            != self.opportunity_decision_count
        ):
            raise CiboCapitalManagementError(
                "every rescue-exam decision must consume full CF semantics"
            )
        if self.external_ai_call_count != 0:
            raise CiboCapitalManagementError(
                "rescue exam forbids external AI"
            )
        if self.account_reset_count != 0 or self.economic_era_reset_count != 0:
            raise CiboCapitalManagementError(
                "rescue exam forbids capital/era resets"
            )
        for name in (
            "ending_capital_usd",
            "peak_capital_usd",
            "maximum_drawdown_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"rescue exam {name} must be finite non-negative Decimal"
                )
        if self.peak_capital_usd < max(
            self.contract.initial_capital_usd,
            self.ending_capital_usd,
        ):
            raise CiboCapitalManagementError(
                "rescue exam peak-capital identity drift"
            )
        if self.maximum_drawdown_usd > self.peak_capital_usd:
            raise CiboCapitalManagementError(
                "rescue exam drawdown exceeds peak capital"
            )

        observed = tuple(
            item.trader_id for item in self.trader_contributions
        )
        if observed != self.contract.trader_ids:
            raise CiboCapitalManagementError(
                "rescue exam requires exact canonical trader order/surface"
            )
        if len(set(observed)) != 7:
            raise CiboCapitalManagementError(
                "rescue exam trader surface is not unique"
            )

        if self.ending_capital_usd <= self.contract.initial_capital_usd:
            raise CiboCapitalManagementError(
                "rescue exam account must finish strictly positive vs initial capital"
            )
        for item in self.trader_contributions:
            if item.net_contribution_usd <= 0:
                raise CiboCapitalManagementError(
                    f"rescue exam trader {item.trader_id.value} did not finish positive"
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
                    f"rescue exam {name} must be bool"
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
                "rescue exam governance contamination"
            )

    @property
    def account_net_profit_usd(self) -> Decimal:
        return self.ending_capital_usd - self.contract.initial_capital_usd

    @property
    def passed(self) -> bool:
        return True
