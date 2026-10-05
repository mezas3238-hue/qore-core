from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    MarginEfficiencyEvidence,
    MarginExpression,
)
from qore.infrastructure.cibo_ce2i_full_surface import (
    AdvancedOpportunityEvidence,
    AdvancedPortfolioEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_robust_allocator import (
    Phase20AllocatorDisposition,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_ce2i_t02_calibration_binding import (
    build_t02_structural_leverage_evidence,
)
from qore.infrastructure.cibo_phase22_historical_policy_replay import (
    Phase22HistoricalCapitalInput,
    evaluate_phase22_historical_policy,
)
from qore.infrastructure.cibo_phase22_v4_historical_policy_replay import (
    Phase22HistoricalCapitalInput as Phase22V4HistoricalCapitalInput,
)
from qore.infrastructure.cibo_phase22_v4_historical_policy_replay import (
    evaluate_phase22_historical_policy as evaluate_phase22_v4_historical_policy,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

MARKET_AT = datetime(2015, 10, 20, 12, 0, tzinfo=UTC)
SEALED_AT = datetime(2026, 10, 1, 22, 20, tzinfo=UTC)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode()).hexdigest()


def _account() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_ref="phase22-v2-counterfactual",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _opportunity(
    trader_id: TraderLineage,
    signal: str,
    symbol: str,
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader_id,
        signal_fingerprint=signal,
        qore_symbol=symbol,
        provider_symbol="USTEC" if symbol == "NAS100" else symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )


def _input(
    trader_id: TraderLineage,
    signal: str,
    symbol: str,
) -> Phase22HistoricalCapitalInput:
    return Phase22HistoricalCapitalInput(
        opportunity=_opportunity(trader_id, signal, symbol),
        minimum_stop_risk_usd=Decimal("0.10"),
        minimum_margin_usd=Decimal("0.20"),
        concentration_group=symbol,
        concentration_risk_usd=Decimal("0.10"),
        provider_model_sha256=_sha("provider-model"),
    )





def _v4_input(
    trader_id: TraderLineage,
    signal: str,
    symbol: str,
) -> Phase22V4HistoricalCapitalInput:
    opportunity = _opportunity(trader_id, signal, symbol)
    return Phase22V4HistoricalCapitalInput(
        opportunity=opportunity,
        minimum_stop_risk_usd=Decimal("0.10"),
        minimum_margin_usd=Decimal("0.20"),
        concentration_group=symbol,
        concentration_risk_usd=Decimal("0.10"),
        provider_model_sha256=_sha("provider-model"),
    )

def _regime(count: int) -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0"),
        margin_utilization=Decimal("0"),
        drawdown_utilization=Decimal("0"),
        opportunity_count=count,
    )


def test_historical_policy_reuses_frozen_full_surface_without_time_impersonation() -> None:
    inputs = (
        _input(TraderLineage.VT31_NAS100, _sha("vt31"), "NAS100"),
        _input(TraderLineage.R43_GBPUSD, _sha("r43"), "GBPUSD"),
    )
    record = evaluate_phase22_historical_policy(
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        account_identity=_account(),
        inputs=inputs,
        regime_state=_regime(len(inputs)),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(
            ("GBPUSD", Decimal("1.80")),
            ("NAS100", Decimal("1.80")),
        ),
        current_step=0,
    )

    assert record.counterfactual_historical_replay is True
    assert record.market_decision_at.year == 2015
    assert record.replay_sealed_at.year == 2026
    assert record.full_surface.complete_registry is True
    assert record.mpc_plan.forecast_model_used is False
    assert record.allocator_decision.disposition in {
        Phase20AllocatorDisposition.ALLOCATE,
        Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION,
        Phase20AllocatorDisposition.PRESERVE_CAPACITY,
    }
    assert record.risk_authority is False
    assert record.execution_authority is False
    assert record.fingerprint().startswith("sha256:")


def test_negative_frozen_prior_can_abstain_without_retuning() -> None:
    inputs = (
        _input(TraderLineage.R38_EURUSD, _sha("eurusd"), "EURUSD"),
    )
    record = evaluate_phase22_historical_policy(
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        account_identity=_account(),
        inputs=inputs,
        regime_state=_regime(1),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("EURUSD", Decimal("1.80")),),
        current_step=0,
    )

    assert (
        record.allocator_decision.disposition
        is Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION
    )
    assert record.allocator_decision.allocation is not None
    assert (
        record.allocator_decision.allocation.selected_signal_fingerprints
        == ()
    )



