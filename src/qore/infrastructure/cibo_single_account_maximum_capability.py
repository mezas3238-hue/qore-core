"""Single-account seven-Trader Maximum Capability protocol for CIBO.

This contract defines the only admissible research shape for measuring the
economic ceiling of CIBO from USD60:

- exactly one account;
- exactly seven canonical Traders sharing that account;
- no capital reset between historical eras;
- realized-profit compounding is continuous;
- every opportunity is evaluated through sovereign CIBO intelligence before
  capital sizing;
- QORE Risk remains sovereign;
- no target capital is used as a tuning objective;
- no future outcome, LIVE, production or broker mutation is allowed.

The contract measures the ceiling; it never promises a particular ending
capital.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD = Decimal("60")
CIBO_MAXIMUM_CAPABILITY_TRADERS: tuple[TraderLineage, ...] = (
    TraderLineage.VT08_FOREX,
    TraderLineage.R34_XAUUSD,
    TraderLineage.R38_EURUSD,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R38_GBPJPY,
    TraderLineage.R42_AUDJPY,
    TraderLineage.VT31_NAS100,
)


@dataclass(frozen=True, slots=True)
class CiboSingleAccountMaximumCapabilityProtocol:
    protocol_id: str = "CIBO_SINGLE_ACCOUNT_7TRADER_MAXIMUM_CAPABILITY_V1"
    initial_capital_usd: Decimal = CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD
    trader_ids: tuple[TraderLineage, ...] = CIBO_MAXIMUM_CAPABILITY_TRADERS
    account_count: int = 1
    capital_reset_allowed: bool = False
    continuous_realized_profit_compound: bool = True
    shared_portfolio_state: bool = True
    shared_qore_risk_state: bool = True
    sovereign_cibo_required: bool = True
    full_cognitive_semantics_required: bool = True
    target_capital_used_for_tuning: bool = False
    outcome_aware_tuning_allowed: bool = False
    fresh_oos_claimed: bool = False
    certification_claimed: bool = False
    live_authorized: bool = False
    production_authorized: bool = False
    real_capital_authorized: bool = False
    broker_mutation_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.protocol_id:
            raise CiboCapitalManagementError(
                "maximum-capability protocol_id is required"
            )
        if (
            not isinstance(self.initial_capital_usd, Decimal)
            or not self.initial_capital_usd.is_finite()
            or self.initial_capital_usd <= 0
        ):
            raise CiboCapitalManagementError(
                "maximum-capability initial capital must be finite positive Decimal"
            )
        if self.initial_capital_usd != CIBO_MAXIMUM_CAPABILITY_INITIAL_CAPITAL_USD:
            raise CiboCapitalManagementError(
                "maximum-capability V1 must start from exactly USD60"
            )
        if self.account_count != 1:
            raise CiboCapitalManagementError(
                "maximum-capability protocol requires exactly one account"
            )
        if self.trader_ids != CIBO_MAXIMUM_CAPABILITY_TRADERS:
            raise CiboCapitalManagementError(
                "maximum-capability protocol requires exact canonical seven Traders"
            )
        if len(set(self.trader_ids)) != 7:
            raise CiboCapitalManagementError(
                "maximum-capability Trader surface must contain seven unique Traders"
            )
        if (
            self.capital_reset_allowed
            or not self.continuous_realized_profit_compound
            or not self.shared_portfolio_state
            or not self.shared_qore_risk_state
            or not self.sovereign_cibo_required
            or not self.full_cognitive_semantics_required
            or self.target_capital_used_for_tuning
            or self.outcome_aware_tuning_allowed
            or self.fresh_oos_claimed
            or self.certification_claimed
            or self.live_authorized
            or self.production_authorized
            or self.real_capital_authorized
            or self.broker_mutation_authorized
        ):
            raise CiboCapitalManagementError(
                "maximum-capability protocol governance drift"
            )


@dataclass(frozen=True, slots=True)
class CiboMaximumCapabilityRunEvidence:
    """Auditable result envelope for one single-account ceiling run."""

    protocol: CiboSingleAccountMaximumCapabilityProtocol
    account_identity: str
    opportunity_decision_count: int
    sovereign_runtime_evaluation_count: int
    full_semantic_decision_count: int
    trader_ids_observed: tuple[TraderLineage, ...]
    account_reset_count: int
    economic_era_reset_count: int
    ending_capital_usd: Decimal
    peak_capital_usd: Decimal
    maximum_drawdown_usd: Decimal
    settled_operation_count: int
    qore_risk_reduce_count: int
    qore_risk_reject_count: int
    compound_reinvestment_count: int
    portfolio_compound_reinvestment_count: int
    outcome_used_for_predecision: bool = False
    broker_mutation: bool = False
    live: bool = False
    production: bool = False
    real_capital: bool = False
    certification_claimed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.protocol,
            CiboSingleAccountMaximumCapabilityProtocol,
        ):
            raise CiboCapitalManagementError(
                "maximum-capability run requires canonical protocol"
            )
        if not self.account_identity:
            raise CiboCapitalManagementError(
                "maximum-capability account identity is required"
            )
        for name in (
            "opportunity_decision_count",
            "sovereign_runtime_evaluation_count",
            "full_semantic_decision_count",
            "account_reset_count",
            "economic_era_reset_count",
            "settled_operation_count",
            "qore_risk_reduce_count",
            "qore_risk_reject_count",
            "compound_reinvestment_count",
            "portfolio_compound_reinvestment_count",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"maximum-capability {name} must be non-negative int"
                )
        if self.opportunity_decision_count <= 0:
            raise CiboCapitalManagementError(
                "maximum-capability run requires at least one decision"
            )
        if self.sovereign_runtime_evaluation_count != self.opportunity_decision_count:
            raise CiboCapitalManagementError(
                "every opportunity must be evaluated by sovereign CIBO"
            )
        if self.full_semantic_decision_count != self.opportunity_decision_count:
            raise CiboCapitalManagementError(
                "every opportunity must consume full causal cognitive semantics"
            )
        if self.account_reset_count != 0 or self.economic_era_reset_count != 0:
            raise CiboCapitalManagementError(
                "single-account maximum-capability run cannot reset capital"
            )
        if tuple(self.trader_ids_observed) != self.protocol.trader_ids:
            raise CiboCapitalManagementError(
                "maximum-capability result must cover exact canonical seven Traders"
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
                    f"maximum-capability {name} must be finite non-negative Decimal"
                )
        if self.peak_capital_usd < max(
            self.protocol.initial_capital_usd,
            self.ending_capital_usd,
        ):
            raise CiboCapitalManagementError(
                "maximum-capability peak capital identity drift"
            )
        if self.maximum_drawdown_usd > self.peak_capital_usd:
            raise CiboCapitalManagementError(
                "maximum-capability drawdown exceeds peak capital"
            )
        for name in (
            "outcome_used_for_predecision",
            "broker_mutation",
            "live",
            "production",
            "real_capital",
            "certification_claimed",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"maximum-capability {name} must be bool"
                )
        if any(
            (
                self.outcome_used_for_predecision,
                self.broker_mutation,
                self.live,
                self.production,
                self.real_capital,
                self.certification_claimed,
            )
        ):
            raise CiboCapitalManagementError(
                "maximum-capability run governance contamination"
            )

    @property
    def capital_multiple(self) -> Decimal:
        with localcontext() as context:
            context.prec = 80
            return self.ending_capital_usd / self.protocol.initial_capital_usd

    @property
    def maximum_drawdown_fraction_of_peak(self) -> Decimal:
        if self.peak_capital_usd == 0:
            return Decimal(0)
        with localcontext() as context:
            context.prec = 80
            return self.maximum_drawdown_usd / self.peak_capital_usd

    @property
    def geometric_growth_per_settled_operation(self) -> Decimal | None:
        """Return geometric per-operation growth when representable by Decimal.

        This is diagnostic only. It is never an optimization target.
        """

        if self.settled_operation_count <= 0 or self.ending_capital_usd <= 0:
            return None
        try:
            multiple = self.capital_multiple
            # Decimal power with a fractional exponent is implementation
            # dependent. Float is used only for this diagnostic scalar.
            value = float(multiple) ** (1.0 / self.settled_operation_count) - 1.0
            return Decimal(str(value))
        except (OverflowError, ValueError, InvalidOperation):
            return None


DEFAULT_CIBO_SINGLE_ACCOUNT_MAXIMUM_CAPABILITY_PROTOCOL = (
    CiboSingleAccountMaximumCapabilityProtocol()
)
