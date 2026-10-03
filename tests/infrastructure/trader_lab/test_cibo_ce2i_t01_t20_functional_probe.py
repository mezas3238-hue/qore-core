from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    plan_minimal_seed,
    plan_self_financing_expansion,
)
from qore.infrastructure.cibo_capital_source_ledger import ReservationState
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDisposition,
    CapitalVelocityEvidence,
    CapitalVelocityPolicy,
    ConvexExposureEvidence,
    ConvexInstrumentEvidence,
    FactorExposure,
    HedgedExposureEvidence,
    HedgeInstrumentEvidence,
    MarginEfficiencyEvidence,
    MarginExpression,
    PortfolioNettingEvidence,
    RiskEfficiencyCandidate,
    RiskEfficiencyEvidence,
    StructuralLeverageEvidence,
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
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationBudget,
    allocate_competing_opportunities,
)
from qore.infrastructure.cibo_ce2i_optionality import (
    KnownCapitalOption,
    plan_capital_optionality,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
    propose_phase20h_robust_allocation,
)
from qore.infrastructure.cibo_ce2i_recycling import (
    RecyclePurpose,
    ReleasedCapacityEvidence,
    deploy_recycled_capacity,
    recycled_reservation_state,
    register_released_capacity,
    release_unused_recycled_capacity,
    reserve_recycled_capacity,
    settle_recycled_capacity,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.cibo_ce2i_t11_runtime_guard import (
    T11RuntimeDisposition,
    evaluate_t11_runtime_exposure_guard,
)
from qore.infrastructure.cibo_ce2i_tool_registry import CE2I_TOOL_REGISTRY
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    normalize_provider_economics,
)
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    T20CapitalAuthorizationEvidence,
    T20CapitalReleaseSlice,
    build_t20_capital_release_evidence,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 2, 40, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _mission(candidate: TraderLabCandidateBinding):
    return derive_cibo_capital_mission(
        CiboAccountCapitalIdentity(
            provider_key="ctrader-lab",
            account_ref=_tag(candidate, "account"),
            environment=MarketRuntimeEnvironment.DEMO,
        )
    )


