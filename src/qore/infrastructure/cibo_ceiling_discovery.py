"""Non-certifying closure gate for CIBO CEILING_DISCOVERY.

This module prevents a diagnostic frontier or a partially wired replay from being
misrepresented as the real CIBO economic ceiling.  A ceiling claim is admissible
only after every decision in the frozen research population has traversed native
MAX intelligence and the sovereign capital runtime on one continuous USD60
account, with the mandatory causal ablations present.

If the available research population ends while CIBO still has growth capacity,
the result is only an observed lower bound and CEILING_DISCOVERY stays open.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_maximum_capability import (
    CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD,
)


class CiboCeilingLimitKind(StrEnum):
    EDGE = "EDGE"
    RISK = "RISK"
    MARGIN = "MARGIN"
    CORRELATION = "CORRELATION"
    PORTFOLIO_CONCENTRATION = "PORTFOLIO_CONCENTRATION"
    PROVIDER_GEOMETRY = "PROVIDER_GEOMETRY"
    MINIMUM_VOLUME = "MINIMUM_VOLUME"
    CAPITAL_SATURATION = "CAPITAL_SATURATION"
    SURVIVAL = "SURVIVAL"
    OPTIONALITY = "OPTIONALITY"
    OPPORTUNITY_POPULATION_EXHAUSTED = "OPPORTUNITY_POPULATION_EXHAUSTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CiboCeilingDiscoveryEvidence:
    decision_count: int
    native_max_pass_count: int
    sovereign_runtime_evaluation_count: int
    full_semantic_decision_count: int
    external_ai_call_count: int
    account_reset_count: int
    economic_era_reset_count: int
    initial_capital_usd: Decimal
    ending_capital_usd: Decimal
    peak_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    native_sovereign_runtime_used: bool
    qore_risk_sovereign: bool
    outcome_used_for_predecision: bool
    target_capital_used_for_tuning: bool
    sizing_ablation_present: bool
    adaptive_leverage_ablation_present: bool
    cibo_compound_ablation_present: bool
    compound_portfolio_ablation_present: bool
    cognition_ablation_present: bool
    population_exhausted: bool
    growth_capacity_remaining_at_population_end: bool
    intrinsic_ceiling_claimed: bool
    observed_lower_bound_only: bool
    limiting_factor: CiboCeilingLimitKind

    def __post_init__(self) -> None:
        for name in (
            "decision_count",
            "native_max_pass_count",
            "sovereign_runtime_evaluation_count",
            "full_semantic_decision_count",
            "external_ai_call_count",
            "account_reset_count",
            "economic_era_reset_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"ceiling discovery {name} must be non-negative int"
                )
        if self.decision_count <= 0:
            raise CiboCapitalManagementError(
                "ceiling discovery requires at least one decision"
            )
        if self.native_max_pass_count != self.decision_count:
            raise CiboCapitalManagementError(
                "ceiling discovery requires Native MAX on every decision"
            )
        if self.sovereign_runtime_evaluation_count != self.decision_count:
            raise CiboCapitalManagementError(
                "ceiling discovery requires sovereign runtime on every decision"
            )
        if self.full_semantic_decision_count != self.decision_count:
            raise CiboCapitalManagementError(
                "ceiling discovery requires full semantics on every decision"
            )
        if self.external_ai_call_count != 0:
            raise CiboCapitalManagementError(
                "ceiling discovery forbids external AI"
            )
        if self.account_reset_count != 0 or self.economic_era_reset_count != 0:
            raise CiboCapitalManagementError(
                "ceiling discovery forbids capital resets"
            )

        for name in (
            "initial_capital_usd",
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
                    f"ceiling discovery {name} must be finite non-negative Decimal"
                )
        if self.initial_capital_usd != CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD:
            raise CiboCapitalManagementError(
                "ceiling discovery must start from exactly USD60"
            )
        if self.peak_capital_usd < max(
            self.initial_capital_usd,
            self.ending_capital_usd,
        ):
            raise CiboCapitalManagementError(
                "ceiling discovery peak capital identity drift"
            )
        if self.maximum_drawdown_usd > self.peak_capital_usd:
            raise CiboCapitalManagementError(
                "ceiling discovery drawdown exceeds peak capital"
            )

        bool_fields = (
            "native_sovereign_runtime_used",
            "qore_risk_sovereign",
            "outcome_used_for_predecision",
            "target_capital_used_for_tuning",
            "sizing_ablation_present",
            "adaptive_leverage_ablation_present",
            "cibo_compound_ablation_present",
            "compound_portfolio_ablation_present",
            "cognition_ablation_present",
            "population_exhausted",
            "growth_capacity_remaining_at_population_end",
            "intrinsic_ceiling_claimed",
            "observed_lower_bound_only",
        )
        if any(type(getattr(self, name)) is not bool for name in bool_fields):
            raise CiboCapitalManagementError(
                "ceiling discovery boolean evidence malformed"
            )
        if not self.native_sovereign_runtime_used:
            raise CiboCapitalManagementError(
                "diagnostic frontier cannot substitute for sovereign CIBO runtime"
            )
        if not self.qore_risk_sovereign:
            raise CiboCapitalManagementError(
                "ceiling discovery requires sovereign QORE Risk"
            )
        if self.outcome_used_for_predecision:
            raise CiboCapitalManagementError(
                "ceiling discovery contains outcome-aware decision leakage"
            )
        if self.target_capital_used_for_tuning:
            raise CiboCapitalManagementError(
                "ceiling discovery cannot tune toward a target capital"
            )
        if not all(
            (
                self.sizing_ablation_present,
                self.adaptive_leverage_ablation_present,
                self.cibo_compound_ablation_present,
                self.compound_portfolio_ablation_present,
                self.cognition_ablation_present,
            )
        ):
            raise CiboCapitalManagementError(
                "ceiling discovery requires all mandatory causal ablations"
            )
        if type(self.limiting_factor) is not CiboCeilingLimitKind:
            raise CiboCapitalManagementError(
                "ceiling discovery limiting factor must be canonical"
            )
        if self.intrinsic_ceiling_claimed and self.observed_lower_bound_only:
            raise CiboCapitalManagementError(
                "intrinsic ceiling and observed lower bound are mutually exclusive"
            )
        if (
            self.population_exhausted
            and self.growth_capacity_remaining_at_population_end
        ):
            if self.intrinsic_ceiling_claimed:
                raise CiboCapitalManagementError(
                    "population exhaustion with remaining growth cannot be intrinsic ceiling"
                )
            if not self.observed_lower_bound_only:
                raise CiboCapitalManagementError(
                    "population exhaustion with remaining growth must be lower bound only"
                )
            if (
                self.limiting_factor
                is not CiboCeilingLimitKind.OPPORTUNITY_POPULATION_EXHAUSTED
            ):
                raise CiboCapitalManagementError(
                    "lower-bound run must identify opportunity population exhaustion"
                )
        if self.intrinsic_ceiling_claimed and (
            self.limiting_factor
            in {
                CiboCeilingLimitKind.UNKNOWN,
                CiboCeilingLimitKind.OPPORTUNITY_POPULATION_EXHAUSTED,
            }
        ):
            raise CiboCapitalManagementError(
                "intrinsic ceiling requires a structural limiting factor"
            )

    @property
    def capital_multiple(self) -> Decimal:
        return self.ending_capital_usd / self.initial_capital_usd

    @property
    def maximum_drawdown_fraction_of_peak(self) -> Decimal:
        if self.peak_capital_usd == 0:
            return Decimal(0)
        return self.maximum_drawdown_usd / self.peak_capital_usd

    @property
    def ceiling_discovery_ready_to_close(self) -> bool:
        return (
            self.intrinsic_ceiling_claimed
            and not self.observed_lower_bound_only
            and self.limiting_factor
            not in {
                CiboCeilingLimitKind.UNKNOWN,
                CiboCeilingLimitKind.OPPORTUNITY_POPULATION_EXHAUSTED,
            }
        )
