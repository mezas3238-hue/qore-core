"""Historical research projection for the CIBO single-account ceiling replay.

The historical ceiling ledger intentionally does not fabricate broker deal ids
or pretend to be GEN-C1 certified settlement evidence.  This module projects
that non-certifying, chronological USD60 account state into the read-only
GEN-C10 / Full Economic Twin contracts consumed by Native MAX.

No settlement outcome is accepted by this API.  Open positions are supplied
only from already-authorized deployments and their causal entry evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal, localcontext

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10EconomicBucket,
    Genc10KnownCapitalOption,
    Genc10ObservedCapitalTwin,
    Genc10SourceCapacityState,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalCapacityDimension,
    CiboCapitalManagementError,
    CiboCapitalState,
    minimum_seed_volume,
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
    CapabilityStatus,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpenExposure,
    CiboCeilingOpportunityEvidence,
)
from qore.infrastructure.cibo_single_account_historical_capital_ledger import (
    CiboHistoricalResearchCapitalState,
)


def _sha(label: str, payload: object) -> str:
    raw = json.dumps(
        {
            "label": label,
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _exact_add(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return left + right


def _exact_mul(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return left * right


def _exact_div(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return left / right


def _money(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCapitalManagementError(
            f"historical ceiling projection {name} must be finite non-negative"
        )


@dataclass(frozen=True, slots=True)
class CiboHistoricalCeilingEpochState:
    capital_twin: Genc10ObservedCapitalTwin
    twin: CiboObservedEconomicTwin
    capital: CiboCapitalState


def _historical_payload(
    state: CiboHistoricalResearchCapitalState,
) -> dict[str, object]:
    return {
        "original_base_proven_usd": format(
            state.original_base_proven_usd,
            "f",
        ),
        "original_base_consumed_usd": format(
            state.original_base_consumed_usd,
            "f",
        ),
        "original_base_reserved_usd": format(
            state.original_base_reserved_usd,
            "f",
        ),
        "profit_generations": [
            {
                "generation": item.generation,
                "proven_usd": format(item.proven_usd, "f"),
                "consumed_usd": format(item.consumed_usd, "f"),
                "reserved_usd": format(item.reserved_usd, "f"),
            }
            for item in state.profit_generations
        ],
        "open_deployments": [
            {
                "authorization_id": item.authorization_id,
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id.value,
                "authorized_at": item.authorized_at.isoformat(),
                "authorized_volume": format(item.authorized_volume, "f"),
                "authorized_stop_risk_usd": format(
                    item.authorized_stop_risk_usd,
                    "f",
                ),
                "authorized_margin_usd": format(
                    item.authorized_margin_usd,
                    "f",
                ),
                "provider_cost_usd": format(
                    item.provider_cost_usd,
                    "f",
                ),
            }
            for item in state.open_deployments
        ],
        "settlement_sha256s": state.settlement_sha256s,
        "peak_realized_capital_usd": format(
            state.peak_realized_capital_usd,
            "f",
        ),
        "non_certifying_research": state.non_certifying_research,
    }


def _validate_open_exposures(
    *,
    state: CiboHistoricalResearchCapitalState,
    open_exposures: tuple[CiboCeilingOpenExposure, ...],
) -> None:
    if any(
        not isinstance(item, CiboCeilingOpenExposure)
        for item in open_exposures
    ):
        raise CiboCapitalManagementError(
            "historical ceiling open exposures must be canonical"
        )
    deployments = {
        item.signal_fingerprint: item for item in state.open_deployments
    }
    exposures = {
        item.signal_fingerprint: item for item in open_exposures
    }
    if set(deployments) != set(exposures):
        raise CiboCapitalManagementError(
            "historical ceiling deployment/exposure surface drift"
        )
    for signal, deployment in deployments.items():
        exposure = exposures[signal]
        if (
            exposure.trader_id is not deployment.trader_id
            or exposure.volume != deployment.authorized_volume
            or exposure.stop_risk_usd
            != deployment.authorized_stop_risk_usd
            or exposure.margin_usd != deployment.authorized_margin_usd
            or exposure.provider_cost_usd != deployment.provider_cost_usd
            or exposure.entry_at < deployment.authorized_at
        ):
            raise CiboCapitalManagementError(
                "historical ceiling deployment/exposure economics drift"
            )


def _sum_decimal_exact(values: tuple[Decimal, ...]) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return sum(values, Decimal(0))


def _source_capacities(
    state: CiboHistoricalResearchCapitalState,
) -> tuple[Genc10SourceCapacityState, ...]:
    profit_proven = _sum_decimal_exact(
        tuple(item.proven_usd for item in state.profit_generations)
    )
    profit_consumed = _sum_decimal_exact(
        tuple(item.consumed_usd for item in state.profit_generations)
    )
    profit_reserved = _sum_decimal_exact(
        tuple(item.reserved_usd for item in state.profit_generations)
    )
    return (
        Genc10SourceCapacityState(
            dimension=CapitalCapacityDimension.BASE_RISK_CAPITAL,
            proven=state.original_base_proven_usd,
            available=state.original_base_available_usd,
            reserved=Decimal(0),
            deployed=state.original_base_reserved_usd,
            consumed=state.original_base_consumed_usd,
        ),
        Genc10SourceCapacityState(
            dimension=CapitalCapacityDimension.ECONOMIC_PROFIT_CAPITAL,
            proven=profit_proven,
            available=state.realized_profit_available_usd,
            reserved=Decimal(0),
            deployed=profit_reserved,
            consumed=profit_consumed,
        ),
    )


def _economic_buckets(
    state: CiboHistoricalResearchCapitalState,
) -> tuple[tuple[Genc10EconomicBucket, Decimal], ...]:
    profit_reserved = _sum_decimal_exact(
        tuple(item.reserved_usd for item in state.profit_generations)
    )
    profit_available = state.realized_profit_available_usd
    amounts = {
        bucket: Decimal(0) for bucket in Genc10EconomicBucket
    }
    amounts[Genc10EconomicBucket.ORIGINAL_BASE] = (
        state.original_base_economic_value_usd
    )
    amounts[Genc10EconomicBucket.REALIZED_PROFIT] = profit_available
    amounts[Genc10EconomicBucket.DEPLOYED_COMPOUND_CAPITAL] = (
        profit_reserved
    )
    return tuple((bucket, amounts[bucket]) for bucket in Genc10EconomicBucket)


def build_historical_ceiling_epoch_state(
    *,
    account_identity: CiboAccountCapitalIdentity,
    historical_capital: CiboHistoricalResearchCapitalState,
    captured_at: datetime,
    expires_at: datetime,
    opportunities: tuple[CiboCeilingOpportunityEvidence, ...],
    open_exposures: tuple[CiboCeilingOpenExposure, ...] = (),
    total_stop_risk_capacity_usd: Decimal | None = None,
    total_margin_capacity_usd: Decimal | None = None,
    concentration_utilization: Decimal = Decimal(0),
    correlation_utilization: Decimal = Decimal(0),
) -> CiboHistoricalCeilingEpochState:
    """Project current causal research capital into the Native MAX twin."""

    if not isinstance(account_identity, CiboAccountCapitalIdentity):
        raise CiboCapitalManagementError(
            "historical ceiling projection requires account identity"
        )
    if not isinstance(
        historical_capital,
        CiboHistoricalResearchCapitalState,
    ):
        raise CiboCapitalManagementError(
            "historical ceiling projection requires research capital state"
        )
    if (
        captured_at.tzinfo is None
        or captured_at.utcoffset() is None
        or expires_at.tzinfo is None
        or expires_at.utcoffset() is None
        or expires_at <= captured_at
    ):
        raise CiboCapitalManagementError(
            "historical ceiling projection chronology invalid"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "historical ceiling projection requires opportunities"
        )
    if any(
        not isinstance(item, CiboCeilingOpportunityEvidence)
        for item in opportunities
    ):
        raise CiboCapitalManagementError(
            "historical ceiling projection opportunity must be canonical"
        )
    signals = tuple(
        item.opportunity.signal_fingerprint for item in opportunities
    )
    if len(signals) != len(set(signals)):
        raise CiboCapitalManagementError(
            "historical ceiling projection duplicate opportunity signal"
        )
    _validate_open_exposures(
        state=historical_capital,
        open_exposures=open_exposures,
    )

    realized = historical_capital.realized_capital_usd
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
        _money(value, name)
    if concentration_utilization > 1 or correlation_utilization > 1:
        raise CiboCapitalManagementError(
            "historical ceiling utilization must be in [0,1]"
        )

    used_stop = historical_capital.open_stop_risk_usd
    used_margin = historical_capital.open_margin_usd
    if used_stop > stop_capacity or used_margin > margin_capacity:
        raise CiboCapitalManagementError(
            "historical ceiling open exposure exceeds declared capacity"
        )

    # GEN-C10 enforces exact conservation with Fraction, so compute residual
    # capacity under a precision high enough to preserve long compound decimals.
    with localcontext() as context:
        context.prec = 80
        stop_risk_headroom = stop_capacity - used_stop
        margin_headroom = margin_capacity - used_margin

    observed_opportunities: list[CiboObservedOpportunityState] = []
    known_options: list[Genc10KnownCapitalOption] = []
    for row in opportunities:
        opportunity = row.opportunity
        minimum_volume = minimum_seed_volume(opportunity)
        stop_risk = _exact_mul(
            minimum_volume,
            opportunity.stop_loss_per_volume,
        )
        margin = _exact_mul(
            minimum_volume,
            opportunity.margin_per_volume,
        )
        provider_cost = _exact_mul(
            minimum_volume,
            row.provider_cost_per_volume_usd,
        )
        provider_cap = int(
            _exact_div(
                opportunity.maximum_volume,
                minimum_volume,
            ).to_integral_value(rounding=ROUND_FLOOR)
        )
        maximum_multiplier = max(0, min(4, provider_cap))
        option_id = opportunity.signal_fingerprint
        evidence_sha = _sha(
            "historical-opportunity",
            (
                opportunity.signal_fingerprint,
                captured_at.isoformat(),
                row.expectation_evidence_sha256,
            ),
        )
        observed_opportunities.append(
            CiboObservedOpportunityState(
                option_id=option_id,
                trader_id=opportunity.trader_id.value,
                qore_symbol=opportunity.qore_symbol,
                known_at=captured_at,
                earliest_action_at=captured_at,
                expires_at=expires_at,
                requested_capital_usd=_exact_add(stop_risk, provider_cost),
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
                maximum_multiplier=maximum_multiplier,
                future_outcome_used=False,
            )
        )
        known_options.append(
            Genc10KnownCapitalOption(
                option_id=option_id,
                known_at=captured_at,
                earliest_action_at=captured_at,
                expires_at=expires_at,
                requested_capital_usd=_exact_add(stop_risk, provider_cost),
                stop_risk_usd=stop_risk,
                margin_usd=margin,
                evidence_sha256=evidence_sha,
            )
        )

    historical_payload = _historical_payload(historical_capital)
    capital_twin = Genc10ObservedCapitalTwin(
        twin_id="cibo-ceiling-historical:" + captured_at.isoformat(),
        account_identity=account_identity,
        captured_at=captured_at,
        capital_truth_sha256=_sha(
            "historical-research-capital-truth",
            historical_payload,
        ),
        compound_cycle_sha256=_sha(
            "historical-research-compound-projection",
            historical_payload,
        ),
        source_ledger_sha256=_sha(
            "historical-research-source-projection",
            historical_payload,
        ),
        provider_registry_sha256=_sha(
            "counterfactual-provider-contract",
            tuple(
                sorted(item.opportunity.qore_symbol for item in opportunities)
            ),
        ),
        total_realized_capital_usd=realized,
        original_base_usd=historical_capital.original_base_economic_value_usd,
        compound_economic_value_usd=(
            historical_capital.realized_profit_economic_value_usd
        ),
        protected_floor_usd=Decimal(0),
        policy_protected_floor_usd=Decimal(0),
        broker_guaranteed_floor_usd=Decimal(0),
        economic_buckets=_economic_buckets(historical_capital),
        generation_balances=tuple(
            (
                item.generation,
                item.economic_value_usd,
            )
            for item in historical_capital.profit_generations
            if item.economic_value_usd > 0
        ),
        source_capacities=_source_capacities(historical_capital),
        total_stop_risk_capacity_usd=stop_capacity,
        used_stop_risk_usd=used_stop,
        stop_risk_headroom_usd=stop_risk_headroom,
        total_margin_capacity_usd=margin_capacity,
        used_margin_usd=used_margin,
        margin_headroom_usd=margin_headroom,
        active_deployment_count=len(historical_capital.open_deployments),
        provider_capability_counts=tuple(
            (status, 0) for status in CapabilityStatus
        ),
        known_options=tuple(known_options),
        future_leakage_used=False,
        market_probability_claimed=False,
        productive_authority=False,
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
            entry_expected_capital_minutes=(
                item.entry_expected_capital_minutes
            ),
            expectation_evidence_sha256=(
                item.expectation_evidence_sha256
            ),
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
        for item in open_exposures
    )
    portfolio = CiboObservedPortfolioState(
        observed_at=captured_at,
        active_position_ids=tuple(
            item.signal_fingerprint for item in open_exposures
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
        released_stop_risk_usd=Decimal(0),
        released_margin_usd=Decimal(0),
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
            ("historical_research_projection", "true"),
            ("native_max_required", "true"),
        ),
        provider_state=tuple(
            (
                symbol,
                "COUNTERFACTUAL_PROVIDER_ECONOMICS",
            )
            for symbol in sorted(
                {item.opportunity.qore_symbol for item in opportunities}
            )
        ),
        allocation_authority=False,
        risk_authority=False,
        execution_authority=False,
        future_outcome_used=False,
    )
    profit_economic = historical_capital.realized_profit_economic_value_usd
    with localcontext() as context:
        context.prec = 100
        profit_reserved = sum(
            (
                item.reserved_usd
                for item in historical_capital.profit_generations
            ),
            Decimal(0),
        )
    capital = CiboCapitalState(
        assigned_capital_usd=realized,
        hard_risk_headroom_usd=stop_risk_headroom,
        margin_headroom_usd=margin_headroom,
        base_capital_at_risk_usd=(
            historical_capital.original_base_economic_value_usd
        ),
        realized_net_profit_usd=profit_economic,
        protected_open_economic_floor_usd=Decimal(0),
        proven_self_financing_capacity_usd=profit_economic,
        reserved_expansion_risk_usd=profit_reserved,
        cost_reserve_usd=(
            historical_capital.open_provider_cost_reserve_usd
        ),
    )
    return CiboHistoricalCeilingEpochState(
        capital_twin=capital_twin,
        twin=twin,
        capital=capital,
    )
