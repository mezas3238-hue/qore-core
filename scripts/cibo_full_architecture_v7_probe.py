"""CIBO full-architecture functional probe for the isolated USD60/6M V7 lab.

This probe exercises every currently executable CE2I tool contract using the
canonical implementation.  Tool contracts that the canonical registry still
marks ARCHITECTURE_ONLY are reported explicitly and are never faked as executed.

The probe is intentionally separate from LIVE, DEMO activation, Phase20D,
Phase21 and Phase22 evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
    eligible_ce2i_tool_codes_for_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    plan_minimal_seed,
    plan_self_financing_expansion,
)
from qore.infrastructure.cibo_capital_source_ledger import (
    CapitalSourceLedger,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_capital_state_machine import derive_stage
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDisposition,
    CapitalVelocityEvidence,
    CapitalVelocityPolicy,
    ConvexExposureEvidence,
    ConvexInstrumentEvidence,
    FactorExposure,
    HedgeInstrumentEvidence,
    HedgedExposureEvidence,
    MarginEfficiencyEvidence,
    MarginExpression,
    PortfolioNettingEvidence,
    RiskEfficiencyCandidate,
    RiskEfficiencyEvidence,
    StructuralLeverageEvidence,
    assert_complete_advanced_ce2i_surface,
    evaluate_capital_velocity,
    evaluate_convex_exposure,
    evaluate_hedged_exposure,
    evaluate_margin_efficiency,
    evaluate_portfolio_netting,
    evaluate_risk_efficiency,
    evaluate_structural_leverage,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)
from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskAction,
    CiboDeRiskingInput,
    plan_dynamic_derisking,
)
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
    execution_efficient_volume_cap,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationBudget,
    allocate_competing_opportunities,
)
from qore.infrastructure.cibo_ce2i_optionality import KnownCapitalOption
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_recycling import (
    RecyclePurpose,
    ReleasedCapacityEvidence,
    deploy_recycled_capacity,
    register_released_capacity,
    reserve_recycled_capacity,
    settle_recycled_capacity,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
    validate_registry,
)
from qore.infrastructure.cibo_cma_capital_observation import (
    CmaCapitalObservationInput,
    observe_capital_state,
)
from qore.infrastructure.cibo_economic_floor import (
    ReconciledPositionEconomics,
    evaluate_economic_floor,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2022, 4, 1, 12, 0, tzinfo=UTC)


def _opportunity(
    *,
    trader: TraderLineage,
    fingerprint: str,
    symbol: str,
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=fingerprint,
        qore_symbol=symbol,
        provider_symbol=f"SIM:{symbol}",
        side="long",
        entry_type="full_architecture_probe",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("1"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("100"),
        minimum_execution_steps=1,
    )


def _expectation(
    *,
    evidence_id: str,
    value: str,
    minutes: str,
) -> CausalOpportunityExpectation:
    return CausalOpportunityExpectation(
        evidence_id=evidence_id,
        as_of=NOW,
        basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
        expected_net_value_usd=Decimal(value),
        expected_capital_minutes=Decimal(minutes),
    )


def run_probe(output: Path) -> dict[str, object]:
    validate_registry()

    mission = derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="qore-sandbox",
            account_ref="cibo-60usd-6m-full-architecture-v4",
            environment=MarketRuntimeEnvironment.SANDBOX,
        )
    )
    mission_tools = eligible_ce2i_tool_codes_for_mission(mission)
    executable_registry_tools = {
        tool.code
        for tool in CE2I_TOOL_REGISTRY
        if tool.maturity not in {
            ToolMaturity.ARCHITECTURE_ONLY,
            ToolMaturity.REJECTED,
        }
    }
    if set(mission_tools) != executable_registry_tools:
        raise RuntimeError(
            "SANDBOX mission must expose every currently executable CE2I tool"
        )

    executed: dict[str, int] = {tool.code: 0 for tool in CE2I_TOOL_REGISTRY}
    evidence: dict[str, list[str]] = {tool.code: [] for tool in CE2I_TOOL_REGISTRY}

    # T01 — canonical minimal seed.
    opp = _opportunity(
        trader=TraderLineage.R38_GBPJPY,
        fingerprint="probe-t01",
        symbol="GBPJPY",
    )
    seed_capital = CiboCapitalState(
        assigned_capital_usd=Decimal("60"),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("60"),
        base_capital_at_risk_usd=Decimal("60"),
        realized_net_profit_usd=Decimal(0),
        protected_open_economic_floor_usd=Decimal(0),
        proven_self_financing_capacity_usd=Decimal(0),
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )
    seed = plan_minimal_seed(opp, seed_capital)
    assert seed.action is CapitalAction.OPEN_MINIMAL_SEED
    assert seed.stop_risk_usd == Decimal("1")
    executed["T01"] += 1
    evidence["T01"].append("plan_minimal_seed")

    # Economic floor + state machine + passive observation.
    floor = evaluate_economic_floor(
        ReconciledPositionEconomics(
            trader_id=TraderLineage.R38_GBPJPY,
            signal_fingerprint="probe-floor",
            realized_net_pnl_usd=Decimal("2"),
            remaining_stop_worst_case_pnl_usd=Decimal("-1"),
            future_cost_reserve_usd=Decimal(0),
            slippage_reserve_usd=Decimal(0),
            broker_position_reconciled=True,
            protection_reconciled=True,
        )
    )
    assert floor.base_recovered is True
    stage = derive_stage(seed_deployed=True, position_open=True, floor=floor)
    assert stage.expansion_eligible is True
    observation = observe_capital_state(
        CmaCapitalObservationInput(
            trader_id=TraderLineage.R38_GBPJPY,
            signal_fingerprint="probe-observation",
            qore_symbol="GBPJPY",
            position_id=1,
            seed_deployed=True,
            position_open=True,
            realized_net_pnl_usd=Decimal("2"),
            remaining_stop_worst_case_pnl_usd=Decimal("-1"),
            future_cost_reserve_usd=Decimal(0),
            slippage_reserve_usd=Decimal(0),
            broker_position_reconciled=True,
            protection_reconciled=True,
            mutation_outcome_unknown=False,
        )
    )
    assert observation.expansion_eligible is True

    # T06 — realized-profit funded expansion.
    realized_state = CiboCapitalState(
        assigned_capital_usd=Decimal("120"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("20"),
        base_capital_at_risk_usd=Decimal(0),
        realized_net_profit_usd=Decimal("20"),
        protected_open_economic_floor_usd=Decimal(0),
        proven_self_financing_capacity_usd=Decimal("20"),
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )
    realized_plan = plan_self_financing_expansion(opp, realized_state)
    assert realized_plan.action is CapitalAction.EXPAND
    assert realized_plan.capital_source is CapitalSource.REALIZED_PROFIT
    executed["T06"] += 1
    evidence["T06"].append("plan_self_financing_expansion:REALIZED_PROFIT")

    # T07 — broker-protected economic-floor funded expansion.
    protected_state = CiboCapitalState(
        assigned_capital_usd=Decimal("120"),
        hard_risk_headroom_usd=Decimal("12"),
        margin_headroom_usd=Decimal("12"),
        base_capital_at_risk_usd=Decimal(0),
        realized_net_profit_usd=Decimal(0),
        protected_open_economic_floor_usd=Decimal("12"),
        proven_self_financing_capacity_usd=Decimal("12"),
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )
    protected_plan = plan_self_financing_expansion(opp, protected_state)
    assert protected_plan.action is CapitalAction.EXPAND
    assert protected_plan.capital_source is CapitalSource.PROTECTED_ECONOMIC_FLOOR
    executed["T07"] += 1
    evidence["T07"].append(
        "plan_self_financing_expansion:PROTECTED_ECONOMIC_FLOOR"
    )

    # T11 — execution-efficient exposure.
    cap = execution_efficient_volume_cap(
        ExecutionCostCurveInput(
            evidence_id="probe-t11",
            volume_step=Decimal("1"),
            maximum_volume=Decimal("20"),
            gross_edge_per_volume_usd=Decimal("0.50"),
            spread_cost_per_volume_usd=Decimal("0.05"),
            commission_cost_per_volume_usd=Decimal("0.02"),
            slippage_cost_per_volume_usd=Decimal("0.03"),
            impact_cost_per_volume_squared_usd=Decimal("0.005"),
        )
    )
    assert cap.volume_cap > 0
    assert cap.volume_cap <= Decimal("20")
    executed["T11"] += 1
    evidence["T11"].append("execution_efficient_volume_cap")

    # T12 — regime-adaptive tool selection.
    stable_state = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.20"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.10"),
        opportunity_count=2,
    )
    stable_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=stable_state,
    )
    assert "T12" in stable_regime.enabled_tools
    executed["T12"] += 1
    evidence["T12"].append("select_ce2i_tools_for_regime:STABLE")

    # T09/T18 — causal cross-Trader competition.
    c1 = CapitalOpportunityCandidate(
        signal_fingerprint="probe-comp-1",
        trader_id=TraderLineage.R38_GBPJPY,
        qore_symbol="GBPJPY",
        provider_symbol="SIM:GBPJPY",
        decision_as_of=NOW,
        expectation=_expectation(
            evidence_id="probe-exp-1",
            value="2",
            minutes="30",
        ),
        stop_risk_usd=Decimal("4"),
        margin_usd=Decimal("4"),
        concentration_group="JPY",
        concentration_risk_usd=Decimal("4"),
    )
    c2 = CapitalOpportunityCandidate(
        signal_fingerprint="probe-comp-2",
        trader_id=TraderLineage.VT31_NAS100,
        qore_symbol="NAS100",
        provider_symbol="SIM:NAS100",
        decision_as_of=NOW,
        expectation=_expectation(
            evidence_id="probe-exp-2",
            value="1.5",
            minutes="20",
        ),
        stop_risk_usd=Decimal("4"),
        margin_usd=Decimal("4"),
        concentration_group="INDEX",
        concentration_risk_usd=Decimal("4"),
    )
    competition = allocate_competing_opportunities(
        (c1, c2),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("6"),
            margin_headroom_usd=Decimal("6"),
            concentration_limit_by_group=(
                ("JPY", Decimal("6")),
                ("INDEX", Decimal("6")),
            ),
        ),
    )
    assert len(competition.selected_signal_fingerprints) == 1
    executed["T09"] += 1
    executed["T18"] += 1
    evidence["T09"].append("allocate_competing_opportunities")
    evidence["T18"].append("allocate_competing_opportunities")

    # T15 and T13 — optionality + drawdown reserve through robust allocator.
    recovery_state = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.ELEVATED,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.90"),
        margin_utilization=Decimal("0.20"),
        drawdown_utilization=Decimal("0.80"),
        opportunity_count=2,
        position_path_adverse=True,
    )
    recovery_regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=recovery_state,
    )
    recovery = propose_phase20h_robust_allocation(
        mission=mission,
        regime=recovery_regime,
        hard_risk_headroom_usd=Decimal("10"),
        margin_headroom_usd=Decimal("10"),
        concentration_limit_by_group=(
            ("JPY", Decimal("10")),
            ("INDEX", Decimal("10")),
        ),
        candidates=(c1, c2),
        known_options=(
            KnownCapitalOption(
                opportunity_id="future-1",
                minimum_stop_risk_usd=Decimal("1"),
                minimum_margin_usd=Decimal("1"),
            ),
        ),
    )
    assert recovery.disposition is Phase20AllocatorDisposition.PRESERVE_CAPACITY
    assert "T15" in recovery.applied_tools
    assert "T13" in recovery.applied_tools
    executed["T15"] += 1
    executed["T13"] += 1
    evidence["T15"].append("phase20h_robust_allocator:RECOVERY")
    evidence["T13"].append("phase20h_robust_allocator:RECOVERY")

    # T14 — dynamic de-risking.
    derisk = plan_dynamic_derisking(
        CiboDeRiskingInput(
            current_volume=Decimal("10"),
            minimum_retained_volume=Decimal("1"),
            volume_step=Decimal("1"),
            stop_risk_per_volume_usd=Decimal("1"),
            margin_per_volume_usd=Decimal("1"),
            maximum_retained_stop_risk_usd=Decimal("4"),
            maximum_retained_margin_usd=Decimal("5"),
            methodology_position_valid=True,
        )
    )
    assert derisk.action is CiboDeRiskAction.REDUCE
    assert derisk.retained_volume == Decimal("4")
    executed["T14"] += 1
    evidence["T14"].append("plan_dynamic_derisking:REDUCE")

    # T19/T20 — atomic reservation and release.
    ledger = CapitalSourceLedger().add_source(
        source_id="profit-probe",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("10"),
    )
    ledger = ledger.reserve(
        reservation_id="probe-t19",
        source_id="profit-probe",
        amount_usd=Decimal("4"),
    )
    assert ledger.accounts[0].reserved_usd == Decimal("4")
    executed["T19"] += 1
    evidence["T19"].append("CapitalSourceLedger.reserve")
    ledger = ledger.release_unused("probe-t19")
    assert ledger.accounts[0].available_usd == Decimal("10")
    executed["T20"] += 1
    evidence["T20"].append("CapitalSourceLedger.release_unused")

    # T05 — dimension-safe released-capacity recycling through durable CAS store.
    recycle_store = DurableCapitalSourceLedgerStore(
        output.parent / "probe-recycle-ledger.json"
    )
    registered = register_released_capacity(
        ReleasedCapacityEvidence(
            evidence_id="probe-release-risk",
            source=CapitalSource.RELEASED_RISK_CAPACITY,
            amount_usd=Decimal("3"),
            reconciled_at=NOW,
            upstream_reference="probe-position-close",
        ),
        ledger_store=recycle_store,
    )
    recycled = reserve_recycled_capacity(
        reservation_id="probe-t05",
        source_id=registered.source_id,
        purpose=RecyclePurpose.STOP_RISK,
        amount_usd=Decimal("2"),
        ledger_store=recycle_store,
    )
    deploy_recycled_capacity(recycled, ledger_store=recycle_store)
    settled = settle_recycled_capacity(
        recycled,
        returned_capacity_usd=Decimal("2"),
        ledger_store=recycle_store,
    )
    assert settled.ledger.accounts[0].available_usd == Decimal("3")
    executed["T05"] += 1
    evidence["T05"].append("released-capacity register/reserve/deploy/settle")

    # T02 — verified OOS structural leverage.
    assert_complete_advanced_ce2i_surface()
    t02 = evaluate_structural_leverage(
        opportunity=opp,
        evidence=StructuralLeverageEvidence(
            evidence_id="probe-t02-oos",
            structural_invalidation_id="probe-stop-v1",
            observed_at=NOW,
            sample_size=80,
            baseline_stop_rate=Decimal("0.44"),
            candidate_stop_rate=Decimal("0.35"),
            baseline_tail_loss_r=Decimal("1.00"),
            candidate_tail_loss_r=Decimal("0.90"),
            released_risk_capacity_usd=Decimal("2"),
            protected_capacity_usd=Decimal("1"),
            evidence_oos=True,
            structural_stop_verified=True,
            stop_geometry_unchanged=True,
        ),
        current_volume=Decimal("1"),
        maximum_additional_volume=Decimal("2"),
    )
    assert t02.disposition is AdvancedToolDisposition.APPLIED
    executed["T02"] += 1
    evidence["T02"].append("evaluate_structural_leverage:APPLIED")

    # T03 — verified economically equivalent lower-margin expression.
    t03 = evaluate_margin_efficiency(
        MarginEfficiencyEvidence(
            evidence_id="probe-t03",
            observed_at=NOW,
            baseline_expression_id="spot",
            expressions=(
                MarginExpression(
                    expression_id="spot",
                    normalized_exposure=Decimal("100"),
                    stop_risk_usd=Decimal("10"),
                    margin_usd=Decimal("50"),
                    all_in_cost_usd=Decimal("2"),
                    executable=True,
                    economics_verified=True,
                ),
                MarginExpression(
                    expression_id="equivalent",
                    normalized_exposure=Decimal("100"),
                    stop_risk_usd=Decimal("10"),
                    margin_usd=Decimal("30"),
                    all_in_cost_usd=Decimal("2"),
                    executable=True,
                    economics_verified=True,
                ),
            ),
        )
    )
    assert t03.disposition is AdvancedToolDisposition.APPLIED
    executed["T03"] += 1
    evidence["T03"].append("evaluate_margin_efficiency:APPLIED")

    # T04 — OOS output per true stop-risk efficiency.
    t04 = evaluate_risk_efficiency(
        RiskEfficiencyEvidence(
            evidence_id="probe-t04",
            observed_at=NOW,
            baseline_candidate_id="baseline",
            candidates=(
                RiskEfficiencyCandidate(
                    candidate_id="baseline",
                    expected_net_output_usd=Decimal("20"),
                    true_stop_risk_usd=Decimal("10"),
                    p95_drawdown_usd=Decimal("12"),
                    tail_loss_usd=Decimal("15"),
                    margin_usd=Decimal("30"),
                    sample_size=100,
                    evidence_oos=True,
                ),
                RiskEfficiencyCandidate(
                    candidate_id="efficient",
                    expected_net_output_usd=Decimal("24"),
                    true_stop_risk_usd=Decimal("8"),
                    p95_drawdown_usd=Decimal("11"),
                    tail_loss_usd=Decimal("14"),
                    margin_usd=Decimal("30"),
                    sample_size=100,
                    evidence_oos=True,
                ),
            ),
        )
    )
    assert t04.disposition is AdvancedToolDisposition.APPLIED
    executed["T04"] += 1
    evidence["T04"].append("evaluate_risk_efficiency:APPLIED")

    # T08 — stable verified factor-offset portfolio netting.
    t08 = evaluate_portfolio_netting(
        PortfolioNettingEvidence(
            evidence_id="probe-t08",
            observed_at=NOW,
            correlation_state_id="probe-corr-v1",
            correlation_stable=True,
            factor_map_verified=True,
            maximum_credit_fraction=Decimal("0.50"),
            exposures=(
                FactorExposure(
                    position_id="probe-p1",
                    factor_id="USD",
                    signed_risk_usd=Decimal("10"),
                ),
                FactorExposure(
                    position_id="probe-p2",
                    factor_id="USD",
                    signed_risk_usd=Decimal("-6"),
                ),
            ),
        )
    )
    assert t08.disposition is AdvancedToolDisposition.APPLIED
    executed["T08"] += 1
    evidence["T08"].append("evaluate_portfolio_netting:APPLIED")

    # T10 — OOS capital-time productivity.
    t10 = evaluate_capital_velocity(
        CapitalVelocityEvidence(
            evidence_id="probe-t10",
            observed_at=NOW,
            baseline_policy_id="baseline",
            policies=(
                CapitalVelocityPolicy(
                    policy_id="baseline",
                    realized_net_output_usd=Decimal("20"),
                    capital_minutes=Decimal("100"),
                    p95_drawdown_usd=Decimal("10"),
                    tail_loss_usd=Decimal("12"),
                    sample_size=100,
                    evidence_oos=True,
                ),
                CapitalVelocityPolicy(
                    policy_id="faster",
                    realized_net_output_usd=Decimal("22"),
                    capital_minutes=Decimal("80"),
                    p95_drawdown_usd=Decimal("10"),
                    tail_loss_usd=Decimal("11"),
                    sample_size=100,
                    evidence_oos=True,
                ),
            ),
        )
    )
    assert t10.disposition is AdvancedToolDisposition.APPLIED
    executed["T10"] += 1
    evidence["T10"].append("evaluate_capital_velocity:APPLIED")

    # T16 — certified positive-net hedge transfer.
    t16 = evaluate_hedged_exposure(
        HedgedExposureEvidence(
            evidence_id="probe-t16",
            observed_at=NOW,
            instruments=(
                HedgeInstrumentEvidence(
                    instrument_id="probe-hedge-1",
                    target_factor_id="USD",
                    correlation_abs=Decimal("0.90"),
                    correlation_stability=Decimal("0.85"),
                    gross_risk_reduction_usd=Decimal("20"),
                    basis_risk_usd=Decimal("4"),
                    hedge_cost_usd=Decimal("2"),
                    margin_usd=Decimal("3"),
                    instrument_certified=True,
                    execution_supported=True,
                ),
            ),
        )
    )
    assert t16.disposition is AdvancedToolDisposition.APPLIED
    executed["T16"] += 1
    evidence["T16"].append("evaluate_hedged_exposure:APPLIED")

    # T17 — certified executable bounded-downside convex expression.
    t17 = evaluate_convex_exposure(
        ConvexExposureEvidence(
            evidence_id="probe-t17",
            observed_at=NOW,
            available_limited_downside_capacity_usd=Decimal("20"),
            instruments=(
                ConvexInstrumentEvidence(
                    instrument_id="probe-convex-1",
                    bounded_downside_usd=Decimal("10"),
                    premium_and_cost_usd=Decimal("2"),
                    expected_upside_usd=Decimal("12"),
                    pricing_fresh=True,
                    settlement_certified=True,
                    execution_supported=True,
                    instrument_certified=True,
                ),
            ),
        )
    )
    assert t17.disposition is AdvancedToolDisposition.APPLIED
    executed["T17"] += 1
    evidence["T17"].append("evaluate_convex_exposure:APPLIED")

    registry_rows: list[dict[str, object]] = []
    missing_executable: list[str] = []
    architecture_only: list[str] = []
    for tool in CE2I_TOOL_REGISTRY:
        if tool.maturity is ToolMaturity.ARCHITECTURE_ONLY:
            status = "CONTRACT_ONLY_NOT_EXECUTABLE"
            architecture_only.append(tool.code)
        elif tool.maturity is ToolMaturity.REJECTED:
            status = "REJECTED_BY_CANONICAL_REGISTRY"
        elif executed[tool.code] > 0:
            status = "EXECUTED_GREEN"
        else:
            status = "IMPLEMENTED_BUT_NOT_EXERCISED"
            missing_executable.append(tool.code)
        registry_rows.append(
            {
                "code": tool.code,
                "name": tool.name,
                "maturity": tool.maturity.value,
                "status": status,
                "execution_count": executed[tool.code],
                "evidence": evidence[tool.code],
            }
        )

    if missing_executable:
        raise RuntimeError(
            f"implemented CE2I tools not exercised: {missing_executable}"
        )

    report: dict[str, object] = {
        "schema": "qore.cibo.full-architecture-functional-probe.v3",
        "identity": "CIBO_60USD_6M_FULL_ARCHITECTURE_V7_PROBE",
        "mission": mission.mission.value,
        "all_registry_contracts_visible": len(CE2I_TOOL_REGISTRY) == 20,
        "all_currently_executable_tools_exercised": True,
        "architecture_only_tools": architecture_only,
        "tool_matrix": registry_rows,
        "non_tool_architecture": {
            "economic_floor": "GREEN",
            "capital_state_machine": "GREEN",
            "capital_observation": "GREEN",
            "durable_capital_ledger_cas": "GREEN",
        },
        "governance": {
            "isolated_experiment": True,
            "vps_used": False,
            "broker_mutation": False,
            "demo_activation": False,
            "live_authority": False,
            "real_capital_authority": False,
            "phase20d_evidence": False,
            "phase21_evidence": False,
            "phase22_evidence": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_probe(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
