"""Read-only Core Compound Portfolio views for CIBO GEN-C3.

Money remains account-local. This module composes the GEN-C1 compound ledger
and GEN-C2 protected-floor ledger into one canonical economic snapshot per
account, then permits a Core-wide analytical view.

The global view cannot transfer, reserve, deploy or release capital. It exists
only to answer where Core's compound capital is, what state it is in, where it
came from, and how much economically usable value remains.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    TraderIdentity,
    canonical_trader_lineage,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.cibo_four_motor_policy import (
    ZERO,
    FourMotorObservation,
    FourMotorPolicyError,
    FourMotorProposal,
)


@dataclass(frozen=True, slots=True)
class CompoundPortfolioAttributionRow:
    account_identity: CiboAccountCapitalIdentity
    origin_trader: TraderIdentity
    generation: int
    state: CompoundCapitalState
    amount_usd: Decimal
    economic_owner: str = "CORE"

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "compound attribution account identity is invalid"
            )
        object.__setattr__(
            self,
            "origin_trader",
            canonical_trader_lineage(
                self.origin_trader,
                field_name="origin_trader",
            ),
        )
        if (
            not isinstance(self.generation, int)
            or isinstance(self.generation, bool)
            or self.generation < 1
        ):
            raise CiboCompoundCapitalError(
                "compound attribution generation must be positive int"
            )
        if type(self.state) is not CompoundCapitalState:
            raise CiboCompoundCapitalError(
                "compound attribution state is invalid"
            )
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd <= 0
        ):
            raise CiboCompoundCapitalError(
                "compound attribution amount must be finite positive"
            )
        if self.economic_owner != "CORE":
            raise CiboCompoundCapitalError(
                "compound attribution cannot transfer economic ownership"
            )


@dataclass(frozen=True, slots=True)
class AccountCoreCompoundPortfolio:
    account_identity: CiboAccountCapitalIdentity
    compound_ledger: CompoundPortfolioLedger
    protected_floor_ledger: ProtectedCapitalFloorLedger
    runtime_authority: bool = False
    cross_account_transfer_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "Core Compound Portfolio account identity is invalid"
            )
        if not isinstance(self.compound_ledger, CompoundPortfolioLedger):
            raise CiboCompoundCapitalError(
                "Core Compound Portfolio compound ledger is invalid"
            )
        if not isinstance(
            self.protected_floor_ledger,
            ProtectedCapitalFloorLedger,
        ):
            raise CiboCompoundCapitalError(
                "Core Compound Portfolio floor ledger is invalid"
            )
        if (
            self.compound_ledger.account_identity != self.account_identity
            or self.protected_floor_ledger.account_identity
            != self.account_identity
        ):
            raise CiboCompoundCapitalError(
                "Core Compound Portfolio cannot mix account domains"
            )
        for name in (
            "runtime_authority",
            "cross_account_transfer_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"Core Compound Portfolio {name} must be bool"
                )
        if self.runtime_authority or self.cross_account_transfer_authority:
            raise CiboCompoundCapitalError(
                "GEN-C3 portfolio view has no capital mutation authority"
            )
        self._validate_floor_binding()

    @property
    def admitted_realized_profit_usd(self) -> Decimal:
        return self.compound_ledger.admitted_realized_profit_usd

    @property
    def current_partition_usd(self) -> Decimal:
        return self.compound_ledger.current_partition_usd

    @property
    def current_economic_value_usd(self) -> Decimal:
        return self.compound_ledger.current_economic_value_usd

    @property
    def protected_floor_usd(self) -> Decimal:
        return self.protected_floor_ledger.total_floor_usd

    @property
    def strategic_reserve_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.STRATEGIC_RESERVE
        )

    @property
    def opportunity_reserve_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.OPPORTUNITY_RESERVE
        )

    @property
    def compoundable_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.COMPOUNDABLE
        )

    @property
    def active_compound_capacity_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY
        )

    @property
    def deployed_compound_capital_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL
        )

    @property
    def released_compound_capital_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.RELEASED_COMPOUND_CAPITAL
        )

    @property
    def consumed_compound_capital_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.CONSUMED
        )

    @property
    def realized_unclassified_profit_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.REALIZED_PROFIT
        )

    @property
    def protected_profit_usd(self) -> Decimal:
        return self.compound_ledger.balance(
            CompoundCapitalState.PROTECTED_PROFIT
        )

    @property
    def attribution(self) -> tuple[CompoundPortfolioAttributionRow, ...]:
        return tuple(
            CompoundPortfolioAttributionRow(
                account_identity=self.account_identity,
                origin_trader=lot.origin_trader,
                generation=lot.generation,
                state=lot.state,
                amount_usd=lot.amount_usd,
            )
            for lot in self.compound_ledger.active_lots
        )

    def _validate_floor_binding(self) -> None:
        retired = {
            item.lot_id: item
            for item in self.compound_ledger.active_lots
            if item.state
            is CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR
        }
        if len(retired) != sum(
            1
            for item in self.compound_ledger.active_lots
            if item.state
            is CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR
        ):
            raise CiboCompoundCapitalError(
                "Core Compound Portfolio duplicate retired lot identity"
            )

        tranche_sources = {
            item.source_compound_lot_id: item
            for item in self.protected_floor_ledger.tranches
        }
        if set(retired) != set(tranche_sources):
            raise CiboCompoundCapitalError(
                "Core Compound Portfolio floor/retired-lot coverage mismatch"
            )
        for lot_id, lot in retired.items():
            tranche = tranche_sources[lot_id]
            if tranche.amount_usd != lot.amount_usd:
                raise CiboCompoundCapitalError(
                    "Core Compound Portfolio floor amount binding drift"
                )


@dataclass(frozen=True, slots=True)
class QoreCoreCompoundPortfolio:
    accounts: tuple[AccountCoreCompoundPortfolio, ...]
    economic_owner: str = "CORE"
    read_only: bool = True
    cross_account_transfer_authority: bool = False
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.accounts, tuple):
            raise CiboCompoundCapitalError(
                "global Compound Portfolio accounts must be tuple"
            )
        if any(
            not isinstance(item, AccountCoreCompoundPortfolio)
            for item in self.accounts
        ):
            raise CiboCompoundCapitalError(
                "global Compound Portfolio account snapshot is invalid"
            )
        identities = tuple(
            (
                item.account_identity.provider_key,
                item.account_identity.account_ref,
                item.account_identity.environment.value,
                item.account_identity.provider_program,
            )
            for item in self.accounts
        )
        if len(identities) != len(set(identities)):
            raise CiboCompoundCapitalError(
                "global Compound Portfolio account domains must be unique"
            )
        if self.economic_owner != "CORE":
            raise CiboCompoundCapitalError(
                "global Compound Portfolio economic owner must remain Core"
            )
        for name in (
            "read_only",
            "cross_account_transfer_authority",
            "runtime_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"global Compound Portfolio {name} must be bool"
                )
        if (
            not self.read_only
            or self.cross_account_transfer_authority
            or self.runtime_authority
        ):
            raise CiboCompoundCapitalError(
                "global Compound Portfolio must remain read-only/no-transfer"
            )

    @property
    def total_admitted_realized_profit_usd(self) -> Decimal:
        return sum(
            (
                item.admitted_realized_profit_usd
                for item in self.accounts
            ),
            Decimal(0),
        )

    @property
    def total_current_economic_value_usd(self) -> Decimal:
        return sum(
            (
                item.current_economic_value_usd
                for item in self.accounts
            ),
            Decimal(0),
        )

    @property
    def total_protected_floor_usd(self) -> Decimal:
        return sum(
            (item.protected_floor_usd for item in self.accounts),
            Decimal(0),
        )

    @property
    def attribution(self) -> tuple[CompoundPortfolioAttributionRow, ...]:
        return tuple(
            row
            for account in self.accounts
            for row in account.attribution
        )

    def attributed_value_by_trader(
        self,
    ) -> tuple[tuple[TraderIdentity, Decimal], ...]:
        totals: dict[TraderIdentity, Decimal] = {}
        for row in self.attribution:
            totals[row.origin_trader] = (
                totals.get(row.origin_trader, Decimal(0))
                + row.amount_usd
            )
        return tuple(
            sorted(
                totals.items(),
                key=lambda item: item[0].value,
            )
        )



def propose_p0_portfolio_vote(observation: FourMotorObservation) -> FourMotorProposal:
    """Risk-backed source USD with correlated/simultaneous-stop constraints.

    Research policy only: global <= 15% NAV, correlated cluster <= 7.5%,
    Trader <= 10%. Not asserted to be FundedNext provider rules.
    """
    if not isinstance(observation, FourMotorObservation):
        raise FourMotorPolicyError("canonical observation required")
    nav = observation.qore_nav_usd
    if observation.research_scenario_only:
        # Research-only: no arbitrary 15%/7.5%/10% quota.
        # QDLE still imposes source solvency, per-trade 5%, and broker grid.
        cap = min(observation.source_available_usd,
                  observation.risk_cash_remaining_usd)
        return FourMotorProposal(
            "PORTFOLIO_COMPOUND", observation,
            {"approved_source_funds_usd": str(cap)},
            ("PAPER_CONCURRENT_RISK_OBSERVED",
             "PAPER_NO_ARBITRARY_GLOBAL_CORRELATED_TRADER_QUOTAS",
             "PHYSICAL_SOURCE_AND_QDLE_MAX_5PCT_STILL_BIND"),
        )
    caps = {
        "SOURCE": observation.source_available_usd,
        "UNPROTECTED": observation.risk_cash_remaining_usd,
        "GLOBAL_STOPS": max(ZERO, nav * Decimal("0.15")
                            - observation.total_open_stop_risk_usd
                            - observation.risk_reservations_usd),
        "CORRELATED": max(ZERO, nav * Decimal("0.075")
                          - observation.correlated_open_stop_risk_usd
                          - observation.risk_reservations_usd),
        "TRADER": max(ZERO, nav * Decimal("0.10")
                      - observation.trader_open_stop_risk_usd
                      - observation.risk_reservations_usd),
    }
    cap = min(caps.values())
    constraints = tuple(sorted(k for k, v in caps.items() if v == cap))
    reasons = ("ACCOUNT_LOCAL_SOURCE_LANE_NO_TRANSFER",
               "SIMULTANEOUS_STOP_RISK_BUDGET",
               "CORRELATED_CLUSTER_AND_TRADER_CONCENTRATION",
               "BINDING_" + "_".join(constraints))
    return FourMotorProposal("PORTFOLIO_COMPOUND", observation,
                             {"approved_source_funds_usd": str(cap)}, reasons)
