"""Causal account-state builder for the single-account CIBO ceiling replay.

This module turns one chronological account state plus one simultaneous
opportunity epoch into the canonical Full Economic Twin consumed by sovereign
CIBO.  It does not select trades, inspect outcomes or mutate a broker.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10KnownCapitalOption,
    build_genc10_observed_twin,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
    PortfolioAllocationReservation,
    PortfolioAllocationReservationState,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    CiboCompoundCycleState,
    initialize_compound_cycle,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboCapitalVelocityState,
    CiboIdleCapitalClass,
    CiboObservedEconomicTwin,
    CiboObservedOpportunityState,
    CiboObservedPortfolioState,
    CiboObservedPositionState,
)
from qore.infrastructure.cibo_instrument_capability_registry import (
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
    build_integrated_capital_truth,
)


_INITIAL_CAPITAL_USD = Decimal("60")


def _sha(*values: object) -> str:
    raw = json.dumps(
        values,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _ratio(value: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal(0)
    return min(Decimal(1), max(Decimal(0), value / total))


@dataclass(frozen=True, slots=True)
class CiboCeilingCapacityReservation:
    signal_fingerprint: str
    trader_id: TraderLineage
    qore_symbol: str
    stop_risk_usd: Decimal
    margin_usd: Decimal

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "ceiling reservation identity is required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "ceiling reservation trader must be canonical"
            )
        for name in ("stop_risk_usd", "margin_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"ceiling reservation {name} must be finite positive Decimal"
                )


@dataclass(frozen=True, slots=True)
class CiboCeilingOpenExposure:
    signal_fingerprint: str
    trader_id: TraderLineage
    qore_symbol: str
    side: str
    entry_at: datetime
    volume: Decimal
    stop_risk_usd: Decimal
    margin_usd: Decimal
    provider_cost_usd: Decimal
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    entry_expected_net_value_usd: Decimal
    entry_expected_capital_minutes: Decimal
    expectation_evidence_sha256: str

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "ceiling exposure identity is required"
            )
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "ceiling exposure trader must be canonical"
            )
        if self.side not in {"long", "short"}:
            raise CiboCapitalManagementError(
                "ceiling exposure side must be long/short"
            )
        if self.entry_at.tzinfo is None or self.entry_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "ceiling exposure entry time must be aware"
            )
        for name in (
            "volume",
            "stop_risk_usd",
            "margin_usd",
            "provider_cost_usd",
            "entry_price",
            "structural_stop",
            "technical_target",
            "entry_expected_net_value_usd",
            "entry_expected_capital_minutes",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"ceiling exposure {name} must be finite Decimal"
                )
        if (
            self.volume <= 0
            or self.stop_risk_usd <= 0
            or self.margin_usd <= 0
            or self.provider_cost_usd < 0
            or self.entry_expected_capital_minutes <= 0
        ):
            raise CiboCapitalManagementError(
                "ceiling exposure economic geometry invalid"
            )
        if (
            not self.expectation_evidence_sha256.startswith("sha256:")
            or len(self.expectation_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "ceiling exposure expectation evidence invalid"
            )


@dataclass(frozen=True, slots=True)
class CiboCeilingOpportunityEvidence:
    opportunity: TraderOpportunityEnvelope
    expected_net_value_usd: Decimal
    expected_capital_minutes: Decimal
    provider_cost_per_volume_usd: Decimal
    expectation_evidence_sha256: str
    expectation_basis: CausalExpectationBasis = (
        CausalExpectationBasis.CURRENT_STATE_FORECAST
    )
    context_allowed: bool = True
    provider_viable: bool = True
    capital_source_eligible: bool = True
    uncertainty_penalty_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if not isinstance(self.opportunity, TraderOpportunityEnvelope):
            raise CiboCapitalManagementError(
                "ceiling opportunity evidence requires canonical opportunity"
            )
        for name in (
            "expected_net_value_usd",
            "expected_capital_minutes",
            "provider_cost_per_volume_usd",
            "uncertainty_penalty_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"ceiling opportunity {name} must be finite Decimal"
                )
        if (
            self.expected_capital_minutes <= 0
            or self.provider_cost_per_volume_usd < 0
            or self.uncertainty_penalty_usd < 0
        ):
            raise CiboCapitalManagementError(
                "ceiling opportunity economics invalid"
            )
        if type(self.expectation_basis) is not CausalExpectationBasis:
            raise CiboCapitalManagementError(
                "ceiling opportunity expectation basis must be canonical"
            )
        for name in (
            "context_allowed",
            "provider_viable",
            "capital_source_eligible",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"ceiling opportunity {name} must be bool"
                )
        if (
            not self.expectation_evidence_sha256.startswith("sha256:")
            or len(self.expectation_evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "ceiling opportunity expectation evidence invalid"
            )


@dataclass(frozen=True, slots=True)
class CiboCeilingAccountState:
    account_identity: CiboAccountCapitalIdentity
    compound_state: CiboCompoundCycleState
    source_ledger: CapitalSourceLedger
    realized_profit_bindings: tuple[
        RealizedProfitEquivalenceBinding, ...
    ] = ()
    open_exposures: tuple[CiboCeilingOpenExposure, ...] = ()
    capacity_reservations: tuple[CiboCeilingCapacityReservation, ...] = ()
    peak_realized_capital_usd: Decimal = _INITIAL_CAPITAL_USD
    released_stop_risk_usd: Decimal = Decimal(0)
    released_margin_usd: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if self.compound_state.account_identity != self.account_identity:
            raise CiboCapitalManagementError(
                "ceiling account/compound identity drift"
            )
        if (
            self.peak_realized_capital_usd
            < self.compound_state.closing_realized_capital_usd
        ):
            raise CiboCapitalManagementError(
                "ceiling account peak is below current realized capital"
            )
        open_signals = tuple(
            item.signal_fingerprint for item in self.open_exposures
        )
        reserved_signals = tuple(
            item.signal_fingerprint for item in self.capacity_reservations
        )
        all_signals = open_signals + reserved_signals
        if len(all_signals) != len(set(all_signals)):
            raise CiboCapitalManagementError(
                "ceiling account has duplicate open/reserved exposure"
            )

    @property
    def realized_capital_usd(self) -> Decimal:
        return self.compound_state.closing_realized_capital_usd


@dataclass(frozen=True, slots=True)
class CiboCeilingEpochState:
    account: CiboCeilingAccountState
    twin: CiboObservedEconomicTwin
    capital: CiboCapitalState


def initialize_ceiling_account_state(
    *,
    account_identity: CiboAccountCapitalIdentity,
) -> CiboCeilingAccountState:
    t19 = PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=_INITIAL_CAPITAL_USD,
        total_margin_capacity_usd=_INITIAL_CAPITAL_USD,
        concentration_limit_by_group=(),
    )
    cycle = initialize_compound_cycle(
        account_identity=account_identity,
        opening_original_base_usd=_INITIAL_CAPITAL_USD,
        t19_ledger=t19,
    )
    source = CapitalSourceLedger().add_source(
        source_id="cibo:assigned-original-base",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        proven_amount_usd=_INITIAL_CAPITAL_USD,
    )
    return CiboCeilingAccountState(
        account_identity=account_identity,
        compound_state=cycle,
        source_ledger=source,
    )


def build_ceiling_epoch_state(
    *,
    account: CiboCeilingAccountState,
    captured_at: datetime,
    expires_at: datetime,
    opportunities: tuple[CiboCeilingOpportunityEvidence, ...],
    total_stop_risk_capacity_usd: Decimal | None = None,
    total_margin_capacity_usd: Decimal | None = None,
    concentration_utilization: Decimal = Decimal(0),
    correlation_utilization: Decimal = Decimal(0),
) -> CiboCeilingEpochState:
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "ceiling epoch captured_at must be aware"
        )
    if (
        expires_at.tzinfo is None
        or expires_at.utcoffset() is None
        or expires_at <= captured_at
    ):
        raise CiboCapitalManagementError(
            "ceiling epoch expiry must follow capture"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "ceiling epoch requires simultaneous opportunities"
        )
    if len(
        {item.opportunity.signal_fingerprint for item in opportunities}
    ) != len(opportunities):
        raise CiboCapitalManagementError(
            "ceiling epoch opportunity signals must be unique"
        )

    realized = account.realized_capital_usd
    stop_capacity = (
        realized
        if total_stop_risk_capacity_usd is None
        else total_stop_risk_capacity_usd
    )
    margin_capacity = (
        realized
        if total_margin_capacity_usd is None
        else total_margin_capacity_usd
    )
    for value, name in (
        (stop_capacity, "stop capacity"),
        (margin_capacity, "margin capacity"),
        (concentration_utilization, "concentration utilization"),
        (correlation_utilization, "correlation utilization"),
    ):
        if (
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
        ):
            raise CiboCapitalManagementError(
                f"ceiling epoch {name} must be finite non-negative Decimal"
            )
    if concentration_utilization > 1 or correlation_utilization > 1:
        raise CiboCapitalManagementError(
            "ceiling epoch portfolio utilization must be in [0,1]"
        )

    reservations = tuple(
        PortfolioAllocationReservation(
            signal_fingerprint=item.signal_fingerprint,
            trader_id=item.trader_id,
            qore_symbol=item.qore_symbol,
            stop_risk_usd=item.stop_risk_usd,
            margin_usd=item.margin_usd,
            concentration_group=item.qore_symbol,
            concentration_risk_usd=item.stop_risk_usd,
            state=PortfolioAllocationReservationState.ACTIVE,
        )
        for item in (
            tuple(account.open_exposures)
            + tuple(account.capacity_reservations)
        )
    )
    t19 = PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=stop_capacity,
        total_margin_capacity_usd=margin_capacity,
        concentration_limit_by_group=(),
        reservations=reservations,
    )
    cycle = replace(account.compound_state, t19_ledger=t19)
    account = replace(account, compound_state=cycle)

    truth = build_integrated_capital_truth(
        account_identity=account.account_identity,
        source_ledger=account.source_ledger,
        compound_state=cycle,
        realized_profit_bindings=account.realized_profit_bindings,
    )
    provider_registry = ProviderInstrumentCapabilityRegistry(
        account_identity=account.account_identity,
        entries=(),
        captured_at=captured_at,
    )

    observed_opportunities: list[CiboObservedOpportunityState] = []
    known_options: list[Genc10KnownCapitalOption] = []
    for row in opportunities:
        opportunity = row.opportunity
        minimum_volume = minimum_seed_volume(opportunity)
        stop_risk = minimum_volume * opportunity.stop_loss_per_volume
        margin = minimum_volume * opportunity.margin_per_volume
        provider_cost = minimum_volume * row.provider_cost_per_volume_usd
        provider_cap = int(
            (
                opportunity.maximum_volume / minimum_volume
            ).to_integral_value(rounding=ROUND_FLOOR)
        )
        maximum_multiplier = max(0, min(4, provider_cap))
        option_id = "ceiling:" + opportunity.signal_fingerprint
        evidence_sha = _sha(
            opportunity.signal_fingerprint,
            captured_at,
            row.expectation_evidence_sha256,
        )
        observed = CiboObservedOpportunityState(
            option_id=option_id,
            trader_id=opportunity.trader_id.value,
            qore_symbol=opportunity.qore_symbol,
            known_at=captured_at,
            earliest_action_at=captured_at,
            expires_at=expires_at,
            requested_capital_usd=stop_risk,
            expected_net_value_usd=row.expected_net_value_usd,
            expected_capital_minutes=row.expected_capital_minutes,
            stop_risk_usd=stop_risk,
            margin_usd=margin,
            provider_cost_usd=provider_cost,
            uncertainty_penalty=row.uncertainty_penalty_usd,
            context_allowed=row.context_allowed,
            provider_viable=row.provider_viable,
            capital_source_eligible=row.capital_source_eligible,
            evidence_sha256=evidence_sha,
            expectation_basis=row.expectation_basis,
            maximum_multiplier=maximum_multiplier,
            future_outcome_used=False,
        )
        observed_opportunities.append(observed)
        known_options.append(
            Genc10KnownCapitalOption(
                option_id=option_id,
                known_at=captured_at,
                earliest_action_at=captured_at,
                expires_at=expires_at,
                requested_capital_usd=stop_risk,
                stop_risk_usd=stop_risk,
                margin_usd=margin,
                evidence_sha256=evidence_sha,
            )
        )

    capital_twin = build_genc10_observed_twin(
        twin_id="cibo-ceiling:" + captured_at.isoformat(),
        captured_at=captured_at,
        compound_state=cycle,
        capital_truth=truth,
        source_ledger=account.source_ledger,
        provider_registry=provider_registry,
        known_options=tuple(known_options),
    )
    positions = tuple(
        CiboObservedPositionState(
            signal_fingerprint=item.signal_fingerprint,
            qore_symbol=item.qore_symbol,
            side=item.side,
            entry_at=item.entry_at,
            observed_at=captured_at,
            current_volume=item.volume,
            current_stop_risk_usd=item.stop_risk_usd,
            current_margin_usd=item.margin_usd,
            released_stop_risk_usd=Decimal(0),
            released_margin_usd=Decimal(0),
            remaining_reward_r=Decimal(0),
            provider_cost_usd=item.provider_cost_usd,
            entry_price=item.entry_price,
            structural_stop=item.structural_stop,
            technical_target=item.technical_target,
            current_mark_price=None,
            market_state_observed_at=None,
            mark_to_market_identified=False,
            entry_expected_net_value_usd=item.entry_expected_net_value_usd,
            entry_expected_capital_minutes=item.entry_expected_capital_minutes,
            expectation_evidence_sha256=item.expectation_evidence_sha256,
            remaining_reward_identified=False,
            expected_continuation_net_value_usd=Decimal(0),
            expected_remaining_capital_minutes=Decimal(1),
            release_cost_usd=Decimal(0),
            uncertainty_penalty=Decimal(0),
            releasable=True,
            continuation_value_identified=False,
            future_outcome_used=False,
            structural_stop_widened=False,
        )
        for item in account.open_exposures
    )
    portfolio = CiboObservedPortfolioState(
        observed_at=captured_at,
        active_position_ids=tuple(
            item.signal_fingerprint for item in account.open_exposures
        ),
        opportunity_ids=tuple(
            item.option_id for item in observed_opportunities
        ),
        concentration_utilization=concentration_utilization,
        correlation_utilization=correlation_utilization,
        reserved_stop_risk_usd=Decimal(0),
        reserved_margin_usd=Decimal(0),
    )
    velocity = CiboCapitalVelocityState(
        observed_at=captured_at,
        released_stop_risk_usd=account.released_stop_risk_usd,
        released_margin_usd=account.released_margin_usd,
        waiting_stop_risk_usd=Decimal(0),
        waiting_margin_usd=Decimal(0),
        oldest_release_age_minutes=Decimal(0),
        idle_classification=CiboIdleCapitalClass.OPTIONALITY_RESERVE,
    )
    twin = CiboObservedEconomicTwin(
        twin_id=capital_twin.twin_id,
        captured_at=captured_at,
        capital_twin=capital_twin,
        positions=positions,
        opportunities=tuple(observed_opportunities),
        portfolio=portfolio,
        velocity=velocity,
        cognitive_constraints=(
            ("capital_intensity_cap", "4"),
            ("native_max_required", "true"),
        ),
        provider_state=tuple(
            sorted(
                {
                    (
                        item.opportunity.qore_symbol,
                        "COUNTERFACTUAL_PROVIDER_ECONOMICS",
                    )
                    for item in opportunities
                }
            )
        ),
        allocation_authority=False,
        risk_authority=False,
        execution_authority=False,
        future_outcome_used=False,
    )
    compound_value = truth.realized_profit_nonconsumed_usd
    deployable_profit_capacity = sum(
        (
            item.available_usd
            for item in account.source_ledger.accounts
            if item.source is CapitalSource.REALIZED_PROFIT
        ),
        Decimal(0),
    )
    if deployable_profit_capacity > compound_value:
        raise CiboCapitalManagementError(
            "ceiling deployable realized-profit capacity exceeds economic value"
        )
    capital = CiboCapitalState(
        assigned_capital_usd=realized,
        hard_risk_headroom_usd=capital_twin.stop_risk_headroom_usd,
        margin_headroom_usd=capital_twin.margin_headroom_usd,
        base_capital_at_risk_usd=cycle.current_original_base_usd,
        realized_net_profit_usd=compound_value,
        protected_open_economic_floor_usd=(
            cycle.floor_ledger.total_floor_usd
        ),
        proven_self_financing_capacity_usd=deployable_profit_capacity,
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )
    return CiboCeilingEpochState(
        account=account,
        twin=twin,
        capital=capital,
    )