def test_authorized_t03_changes_allocator_margin_before_allocation() -> None:
    signal = _sha("t03-causal-economic-effect")
    inputs = (
        _v4_input(TraderLineage.R34_XAUUSD, signal, "XAUUSD"),
    )
    evidence = AdvancedPortfolioEvidence(
        opportunities=(
            AdvancedOpportunityEvidence(
                signal_fingerprint=signal,
                margin_efficiency=MarginEfficiencyEvidence(
                    evidence_id="t03-policy-ready",
                    observed_at=MARKET_AT,
                    baseline_expression_id="spot",
                    expressions=(
                        MarginExpression(
                            expression_id="spot",
                            normalized_exposure=Decimal("1"),
                            stop_risk_usd=Decimal("0.10"),
                            margin_usd=Decimal("0.20"),
                            all_in_cost_usd=Decimal("0.01"),
                            executable=True,
                            economics_verified=True,
                        ),
                        MarginExpression(
                            expression_id="equivalent",
                            normalized_exposure=Decimal("1"),
                            stop_risk_usd=Decimal("0.10"),
                            margin_usd=Decimal("0.10"),
                            all_in_cost_usd=Decimal("0.01"),
                            executable=True,
                            economics_verified=True,
                        ),
                    ),
                    fresh_oos_utility_demonstrated=True,
                    policy_authorized=True,
                ),
            ),
        )
    )

    record = evaluate_phase22_v4_historical_policy(
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        account_identity=_account(),
        inputs=inputs,
        regime_state=_regime(1),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("XAUUSD", Decimal("1.80")),),
        current_step=0,
        advanced_evidence=evidence,
        lab_cibo_free_tool_choice=True,
        lab_allow_nonpositive_expectation=True,
    )

    effects = record.advanced_economic_application.candidate_effects
    assert len(effects) == 1
    assert effects[0].tool_code == "T03"
    assert effects[0].field_name == "margin_usd"
    assert effects[0].before_usd == Decimal("0.20")
    assert effects[0].after_usd == Decimal("0.10")
    assert record.advanced_economic_application.candidates[0].margin_usd == Decimal(
        "0.10"
    )
    assert record.allocator_decision.allocation is not None
    assert record.allocator_decision.allocation.used_margin_usd == Decimal("0.10")


def test_v4_counterfactual_replay_does_not_backdate_frozen_train_prior() -> None:
    inputs = (
        _v4_input(TraderLineage.R43_GBPUSD, _sha("clock-separation"), "GBPUSD"),
    )
    record = evaluate_phase22_v4_historical_policy(
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        account_identity=_account(),
        inputs=inputs,
        regime_state=_regime(1),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("GBPUSD", Decimal("1.80")),),
        current_step=0,
        lab_allow_nonpositive_expectation=True,
    )

    candidate = record.advanced_economic_application.candidates[0]
    assert MARKET_AT < FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at < SEALED_AT
    assert candidate.decision_as_of == SEALED_AT
    assert candidate.expectation.as_of == FROZEN_PHASE20_POLICY_CANDIDATE.frozen_at
    assert candidate.expectation.as_of > MARKET_AT
    assert candidate.expectation.as_of <= candidate.decision_as_of


