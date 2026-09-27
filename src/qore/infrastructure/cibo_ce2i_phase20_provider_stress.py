"""Counterfactual provider-economic stress for CIBO Phase 20.

Exact historical provider economics are absent for the sealed Phase-18
population. This module therefore permits permanently-labelled counterfactual
robustness experiments using an explicit provider observation plus predeclared
non-improving stress parameters.

It MUST NOT be used to claim historical provider economics, historical causal
decision replay, LIVE authority, Risk authority or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    CiboReplayCausalTrade,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)


def _finite_nonnegative(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise CiboCapitalManagementError(
            f"{name} must be finite non-negative Decimal"
        )


def _finite_positive(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise CiboCapitalManagementError(
            f"{name} must be finite positive Decimal"
        )


def _finite_at_least_one(value: Decimal, *, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 1:
        raise CiboCapitalManagementError(
            f"{name} must be finite Decimal >= 1"
        )


class Phase20ProviderStressStatus(StrEnum):
    EXECUTABLE = "EXECUTABLE"
    FAIL_CLOSED_PROVIDER_CONSTRAINT = "FAIL_CLOSED_PROVIDER_CONSTRAINT"


@dataclass(frozen=True, slots=True)
class Phase20ProviderStressScenario:
    scenario_id: str
    evidence_id: str
    minimum_spread_ticks: Decimal
    spread_multiplier: Decimal
    commission_multiplier: Decimal
    minimum_slippage_reserve_per_volume_usd: Decimal
    margin_multiplier: Decimal
    broker_risk_buffer: Decimal
    minimum_volume_floor: Decimal | None = None
    maximum_volume_cap: Decimal | None = None
    available_liquidity_volume_cap: Decimal | None = None
    execution_delay_ms_floor: Decimal = Decimal("0")
    historical_provider_economics_claimed: bool = False
    outcome_tuned: bool = False
    policy_pass_tuned: bool = False

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.evidence_id:
            raise CiboCapitalManagementError(
                "Phase 20 provider stress identity is required"
            )
        _finite_nonnegative(
            self.minimum_spread_ticks,
            name="minimum_spread_ticks",
        )
        _finite_nonnegative(
            self.minimum_slippage_reserve_per_volume_usd,
            name="minimum_slippage_reserve_per_volume_usd",
        )
        _finite_nonnegative(
            self.execution_delay_ms_floor,
            name="execution_delay_ms_floor",
        )
        for name in (
            "spread_multiplier",
            "commission_multiplier",
            "margin_multiplier",
            "broker_risk_buffer",
        ):
            _finite_at_least_one(getattr(self, name), name=name)
        for name in ("minimum_volume_floor", "maximum_volume_cap"):
            value = getattr(self, name)
            if value is not None:
                _finite_positive(value, name=name)
        if self.available_liquidity_volume_cap is not None:
            _finite_nonnegative(
                self.available_liquidity_volume_cap,
                name="available_liquidity_volume_cap",
            )
        if (
            self.historical_provider_economics_claimed
            or self.outcome_tuned
            or self.policy_pass_tuned
        ):
            raise CiboCapitalManagementError(
                "Phase 20 provider stress governance drift"
            )


@dataclass(frozen=True, slots=True)
class Phase20CounterfactualProviderEconomics:
    scenario_id: str
    provider_key: str
    provider_symbol: str
    source_observed_at_iso: str
    stressed_spread_ticks: Decimal
    stressed_spread_cost_per_volume_usd: Decimal
    stressed_commission_per_volume_usd: Decimal
    stressed_slippage_reserve_per_volume_usd: Decimal
    stressed_execution_cost_per_volume_usd: Decimal
    stressed_margin_per_volume_usd: Decimal
    stressed_minimum_volume: Decimal
    stressed_maximum_volume: Decimal
    minimum_executable_volume: Decimal
    available_liquidity_volume: Decimal
    stressed_execution_delay_ms: Decimal
    tick_size: Decimal
    tick_value: Decimal
    volume_step: Decimal
    broker_risk_buffer: Decimal
    source_evidence_id: str
    historical_provider_economics_claimed: bool = False
    historical_causality_claimed: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.historical_provider_economics_claimed
            or self.historical_causality_claimed
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "counterfactual provider stress cannot claim historical or trading authority"
            )


@dataclass(frozen=True, slots=True)
class Phase20CounterfactualOpportunity:
    opportunity: TraderOpportunityEnvelope
    economics: Phase20CounterfactualProviderEconomics
    research_only: bool = True
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            not self.research_only
            or self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase 20 counterfactual opportunity governance drift"
            )


@dataclass(frozen=True, slots=True)
class Phase20ProviderStressEvaluation:
    scenario_id: str
    status: Phase20ProviderStressStatus
    reason: str
    minimum_executable_volume: Decimal
    effective_maximum_volume: Decimal
    available_liquidity_volume: Decimal
    result: Phase20CounterfactualOpportunity | None

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.reason:
            raise CiboCapitalManagementError(
                "Phase 20 provider stress evaluation identity is required"
            )
        for name in (
            "minimum_executable_volume",
            "effective_maximum_volume",
            "available_liquidity_volume",
        ):
            _finite_nonnegative(getattr(self, name), name=name)
        if self.status is Phase20ProviderStressStatus.EXECUTABLE:
            if self.result is None:
                raise CiboCapitalManagementError(
                    "executable provider stress requires a result"
                )
        elif self.result is not None:
            raise CiboCapitalManagementError(
                "failed provider stress cannot expose an executable result"
            )


def _minimum_executable_volume(
    *,
    minimum_volume: Decimal,
    volume_step: Decimal,
    minimum_execution_steps: int,
) -> Decimal:
    raw = minimum_volume * Decimal(minimum_execution_steps)
    steps = (raw / volume_step).to_integral_value(rounding=ROUND_CEILING)
    return steps * volume_step


def evaluate_phase20_counterfactual_provider_stress(
    *,
    causal: CiboReplayCausalTrade,
    observation: ProviderEconomicObservation,
    scenario: Phase20ProviderStressScenario,
) -> Phase20ProviderStressEvaluation:
    """Evaluate one explicit non-historical provider stress scenario."""

    if not isinstance(causal, CiboReplayCausalTrade):
        raise CiboCapitalManagementError(
            "causal must be CiboReplayCausalTrade"
        )
    if not isinstance(observation, ProviderEconomicObservation):
        raise CiboCapitalManagementError(
            "observation must be ProviderEconomicObservation"
        )
    if not isinstance(scenario, Phase20ProviderStressScenario):
        raise CiboCapitalManagementError(
            "scenario must be Phase20ProviderStressScenario"
        )
    if causal.qore_symbol != observation.qore_symbol:
        raise CiboCapitalManagementError(
            "counterfactual provider stress QORE symbol mismatch"
        )

    stressed_minimum_volume = max(
        observation.minimum_volume,
        scenario.minimum_volume_floor or observation.minimum_volume,
    )
    stressed_maximum_volume = min(
        observation.maximum_volume,
        scenario.maximum_volume_cap or observation.maximum_volume,
    )
    available_liquidity_volume = min(
        stressed_maximum_volume,
        (
            scenario.available_liquidity_volume_cap
            if scenario.available_liquidity_volume_cap is not None
            else stressed_maximum_volume
        ),
    )
    minimum_executable_volume = _minimum_executable_volume(
        minimum_volume=stressed_minimum_volume,
        volume_step=observation.volume_step,
        minimum_execution_steps=causal.minimum_execution_steps,
    )

    if stressed_maximum_volume < stressed_minimum_volume:
        return Phase20ProviderStressEvaluation(
            scenario_id=scenario.scenario_id,
            status=Phase20ProviderStressStatus.FAIL_CLOSED_PROVIDER_CONSTRAINT,
            reason="MAXIMUM_VOLUME_BELOW_STRESSED_MINIMUM",
            minimum_executable_volume=minimum_executable_volume,
            effective_maximum_volume=stressed_maximum_volume,
            available_liquidity_volume=available_liquidity_volume,
            result=None,
        )
    if minimum_executable_volume > stressed_maximum_volume:
        return Phase20ProviderStressEvaluation(
            scenario_id=scenario.scenario_id,
            status=Phase20ProviderStressStatus.FAIL_CLOSED_PROVIDER_CONSTRAINT,
            reason="MINIMUM_EXECUTION_EXCEEDS_STRESSED_MAXIMUM",
            minimum_executable_volume=minimum_executable_volume,
            effective_maximum_volume=stressed_maximum_volume,
            available_liquidity_volume=available_liquidity_volume,
            result=None,
        )
    if available_liquidity_volume < minimum_executable_volume:
        return Phase20ProviderStressEvaluation(
            scenario_id=scenario.scenario_id,
            status=Phase20ProviderStressStatus.FAIL_CLOSED_PROVIDER_CONSTRAINT,
            reason="LIQUIDITY_BELOW_MINIMUM_EXECUTABLE",
            minimum_executable_volume=minimum_executable_volume,
            effective_maximum_volume=stressed_maximum_volume,
            available_liquidity_volume=available_liquidity_volume,
            result=None,
        )

    observed_spread_ticks = (
        observation.ask - observation.bid
    ) / observation.tick_size
    stressed_spread_ticks = max(
        scenario.minimum_spread_ticks,
        observed_spread_ticks * scenario.spread_multiplier,
    )
    stressed_spread_cost = stressed_spread_ticks * observation.tick_value
    stressed_commission = (
        observation.commission_per_volume_usd
        * scenario.commission_multiplier
    )
    stressed_slippage = max(
        observation.slippage_reserve_per_volume_usd,
        scenario.minimum_slippage_reserve_per_volume_usd,
    )
    stressed_execution_cost = (
        stressed_spread_cost
        + stressed_commission
        + stressed_slippage
    )
    stressed_margin = (
        observation.margin_per_volume * scenario.margin_multiplier
    )

    stop_ticks = (
        abs(causal.entry_price - causal.structural_stop)
        / observation.tick_size
    )
    raw_stop_loss_per_volume_usd = stop_ticks * observation.tick_value
    stop_loss_per_volume = (
        raw_stop_loss_per_volume_usd + stressed_execution_cost
    ) * scenario.broker_risk_buffer
    if stop_loss_per_volume <= 0:
        raise CiboCapitalManagementError(
            "counterfactual stop loss per volume must be positive"
        )

    opportunity = TraderOpportunityEnvelope(
        trader_id=causal.trader_id,
        signal_fingerprint=causal.signal_fingerprint,
        qore_symbol=causal.qore_symbol,
        provider_symbol=observation.provider_symbol,
        side=causal.side,
        entry_type="counterfactual_provider_stress",
        intended_entry=causal.entry_price,
        stop_loss=causal.structural_stop,
        take_profit=causal.technical_target,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=stressed_margin,
        volume_step=observation.volume_step,
        minimum_volume=stressed_minimum_volume,
        maximum_volume=stressed_maximum_volume,
        minimum_execution_steps=causal.minimum_execution_steps,
    )
    economics = Phase20CounterfactualProviderEconomics(
        scenario_id=scenario.scenario_id,
        provider_key=observation.provider_key,
        provider_symbol=observation.provider_symbol,
        source_observed_at_iso=observation.observed_at.isoformat(),
        stressed_spread_ticks=stressed_spread_ticks,
        stressed_spread_cost_per_volume_usd=stressed_spread_cost,
        stressed_commission_per_volume_usd=stressed_commission,
        stressed_slippage_reserve_per_volume_usd=stressed_slippage,
        stressed_execution_cost_per_volume_usd=stressed_execution_cost,
        stressed_margin_per_volume_usd=stressed_margin,
        stressed_minimum_volume=stressed_minimum_volume,
        stressed_maximum_volume=stressed_maximum_volume,
        minimum_executable_volume=minimum_executable_volume,
        available_liquidity_volume=available_liquidity_volume,
        stressed_execution_delay_ms=scenario.execution_delay_ms_floor,
        tick_size=observation.tick_size,
        tick_value=observation.tick_value,
        volume_step=observation.volume_step,
        broker_risk_buffer=scenario.broker_risk_buffer,
        source_evidence_id=(
            f"{scenario.evidence_id}|provider:{observation.provider_key}:"
            f"{observation.observed_at.isoformat()}"
        ),
    )
    result = Phase20CounterfactualOpportunity(
        opportunity=opportunity,
        economics=economics,
    )
    return Phase20ProviderStressEvaluation(
        scenario_id=scenario.scenario_id,
        status=Phase20ProviderStressStatus.EXECUTABLE,
        reason="COUNTERFACTUAL_STRESS_EXECUTABLE",
        minimum_executable_volume=minimum_executable_volume,
        effective_maximum_volume=stressed_maximum_volume,
        available_liquidity_volume=available_liquidity_volume,
        result=result,
    )


def build_phase20_counterfactual_provider_stress(
    *,
    causal: CiboReplayCausalTrade,
    observation: ProviderEconomicObservation,
    scenario: Phase20ProviderStressScenario,
) -> Phase20CounterfactualOpportunity:
    """Build one executable counterfactual opportunity or fail closed."""

    evaluation = evaluate_phase20_counterfactual_provider_stress(
        causal=causal,
        observation=observation,
        scenario=scenario,
    )
    if evaluation.result is None:
        raise CiboCapitalManagementError(
            f"counterfactual provider stress infeasible: {evaluation.reason}"
        )
    return evaluation.result


def phase20c_synthetic_predeclared_stress_scenarios(
) -> tuple[Phase20ProviderStressScenario, ...]:
    """Frozen synthetic Phase20C matrix.

    These values are explicit counterfactual assumptions for contract/failure
    proof only. They are not calibrated provider bounds and must never be
    relabelled as historical or forward-observed economics.
    """

    evidence_id = "counterfactual:phase20c:synthetic-matrix:v1"
    return (
        Phase20ProviderStressScenario(
            scenario_id="CF_BASELINE_CURRENT_SNAPSHOT",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("1"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_SPREAD_X2",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("2"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_COMMISSION_X2",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("1"),
            commission_multiplier=Decimal("2"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_SLIPPAGE_FLOOR_4",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("1"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("4"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_MARGIN_X2",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("1"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("2"),
            broker_risk_buffer=Decimal("1"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_EXECUTION_DELAY_2000MS",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("1"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
            execution_delay_ms_floor=Decimal("2000"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_LIQUIDITY_UNAVAILABLE",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("1"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
            available_liquidity_volume_cap=Decimal("0"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_MINIMUM_VOLUME_CLIFF",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("0"),
            spread_multiplier=Decimal("1"),
            commission_multiplier=Decimal("1"),
            minimum_slippage_reserve_per_volume_usd=Decimal("0"),
            margin_multiplier=Decimal("1"),
            broker_risk_buffer=Decimal("1"),
            minimum_volume_floor=Decimal("2"),
            maximum_volume_cap=Decimal("1"),
        ),
        Phase20ProviderStressScenario(
            scenario_id="CF_COMBINED_ADVERSE",
            evidence_id=evidence_id,
            minimum_spread_ticks=Decimal("4"),
            spread_multiplier=Decimal("3"),
            commission_multiplier=Decimal("2"),
            minimum_slippage_reserve_per_volume_usd=Decimal("5"),
            margin_multiplier=Decimal("2.5"),
            broker_risk_buffer=Decimal("1.25"),
            minimum_volume_floor=Decimal("0.05"),
            available_liquidity_volume_cap=Decimal("0.10"),
            execution_delay_ms_floor=Decimal("3000"),
        ),
    )


def run_phase20c_counterfactual_stress_matrix(
    *,
    causal: CiboReplayCausalTrade,
    observation: ProviderEconomicObservation,
    scenarios: tuple[Phase20ProviderStressScenario, ...],
) -> tuple[Phase20ProviderStressEvaluation, ...]:
    """Evaluate a frozen scenario matrix and enforce non-improving economics."""

    if not scenarios:
        raise CiboCapitalManagementError(
            "Phase20C stress matrix requires at least one scenario"
        )
    ids = [scenario.scenario_id for scenario in scenarios]
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "Phase20C stress matrix scenario ids must be unique"
        )

    evaluations = tuple(
        evaluate_phase20_counterfactual_provider_stress(
            causal=causal,
            observation=observation,
            scenario=scenario,
        )
        for scenario in scenarios
    )
    baseline = evaluations[0]
    if (
        scenarios[0].scenario_id != "CF_BASELINE_CURRENT_SNAPSHOT"
        or baseline.result is None
    ):
        raise CiboCapitalManagementError(
            "Phase20C stress matrix requires executable frozen baseline first"
        )
    baseline_economics = baseline.result.economics
    for evaluation in evaluations[1:]:
        if evaluation.result is None:
            continue
        economics = evaluation.result.economics
        if (
            economics.stressed_execution_cost_per_volume_usd
            < baseline_economics.stressed_execution_cost_per_volume_usd
            or economics.stressed_margin_per_volume_usd
            < baseline_economics.stressed_margin_per_volume_usd
            or evaluation.result.opportunity.stop_loss_per_volume
            < baseline.result.opportunity.stop_loss_per_volume
        ):
            raise CiboCapitalManagementError(
                "Phase20C adverse scenario improved provider economics"
            )
        if (
            evaluation.result.opportunity.intended_entry
            != baseline.result.opportunity.intended_entry
            or evaluation.result.opportunity.stop_loss
            != baseline.result.opportunity.stop_loss
            or evaluation.result.opportunity.take_profit
            != baseline.result.opportunity.take_profit
        ):
            raise CiboCapitalManagementError(
                "Phase20C stress matrix changed Trader geometry"
            )
    return evaluations