def _opportunity(
    candidate: TraderLabCandidateBinding,
    *,
    symbol: str = "BTCUSD",
    trader: TraderLineage = TraderLineage.R38_EURUSD,
    suffix: str = "signal",
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=_tag(candidate, suffix),
        qore_symbol=symbol,
        provider_symbol=symbol,
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("1"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
        decision_context=(
            ("trader_lab_candidate", candidate.fingerprint.value),
        ),
    )


def _capital(
    *,
    realized: str = "0",
    protected: str = "0",
    proven: str = "0",
) -> CiboCapitalState:
    return CiboCapitalState(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("20"),
        margin_headroom_usd=Decimal("100"),
        base_capital_at_risk_usd=Decimal("0"),
        realized_net_profit_usd=Decimal(realized),
        protected_open_economic_floor_usd=Decimal(protected),
        proven_self_financing_capacity_usd=Decimal(proven),
        reserved_expansion_risk_usd=Decimal("0"),
        cost_reserve_usd=Decimal("0"),
    )


def _regime(
    candidate: TraderLabCandidateBinding,
    *,
    drawdown: str = "0.20",
    adverse: bool = False,
    opportunity_count: int = 2,
):
    mission = _mission(candidate)
    return select_ce2i_tools_for_regime(
        mission=mission,
        state=CiboCapitalRegimeState(
            liquidity=LiquidityState.NORMAL,
            volatility=VolatilityState.NORMAL,
            correlation=CorrelationState.NORMAL,
            provider_condition=ProviderCondition.HEALTHY,
            risk_utilization=Decimal("0.20"),
            margin_utilization=Decimal("0.20"),
            drawdown_utilization=Decimal(drawdown),
            opportunity_count=opportunity_count,
            position_path_adverse=adverse,
        ),
    )


def _competition_candidate(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: str,
    trader: TraderLineage,
    net: str,
    minutes: str,
    group: str,
) -> CapitalOpportunityCandidate:
    signal = _tag(candidate, suffix)
    return CapitalOpportunityCandidate(
        signal_fingerprint=signal,
        trader_id=trader,
        qore_symbol=suffix.upper(),
        provider_symbol=suffix.upper(),
        decision_as_of=NOW,
        expectation=CausalOpportunityExpectation(
            evidence_id=_tag(candidate, f"expectation:{suffix}"),
            as_of=NOW,
            basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
            expected_net_value_usd=Decimal(net),
            expected_capital_minutes=Decimal(minutes),
        ),
        stop_risk_usd=Decimal("5"),
        margin_usd=Decimal("10"),
        concentration_group=group,
        concentration_risk_usd=Decimal("5"),
    )


def _known_options(candidate: TraderLabCandidateBinding) -> tuple[KnownCapitalOption, ...]:
    return (
        KnownCapitalOption(
            opportunity_id=_tag(candidate, "future-small"),
            minimum_stop_risk_usd=Decimal("4"),
            minimum_margin_usd=Decimal("20"),
        ),
        KnownCapitalOption(
            opportunity_id=_tag(candidate, "future-large"),
            minimum_stop_risk_usd=Decimal("10"),
            minimum_margin_usd=Decimal("40"),
        ),
    )


def test_trader_lab_t01_minimal_seed(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=901)
    plan = plan_minimal_seed(_opportunity(candidate), _capital())
    assert plan.action is CapitalAction.OPEN_MINIMAL_SEED
    assert plan.capital_source is CapitalSource.ORIGINAL_BASE_CAPITAL
    assert plan.volume == Decimal("0.01")


def test_trader_lab_t02_structural_leverage(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=902)
    decision = evaluate_structural_leverage(
        opportunity=_opportunity(candidate),
        evidence=StructuralLeverageEvidence(
            evidence_id=_tag(candidate, "t02"),
            structural_invalidation_id=_tag(candidate, "structural-stop"),
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
        current_volume=Decimal("0.01"),
        maximum_additional_volume=Decimal("0.20"),
    )
    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.approved_volume > Decimal("0.01")


def test_trader_lab_t03_margin_efficiency(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=903)
    decision = evaluate_margin_efficiency(
        MarginEfficiencyEvidence(
            evidence_id=_tag(candidate, "t03"),
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
    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.released_capacity_usd == Decimal("20")


def test_trader_lab_t04_risk_efficiency(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=904)
    decision = evaluate_risk_efficiency(
        RiskEfficiencyEvidence(
            evidence_id=_tag(candidate, "t04"),
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
    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.selected_id == "efficient"


def test_trader_lab_t05_capital_recycling(candidate_factory, tmp_path: Path) -> None:
    candidate = candidate_factory(candidate_suffix=905)
    store = DurableCapitalSourceLedgerStore(tmp_path / "t05-ledger.json")
    released = register_released_capacity(
        ReleasedCapacityEvidence(
            evidence_id=_tag(candidate, "t05-release"),
            source=CapitalSource.RELEASED_RISK_CAPACITY,
            amount_usd=Decimal("20"),
            reconciled_at=NOW,
            upstream_reference=_tag(candidate, "settlement"),
        ),
        ledger_store=store,
    )
    reservation = reserve_recycled_capacity(
        reservation_id=_tag(candidate, "t05-reservation"),
        source_id=released.source_id,
        purpose=RecyclePurpose.STOP_RISK,
        amount_usd=Decimal("8"),
        ledger_store=store,
    )
    deploy_recycled_capacity(reservation, ledger_store=store)
    settled = settle_recycled_capacity(
        reservation,
        returned_capacity_usd=Decimal("3"),
        ledger_store=store,
    )
    assert settled.ledger.accounts[0].consumed_usd == Decimal("5")
    assert recycled_reservation_state(
        reservation, ledger_store=store
    ) is ReservationState.SETTLED


def test_trader_lab_t06_profit_funded_expansion(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=906)
    plan = plan_self_financing_expansion(
        _opportunity(candidate),
        _capital(realized="10", proven="10"),
    )
    assert plan.action is CapitalAction.EXPAND
    assert plan.capital_source is CapitalSource.REALIZED_PROFIT


def test_trader_lab_t07_protected_capacity_expansion(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=907)
    plan = plan_self_financing_expansion(
        _opportunity(candidate),
        _capital(protected="10", proven="10"),
    )
    assert plan.action is CapitalAction.EXPAND
    assert plan.capital_source is CapitalSource.PROTECTED_ECONOMIC_FLOOR


def test_trader_lab_t08_portfolio_netting(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=908)
    decision = evaluate_portfolio_netting(
        PortfolioNettingEvidence(
            evidence_id=_tag(candidate, "t08"),
            observed_at=NOW,
            correlation_state_id=_tag(candidate, "corr-v1"),
            correlation_stable=True,
            factor_map_verified=True,
            risk_mapping_evidence_id=_tag(candidate, "risk-map"),
            correlation_evidence_id=_tag(candidate, "corr-oos"),
            netting_utility_evidence_id=_tag(candidate, "netting-oos"),
            risk_mapping_verified=True,
            correlation_oos=True,
            correlation_sample_size=120,
            correlation_stability_folds=4,
            netting_utility_oos=True,
            netting_utility_sample_size=80,
            exposures=(
                FactorExposure(
                    position_id=_tag(candidate, "p1"),
                    factor_id="USD",
                    signed_risk_usd=Decimal("10"),
                ),
                FactorExposure(
                    position_id=_tag(candidate, "p2"),
                    factor_id="USD",
                    signed_risk_usd=Decimal("-6"),
                ),
            ),
        )
    )
    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.released_capacity_usd > 0


def test_trader_lab_t09_opportunity_competition(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=909)
    slow = _competition_candidate(
        candidate,
        suffix="slow",
        trader=TraderLineage.R38_EURUSD,
        net="10",
        minutes="20",
        group="USD",
    )
    fast = _competition_candidate(
        candidate,
        suffix="fast",
        trader=TraderLineage.R43_GBPUSD,
        net="8",
        minutes="5",
        group="USD",
    )
    decision = allocate_competing_opportunities(
        (slow, fast),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("5"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(("USD", Decimal("100")),),
        ),
    )
    assert decision.selected_signal_fingerprints == (fast.signal_fingerprint,)


def test_trader_lab_t10_capital_velocity(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=910)
    decision = evaluate_capital_velocity(
        CapitalVelocityEvidence(
            evidence_id=_tag(candidate, "t10"),
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
    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.selected_id == "faster"


def test_trader_lab_t11_execution_efficiency(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=911)
    opportunity = _opportunity(candidate, symbol="USDCAD")
    envelope = normalize_provider_economics(
        opportunity=opportunity,
        observation=ProviderEconomicObservation(
            provider_key="trader-lab",
            qore_symbol="USDCAD",
            provider_symbol="USDCAD",
            bid=Decimal("100"),
            ask=Decimal("100.10"),
            contract_size=Decimal("1"),
            tick_size=Decimal("1"),
            tick_value=Decimal("1"),
            minimum_volume=Decimal("0.01"),
            maximum_volume=Decimal("1"),
            volume_step=Decimal("0.01"),
            margin_per_volume=Decimal("1"),
            commission_per_volume_usd=Decimal("0.01"),
            slippage_reserve_per_volume_usd=Decimal("0.01"),
            observed_at=NOW,
        ),
    )
    decision = evaluate_t11_runtime_exposure_guard(
        qore_symbol=opportunity.qore_symbol,
        requested_volume=opportunity.minimum_volume,
        provider_envelope=envelope,
        gross_edge_model_ready=True,
        market_impact_model_ready=True,
    )
    assert decision.disposition is T11RuntimeDisposition.ADVANCED_EXPOSURE_ALLOWED
    assert decision.advanced_exposure_authorized is True


def test_trader_lab_t12_regime_adaptive_capitalization(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=912)
    decision = _regime(candidate)
    assert decision.posture is CiboRegimePosture.WATCH
    assert decision.enabled_tools == tuple(
        item.code for item in CE2I_TOOL_REGISTRY
    )


def test_trader_lab_t13_drawdown_reserve(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=913)
    mission = _mission(candidate)
    decision = propose_phase20h_robust_allocation(
        mission=mission,
        regime=_regime(candidate, drawdown="0.80", opportunity_count=1),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        concentration_limit_by_group=(("USD", Decimal("100")),),
        candidates=(
            _competition_candidate(
                candidate,
                suffix="recovery",
                trader=TraderLineage.R43_GBPUSD,
                net="8",
                minutes="5",
                group="USD",
            ),
        ),
        known_options=_known_options(candidate),
    )
    assert decision.disposition is Phase20AllocatorDisposition.PRESERVE_CAPACITY
    assert decision.applied_tools == ("T15", "T13")
    assert decision.deployable_stop_risk_usd == 0


def test_trader_lab_t14_dynamic_derisking(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=914)
    decision = plan_dynamic_derisking(
        CiboDeRiskingInput(
            current_volume=Decimal("1"),
            minimum_retained_volume=Decimal("0.01"),
            volume_step=Decimal("0.01"),
            stop_risk_per_volume_usd=Decimal("1"),
            margin_per_volume_usd=Decimal("1"),
            maximum_retained_stop_risk_usd=Decimal("0.50"),
            maximum_retained_margin_usd=Decimal("0.50"),
            methodology_position_valid=True,
        )
    )
    assert _tag(candidate, "t14")
    assert decision.action is CiboDeRiskAction.REDUCE
    assert decision.released_stop_risk_usd > 0


def test_trader_lab_t15_capital_optionality(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=915)
    mission = _mission(candidate)
    decision = plan_capital_optionality(
        mission=mission,
        regime=_regime(candidate, adverse=True),
        hard_risk_headroom_usd=Decimal("60"),
        margin_headroom_usd=Decimal("500"),
        known_options=_known_options(candidate),
    )
    assert decision.preserve_new_capital is True
    assert decision.reserve_stop_risk_usd == Decimal("4")


def test_trader_lab_t16_hedged_exposure(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=916)
    decision = evaluate_hedged_exposure(
        HedgedExposureEvidence(
            evidence_id=_tag(candidate, "t16"),
            observed_at=NOW,
            instruments=(
                HedgeInstrumentEvidence(
                    instrument_id=_tag(candidate, "hedge-1"),
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
    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.released_capacity_usd == Decimal("14")


def test_trader_lab_t17_convex_exposure(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=917)
    decision = evaluate_convex_exposure(
        ConvexExposureEvidence(
            evidence_id=_tag(candidate, "t17"),
            observed_at=NOW,
            available_limited_downside_capacity_usd=Decimal("20"),
            instruments=(
                ConvexInstrumentEvidence(
                    instrument_id=_tag(candidate, "convex-1"),
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
    assert decision.disposition is AdvancedToolDisposition.APPLIED
    assert decision.selected_id == _tag(candidate, "convex-1")


def test_trader_lab_t18_cross_trader_allocation(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=918)
    eur = _competition_candidate(
        candidate,
        suffix="eur",
        trader=TraderLineage.R38_EURUSD,
        net="10",
        minutes="10",
        group="EUR",
    )
    nas = _competition_candidate(
        candidate,
        suffix="nas",
        trader=TraderLineage.VT31_NAS100,
        net="9",
        minutes="10",
        group="INDEX",
    )
    decision = allocate_competing_opportunities(
        (eur, nas),
        OpportunityAllocationBudget(
            stop_risk_headroom_usd=Decimal("20"),
            margin_headroom_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EUR", Decimal("5")),
                ("INDEX", Decimal("5")),
            ),
        ),
    )
    assert decision.selected_signal_fingerprints == (
        eur.signal_fingerprint,
        nas.signal_fingerprint,
    )


def test_trader_lab_t19_capacity_reservation(candidate_factory, tmp_path: Path) -> None:
    candidate = candidate_factory(candidate_suffix=919)
    store = DurableCapitalSourceLedgerStore(tmp_path / "t19-ledger.json")
    released = register_released_capacity(
        ReleasedCapacityEvidence(
            evidence_id=_tag(candidate, "t19-release"),
            source=CapitalSource.RELEASED_RISK_CAPACITY,
            amount_usd=Decimal("20"),
            reconciled_at=NOW,
            upstream_reference=_tag(candidate, "settlement"),
        ),
        ledger_store=store,
    )
    reservation = reserve_recycled_capacity(
        reservation_id=_tag(candidate, "t19-reservation"),
        source_id=released.source_id,
        purpose=RecyclePurpose.STOP_RISK,
        amount_usd=Decimal("8"),
        ledger_store=store,
    )
    assert recycled_reservation_state(
        reservation, ledger_store=store
    ) is ReservationState.RESERVED
    released_book = release_unused_recycled_capacity(
        reservation, ledger_store=store
    )
    assert released_book.ledger.accounts[0].available_usd == Decimal("20")


def test_trader_lab_t20_capital_release(candidate_factory) -> None:
    candidate = candidate_factory(candidate_suffix=920)
    signal = _tag(candidate, "t20-signal")
    authorization = T20CapitalAuthorizationEvidence(
        evidence_id=_tag(candidate, "t20-auth"),
        decision_evidence_sha256="sha256:" + "1" * 64,
        signal_fingerprint=signal,
        position_id=7001,
        requested_at=NOW,
        requested_margin_usd=Decimal("20"),
        requested_stop_risk_usd=Decimal("2"),
        risk_decision_id=_tag(candidate, "risk"),
        risk_disposition="REDUCE",
        risk_authorized_at=NOW + timedelta(seconds=1),
        risk_authorized_margin_usd=Decimal("15"),
        risk_authorized_stop_risk_usd=Decimal("1.5"),
        execution_evidence_id=_tag(candidate, "execution"),
        execution_realized_at=NOW + timedelta(seconds=3),
        execution_realized_margin_usd=Decimal("12"),
        execution_realized_stop_risk_usd=Decimal("1.2"),
        capacity_deployed_at=NOW + timedelta(seconds=2),
        source_refs=(
            _tag(candidate, "cibo-request"),
            _tag(candidate, "qore-risk"),
            _tag(candidate, "execution-fill"),
        ),
    )
    settlement = CmaSettlementState(
        signal_fingerprint=signal,
        position_id=7001,
        records=(
            CmaSettlementRecord(
                event="CTRADER_DEMO_ENTRY_COST_SETTLEMENT",
                deal_id=8000,
                signal_fingerprint=signal,
                position_id=7001,
                net_profit_usd=Decimal("-0.10"),
                position_open_after=True,
            ),
            CmaSettlementRecord(
                event="CTRADER_DEMO_PARTIAL_SETTLEMENT",
                deal_id=8001,
                signal_fingerprint=signal,
                position_id=7001,
                net_profit_usd=Decimal("0.60"),
                position_open_after=True,
            ),
            CmaSettlementRecord(
                event="CTRADER_DEMO_EXIT_SETTLEMENT",
                deal_id=8002,
                signal_fingerprint=signal,
                position_id=7001,
                net_profit_usd=Decimal("1.50"),
                position_open_after=False,
            ),
        ),
        position_closed=True,
    )
    outcome = Phase22HistoricalReplayOutcomeSeal(
        evidence_id=_tag(candidate, "outcome"),
        decision_evidence_sha256="sha256:" + "1" * 64,
        signal_fingerprint=signal,
        trader_id="R38_EURUSD",
        qore_symbol="BTCUSD",
        observed_at=NOW + timedelta(minutes=12),
        gross_structural_outcome_r=Decimal("1.666666666666666666666666667"),
        provider_execution_adjustment_usd=Decimal("0"),
        decision_provider_cost_proxy_usd=Decimal("0"),
        realized_net_pnl_usd=Decimal("2.00"),
        executed_initial_stop_risk_usd=Decimal("1.2"),
        realized_structural_outcome_r=Decimal("1.666666666666666666666666667"),
        capital_deployed_at=NOW + timedelta(seconds=2),
        capital_released_at=NOW + timedelta(minutes=10, seconds=2),
        capital_minutes=Decimal("10"),
        provider_calibration_sha256="sha256:" + "2" * 64,
        amendment_sha256="sha256:" + "3" * 64,
        execution_economics_kind="HISTORICAL_COUNTERFACTUAL_EXECUTION_ECONOMICS",
        counterfactual_historical_replay=True,
        historical_broker_fills_claimed=False,
        fabricated_execution_evidence_used=False,
        outcome_reconciled=True,
    )
    evidence = build_t20_capital_release_evidence(
        evidence_id=_tag(candidate, "t20-release"),
        authorization=authorization,
        outcome=outcome,
        settlement=settlement,
        releases=(
            T20CapitalReleaseSlice(
                settlement_deal_id=8001,
                released_at=NOW + timedelta(minutes=4, seconds=2),
                released_stop_risk_capacity_usd=Decimal("0.4"),
                released_margin_capacity_usd=Decimal("4"),
                source_ref=_tag(candidate, "release-8001"),
                terminal=False,
            ),
            T20CapitalReleaseSlice(
                settlement_deal_id=8002,
                released_at=NOW + timedelta(minutes=10, seconds=2),
                released_stop_risk_capacity_usd=Decimal("0.8"),
                released_margin_capacity_usd=Decimal("8"),
                source_ref=_tag(candidate, "release-8002"),
                terminal=True,
            ),
        ),
        observed_at=NOW + timedelta(minutes=12),
        source_refs=(
            _tag(candidate, "phase20-outcome"),
            _tag(candidate, "cma-settlement"),
            _tag(candidate, "capital-return-ledger"),
        ),
    )
    assert evidence.terminal_capacity_reconciled is True
    assert evidence.total_released_stop_risk_capacity_usd == Decimal("1.2")
    assert evidence.total_released_margin_capacity_usd == Decimal("12")