def test_t03_shadow_measurement_cannot_change_allocator_economics() -> None:
    signal = _sha("t03-shadow-no-authority")
    inputs = (
        _input(TraderLineage.R34_XAUUSD, signal, "XAUUSD"),
    )
    evidence = AdvancedPortfolioEvidence(
        opportunities=(
            AdvancedOpportunityEvidence(
                signal_fingerprint=signal,
                margin_efficiency=MarginEfficiencyEvidence(
                    evidence_id="t03-shadow",
                    observed_at=MARKET_AT,
                    baseline_expression_id="spot",
                    expressions=(
                        MarginExpression(
                            expression_id="spot",
                            normalized_exposure=Decimal("1"),
                            stop_risk_usd=Decimal("0.10"),
                            margin_usd=Decimal("0.20"),
                            all_in_cost_usd=Decimal("0.01"),
                            executable=True,
                            economics_verified=True,
                        ),
                        MarginExpression(
                            expression_id="equivalent",
                            normalized_exposure=Decimal("1"),
                            stop_risk_usd=Decimal("0.10"),
                            margin_usd=Decimal("0.10"),
                            all_in_cost_usd=Decimal("0.01"),
                            executable=True,
                            economics_verified=True,
                        ),
                    ),
                ),
            ),
        )
    )

    record = evaluate_phase22_v4_historical_policy(
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        account_identity=_account(),
        inputs=inputs,
        regime_state=_regime(1),
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("XAUUSD", Decimal("1.80")),),
        current_step=0,
        advanced_evidence=evidence,
        lab_cibo_free_tool_choice=True,
        lab_allow_nonpositive_expectation=True,
    )

    assert record.advanced_economic_application.candidate_effects == ()
    assert record.advanced_economic_application.candidates[0].margin_usd == Decimal(
        "0.20"
    )
    assert record.allocator_decision.allocation is not None
    assert record.allocator_decision.allocation.used_margin_usd == Decimal("0.20")


def test_recovery_regime_blocks_t02_economic_actuation_but_keeps_engine_observable() -> None:
    signal = _sha("recovery-t02-no-economic-authority")
    input_row = _v4_input(TraderLineage.R43_GBPUSD, signal, "GBPUSD")
    evidence = build_t02_structural_leverage_evidence(
        opportunity=input_row.opportunity,
        observed_at=MARKET_AT,
        released_risk_capacity_usd=Decimal("0.10"),
    )
    assert evidence is not None
    advanced = AdvancedPortfolioEvidence(
        opportunities=(
            AdvancedOpportunityEvidence(
                signal_fingerprint=signal,
                current_volume=Decimal("0.01"),
                maximum_additional_volume=Decimal("0.01"),
                structural_leverage=evidence,
            ),
        )
    )
    recovery = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0"),
        margin_utilization=Decimal("0"),
        drawdown_utilization=Decimal("0.80"),
        opportunity_count=1,
    )
    record = evaluate_phase22_v4_historical_policy(
        market_decision_at=MARKET_AT,
        replay_sealed_at=SEALED_AT,
        account_identity=_account(),
        inputs=(input_row,),
        regime_state=recovery,
        hard_risk_headroom_usd=Decimal("3.60"),
        margin_headroom_usd=Decimal("60"),
        concentration_limit_by_group=(("GBPUSD", Decimal("1.80")),),
        current_step=0,
        advanced_evidence=advanced,
        lab_cibo_free_tool_choice=True,
        lab_allow_nonpositive_expectation=True,
    )
    assert record.full_surface.regime.posture is CiboRegimePosture.RECOVERY
    assert "T02" not in record.full_surface.regime.enabled_tools
    t02_decisions = [
        decision
        for assessment in record.full_surface.opportunity_assessments
        for decision in assessment.decisions
        if decision.tool_code == "T02"
    ]
    assert len(t02_decisions) == 1
    assert record.advanced_economic_application.candidate_effects == ()
    candidate = record.advanced_economic_application.candidates[0]
    assert candidate.stop_risk_usd == input_row.minimum_stop_risk_usd
    assert candidate.margin_usd == input_row.minimum_margin_usd