from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2 import (
    CognitiveState,
    JourneyDisposition,
    MarketEnvironmentObservation,
    MarketEnvironmentState,
    MarketStabilityEvidence,
    MarketTrajectoryState,
    MarketTransitionObservation,
    PositionJourneyEvidence,
    PositionPathObservation,
    PositionPathState,
    StabilityMode,
    TraderStabilityTelemetry,
    assess_drawdown_stability,
    assess_market_environment,
    assess_market_trajectory,
    assess_position_journey,
    assess_position_path,
    superintelligence_freeze_contract,
)

NOW = datetime(2026, 9, 24, 16, 30, tzinfo=UTC)


def _market(**overrides: object) -> MarketStabilityEvidence:
    values: dict[str, object] = {
        "as_of": NOW,
        "regime": "TREND_EXPANSION",
        "transition": "STABLE",
        "uncertainty_bps": 1500,
        "contradiction_bps": 1000,
        "cross_market_confirmation_bps": 8500,
        "failure_hypothesis_bps": 1500,
        "continuation_support_bps": 8000,
        "anomaly_bps": 500,
    }
    values.update(overrides)
    return MarketStabilityEvidence(**values)  # type: ignore[arg-type]


def _telemetry(**overrides: object) -> TraderStabilityTelemetry:
    values: dict[str, object] = {
        "trader_id": "GENERIC_TRADER",
        "as_of": NOW,
        "last_closed_trade_at": NOW - timedelta(minutes=5),
        "current_drawdown_r": Decimal("1.0"),
        "drawdown_velocity_r": Decimal("-0.2"),
        "recovery_from_trough_r": Decimal("0.8"),
        "recent_trade_count": 10,
        "recent_loss_count": 3,
        "recent_net_r": Decimal("2.1"),
        "max_single_trade_risk_r": Decimal("1"),
    }
    values.update(overrides)
    return TraderStabilityTelemetry(**values)  # type: ignore[arg-type]


def test_owner_scope_freezes_shared_as_qore_wide_not_vt31_module() -> None:
    contract = superintelligence_freeze_contract()
    scope = contract["transversal_scope"]
    ontology = contract["generic_ontology_law"]
    validation = contract["multi_trader_validation"]

    assert isinstance(scope, dict)
    assert scope["shared_core_is_qore_wide"] is True
    assert scope["shared_core_is_not_a_vt31_module"] is True
    assert scope["vt31_role"] == "PRIMARY_FALSIFICATION_LAB_ONLY"
    assert scope["all_enabled_traders_may_consume_shared_context"] is True
    assert scope["same_market_context_may_yield_different_trader_decisions"] is True

    assert isinstance(ontology, dict)
    assert ontology["trader_specific_ontology_forbidden_in_shared_core"] is True
    assert ontology["vt31_specific_concepts_belong_in_adapter_or_lab"] is True

    assert isinstance(validation, dict)
    assert validation["required_after_vt31"] is True
    assert validation["vt31_pass_is_not_global_completion"] is True
    assert validation["must_include_different_methodologies"] is True


def test_owner_freeze_requires_third_eye_pf_density_and_sub4_aspiration() -> None:
    contract = superintelligence_freeze_contract()
    scope = contract["transversal_scope"]
    essential = contract["shared_essential_intelligence"]
    north_star = essential["owner_economic_north_star"]

    assert scope["shared_is_third_eye_cognitive_support_for_every_enabled_trader"] is True
    assert scope["shared_must_support_full_market_lifecycle_not_only_entry_filtering"] is True
    assert essential["profit_factor"]["must_increase_vs_same_trader_baseline"] is True
    assert north_star["drawdown_acceptable_band_r"] == ("4", "6")
    assert north_star["drawdown_below_4r_is_preferred_when_pf_and_density_are_preserved"] is True
    assert north_star["density_must_be_preserved"] is True
    assert north_star["mass_abstention_is_not_intelligence"] is True
    assert north_star["risk_or_sizing_compression_cannot_claim_shared_success"] is True


def test_generic_shared_modules_do_not_embed_vt31_methodology_ontology() -> None:
    root = Path("src/qore/infrastructure/core_stack_v2")
    generic_modules = (
        "contracts.py",
        "engine.py",
        "intelligence.py",
        "adapters.py",
        "perception_engine.py",
        "stability_intelligence.py",
        "journey_intelligence.py",
        "transition_intelligence.py",
        "environment_intelligence.py",
        "path_intelligence.py",
        "instinct_intelligence.py",
        "realtime_trade_management.py",
    )
    forbidden = (
        "silver_bullet",
        "vt31",
        "nas100",
        "09:00",
        "10:00_reference",
        "breaker",
        "fair_value_gap",
    )
    for name in generic_modules:
        content = (root / name).read_text().lower()
        for token in forbidden:
            assert token not in content, f"{name} contains trader-specific token {token}"


def test_stability_cognition_is_trader_agnostic_and_has_no_authority() -> None:
    first = assess_drawdown_stability(_telemetry(trader_id="TRADER_A"), _market())
    second = assess_drawdown_stability(_telemetry(trader_id="TRADER_B"), _market())

    assert first.mode in {
        StabilityMode.STABLE,
        StabilityMode.RECOVERY,
    }
    assert first.cognitive_state is CognitiveState.PASS
    assert second.cognitive_state == first.cognitive_state
    assert second.trader_id == "TRADER_B"
    assert first.order_authority is False
    assert first.risk_authority is False
    assert first.sizing_authority is False
    assert first.execution_authority is False
    assert first.strategy_mutation_authority is False


def test_stability_enters_defensive_mode_at_hard_6r_ceiling() -> None:
    result = assess_drawdown_stability(
        _telemetry(
            current_drawdown_r=Decimal("6"),
            drawdown_velocity_r=Decimal("0.8"),
            recent_loss_count=8,
            recent_net_r=Decimal("-4"),
        ),
        _market(
            uncertainty_bps=8000,
            contradiction_bps=8000,
            cross_market_confirmation_bps=1500,
            failure_hypothesis_bps=8500,
            continuation_support_bps=1500,
            anomaly_bps=7000,
        ),
    )

    assert result.mode is StabilityMode.DEFENSIVE
    assert result.cognitive_state is CognitiveState.ABSTAIN
    assert "HARD_DRAWDOWN_CEILING_REACHED" in result.reasons
    assert result.headroom_to_hard_ceiling_r == Decimal("0")


def test_stability_detects_deterioration_before_hard_ceiling() -> None:
    result = assess_drawdown_stability(
        _telemetry(
            current_drawdown_r=Decimal("4.8"),
            drawdown_velocity_r=Decimal("1.2"),
            recent_loss_count=8,
            recent_net_r=Decimal("-3.5"),
        ),
        _market(
            uncertainty_bps=7500,
            contradiction_bps=8000,
            cross_market_confirmation_bps=1500,
            failure_hypothesis_bps=8500,
            continuation_support_bps=1000,
            anomaly_bps=6500,
        ),
    )

    assert result.mode is StabilityMode.DEFENSIVE
    assert result.cognitive_state is CognitiveState.ABSTAIN
    assert "CAUSAL_DETERIORATION_HIGH" in result.reasons


def test_future_closed_trade_evidence_is_forbidden() -> None:
    with pytest.raises(ValueError, match="future closed-trade evidence forbidden"):
        _telemetry(last_closed_trade_at=NOW + timedelta(seconds=1))


def test_future_market_evidence_is_forbidden() -> None:
    with pytest.raises(ValueError, match="future market evidence forbidden"):
        assess_drawdown_stability(
            _telemetry(),
            _market(as_of=NOW + timedelta(seconds=1)),
        )


def _journey(**overrides: object) -> PositionJourneyEvidence:
    values: dict[str, object] = {
        "trader_id": "GENERIC_TRADER",
        "market": "GENERIC_MARKET",
        "side": "LONG",
        "opened_at": NOW - timedelta(minutes=15),
        "as_of": NOW,
        "data_integrity_bps": 9500,
        "regime_stability_bps": 8500,
        "expansion_bps": 8000,
        "displacement_bps": 8000,
        "momentum_bps": 8000,
        "liquidity_capacity_bps": 8500,
        "cross_market_confirmation_bps": 8500,
        "exhaustion_bps": 1500,
        "opposite_displacement_bps": 1000,
        "contradiction_bps": 1000,
        "anomaly_bps": 500,
        "uncertainty_bps": 1000,
    }
    values.update(overrides)
    return PositionJourneyEvidence(**values)  # type: ignore[arg-type]


def test_journey_extend_requires_current_capacity_not_profit_state() -> None:
    result = assess_position_journey(_journey())

    assert result.disposition is JourneyDisposition.EXTEND
    assert "EXTENSION_CAPACITY_SUPPORTED" in result.reasons
    assert result.target_mutation_authority is False
    assert result.stop_mutation_authority is False
    assert result.stop_widening_allowed is False
    assert result.order_authority is False
    assert result.risk_authority is False
    assert result.execution_authority is False


def test_journey_defends_on_causal_deterioration() -> None:
    result = assess_position_journey(
        _journey(
            regime_stability_bps=2500,
            expansion_bps=2500,
            displacement_bps=3000,
            momentum_bps=2000,
            liquidity_capacity_bps=2500,
            cross_market_confirmation_bps=2000,
            exhaustion_bps=8000,
            opposite_displacement_bps=8500,
            contradiction_bps=8000,
            anomaly_bps=6500,
            uncertainty_bps=7500,
        )
    )

    assert result.disposition is JourneyDisposition.DEFEND
    assert "CAUSAL_POSITION_DETERIORATION" in result.reasons


def test_journey_emits_exit_risk_warning_without_execution_authority() -> None:
    result = assess_position_journey(
        _journey(
            anomaly_bps=9000,
            opposite_displacement_bps=8500,
        )
    )

    assert result.disposition is JourneyDisposition.EXIT_RISK_WARNING
    assert result.execution_authority is False
    assert result.stop_widening_allowed is False


def test_journey_is_insufficient_when_current_data_integrity_is_low() -> None:
    result = assess_position_journey(_journey(data_integrity_bps=5000))

    assert result.disposition is JourneyDisposition.INSUFFICIENT
    assert result.reasons == ("DATA_INTEGRITY_INSUFFICIENT",)

def _transition_observation(
    minutes: int,
    **overrides: object,
) -> MarketTransitionObservation:
    values: dict[str, object] = {
        "as_of": NOW + timedelta(minutes=minutes),
        "data_integrity_bps": 9800,
        "trend_support_bps": 8200,
        "momentum_bps": 8200,
        "displacement_bps": 8000,
        "liquidity_capacity_bps": 7800,
        "volatility_stability_bps": 8000,
        "cross_market_confirmation_bps": 8500,
        "correlation_stability_bps": 8500,
        "contradiction_bps": 1200,
        "anomaly_bps": 500,
        "uncertainty_bps": 1200,
        "opposite_pressure_bps": 900,
    }
    values.update(overrides)
    return MarketTransitionObservation(**values)  # type: ignore[arg-type]


def test_dynamic_transition_model_reads_sequence_not_only_snapshot() -> None:
    result = assess_market_trajectory(
        (
            _transition_observation(0),
            _transition_observation(
                1,
                trend_support_bps=7000,
                momentum_bps=6800,
                displacement_bps=6500,
                cross_market_confirmation_bps=7000,
                correlation_stability_bps=7200,
                contradiction_bps=3000,
                uncertainty_bps=3000,
                opposite_pressure_bps=3000,
            ),
            _transition_observation(
                2,
                trend_support_bps=4800,
                momentum_bps=4200,
                displacement_bps=4300,
                liquidity_capacity_bps=5000,
                volatility_stability_bps=4500,
                cross_market_confirmation_bps=4000,
                correlation_stability_bps=4200,
                contradiction_bps=6000,
                anomaly_bps=4000,
                uncertainty_bps=5600,
                opposite_pressure_bps=6200,
            ),
            _transition_observation(
                3,
                trend_support_bps=2300,
                momentum_bps=2000,
                displacement_bps=2500,
                liquidity_capacity_bps=2800,
                volatility_stability_bps=3000,
                cross_market_confirmation_bps=1500,
                correlation_stability_bps=2500,
                contradiction_bps=8500,
                anomaly_bps=7200,
                uncertainty_bps=8200,
                opposite_pressure_bps=8600,
            ),
        )
    )

    assert result.state is MarketTrajectoryState.FAILURE
    assert result.deterioration_velocity_bps > 0
    assert result.deterioration_persistence_bps >= 5500
    assert "DETERIORATION_PERSISTENT" in result.reasons
    assert result.order_authority is False
    assert result.risk_authority is False
    assert result.sizing_authority is False
    assert result.execution_authority is False
    assert result.strategy_mutation_authority is False


def test_dynamic_transition_model_detects_recovery_causally() -> None:
    result = assess_market_trajectory(
        (
            _transition_observation(
                0,
                trend_support_bps=2000,
                momentum_bps=1800,
                displacement_bps=2200,
                liquidity_capacity_bps=2600,
                volatility_stability_bps=2500,
                cross_market_confirmation_bps=1500,
                correlation_stability_bps=2500,
                contradiction_bps=8500,
                anomaly_bps=7000,
                uncertainty_bps=8000,
                opposite_pressure_bps=8500,
            ),
            _transition_observation(
                1,
                trend_support_bps=3500,
                momentum_bps=3600,
                displacement_bps=3800,
                liquidity_capacity_bps=4000,
                volatility_stability_bps=4200,
                cross_market_confirmation_bps=3800,
                correlation_stability_bps=4300,
                contradiction_bps=6200,
                anomaly_bps=5000,
                uncertainty_bps=6000,
                opposite_pressure_bps=6000,
            ),
            _transition_observation(
                2,
                trend_support_bps=5600,
                momentum_bps=5800,
                displacement_bps=6000,
                liquidity_capacity_bps=6200,
                volatility_stability_bps=6500,
                cross_market_confirmation_bps=6200,
                correlation_stability_bps=6500,
                contradiction_bps=3800,
                anomaly_bps=2600,
                uncertainty_bps=3500,
                opposite_pressure_bps=3300,
            ),
            _transition_observation(3),
        )
    )

    assert result.state is MarketTrajectoryState.RECOVERING
    assert result.recovery_velocity_bps > 0
    assert result.recovery_persistence_bps >= 5500
    assert "SUPPORT_RECOVERING" in result.reasons


def test_dynamic_transition_model_fails_closed_on_low_integrity() -> None:
    result = assess_market_trajectory(
        (
            _transition_observation(0),
            _transition_observation(1),
            _transition_observation(2, data_integrity_bps=5000),
            _transition_observation(3),
        )
    )

    assert result.state is MarketTrajectoryState.INSUFFICIENT
    assert result.reasons[0] == "TRAJECTORY_EVIDENCE_INSUFFICIENT"


def test_dynamic_transition_model_rejects_noncausal_ordering() -> None:
    with pytest.raises(
        ValueError,
        match="market observations must be strictly increasing and causal",
    ):
        assess_market_trajectory(
            (
                _transition_observation(1),
                _transition_observation(0),
                _transition_observation(2),
                _transition_observation(3),
            )
        )



def _environment_observation(minutes: int, level: int) -> MarketEnvironmentObservation:
    support = max(500, 9000 - level)
    stability = max(500, 9000 - level)
    adverse = min(9500, 1000 + level)
    return MarketEnvironmentObservation(
        as_of=NOW + timedelta(minutes=minutes),
        data_integrity_bps=9800,
        trajectory_support_bps=support,
        trajectory_adversity_bps=adverse,
        deterioration_velocity_bps=min(9500, 500 + level),
        recovery_velocity_bps=max(500, 9000 - level),
        cross_market_breadth_bps=stability,
        leadership_stability_bps=stability,
        correlation_stability_bps=stability,
        volatility_stability_bps=stability,
        liquidity_stability_bps=stability,
        regime_stability_bps=stability,
        anomaly_bps=adverse,
        uncertainty_bps=adverse,
        opposite_pressure_bps=adverse,
    )


def test_market_environment_detects_persistent_adverse_formation() -> None:
    result = assess_market_environment(
        tuple(
            _environment_observation(index, level)
            for index, level in enumerate((500, 2500, 4500, 6500, 8000))
        )
    )

    assert result.state in {
        MarketEnvironmentState.ADVERSE_FORMING,
        MarketEnvironmentState.DEFENSIVE,
    }
    assert result.adverse_persistence_bps >= 6000
    assert result.cross_market_fragility_bps >= 6000
    assert result.structural_fragility_bps >= 6000
    assert result.order_authority is False
    assert result.risk_authority is False
    assert result.sizing_authority is False
    assert result.execution_authority is False
    assert result.strategy_mutation_authority is False


def test_market_environment_detects_restoration_causally() -> None:
    observations = tuple(
        _environment_observation(index, level)
        for index, level in enumerate((8000, 6500, 4500, 2500, 500))
    )
    result = assess_market_environment(observations)

    assert result.state is MarketEnvironmentState.RESTORED
    assert result.recovery_persistence_bps >= 6000
    assert result.market_support_bps >= 6200
    assert "MARKET_SUPPORT_RESTORED" in result.reasons


def test_market_environment_fails_closed_and_rejects_noncausal_ordering() -> None:
    low = _environment_observation(2, 4500)
    low = MarketEnvironmentObservation(
        **{
            name: (5000 if name == "data_integrity_bps" else getattr(low, name))
            for name in low.__dataclass_fields__
        }
    )
    result = assess_market_environment(
        (
            _environment_observation(0, 500),
            _environment_observation(1, 2500),
            low,
            _environment_observation(3, 6500),
            _environment_observation(4, 8000),
        )
    )
    assert result.state is MarketEnvironmentState.INSUFFICIENT

    with pytest.raises(ValueError, match="strictly increasing"):
        assess_market_environment(
            (
                _environment_observation(1, 500),
                _environment_observation(0, 2500),
                _environment_observation(2, 4500),
                _environment_observation(3, 6500),
                _environment_observation(4, 8000),
            )
        )


def _path_observation(
    minutes: int,
    *,
    progress: int,
    close_support: int,
    efficiency: int,
    favorable: int,
    adverse: int,
    favorable_body: int,
    adverse_body: int,
    market_support: int,
    environment_adverse: int,
    recovery: int,
) -> PositionPathObservation:
    return PositionPathObservation(
        as_of=NOW + timedelta(minutes=minutes),
        data_integrity_bps=9800,
        journey_progress_bps=progress,
        close_support_bps=close_support,
        directional_efficiency_bps=efficiency,
        favorable_excursion_bps=favorable,
        adverse_excursion_bps=adverse,
        favorable_body_bps=favorable_body,
        adverse_body_bps=adverse_body,
        market_support_bps=market_support,
        environment_adverse_bps=environment_adverse,
        recovery_evidence_bps=recovery,
    )


def test_position_path_protects_established_winner_during_pullback() -> None:
    result = assess_position_path(
        (
            _path_observation(
                1, progress=5200, close_support=7600, efficiency=7600,
                favorable=6500, adverse=1800, favorable_body=7200,
                adverse_body=1800, market_support=7800,
                environment_adverse=2200, recovery=4200,
            ),
            _path_observation(
                2, progress=6800, close_support=8000, efficiency=8200,
                favorable=7800, adverse=2200, favorable_body=8000,
                adverse_body=2000, market_support=8000,
                environment_adverse=2500, recovery=4500,
            ),
            _path_observation(
                3, progress=7200, close_support=6200, efficiency=6000,
                favorable=8200, adverse=3600, favorable_body=5400,
                adverse_body=4200, market_support=6500,
                environment_adverse=5200, recovery=5000,
            ),
            _path_observation(
                4, progress=7200, close_support=5600, efficiency=5400,
                favorable=8200, adverse=4300, favorable_body=5000,
                adverse_body=5000, market_support=6100,
                environment_adverse=6100, recovery=5200,
            ),
        )
    )
    assert result.state in {
        PositionPathState.FAVORABLE_EXPANSION,
        PositionPathState.HEALTHY_PULLBACK,
    }
    assert result.winner_protection_bps >= 6200
    assert result.order_authority is False
    assert result.risk_authority is False
    assert result.sizing_authority is False
    assert result.execution_authority is False


def test_position_path_detects_persistent_unproven_failure_risk() -> None:
    result = assess_position_path(
        (
            _path_observation(
                1, progress=900, close_support=4200, efficiency=4300,
                favorable=1500, adverse=5200, favorable_body=3200,
                adverse_body=6100, market_support=4300,
                environment_adverse=5600, recovery=2600,
            ),
            _path_observation(
                2, progress=1200, close_support=3300, efficiency=3400,
                favorable=1800, adverse=6500, favorable_body=2600,
                adverse_body=7200, market_support=3500,
                environment_adverse=6500, recovery=2200,
            ),
            _path_observation(
                3, progress=1300, close_support=2400, efficiency=2600,
                favorable=1900, adverse=7600, favorable_body=1900,
                adverse_body=8300, market_support=2700,
                environment_adverse=7600, recovery=1800,
            ),
            _path_observation(
                4, progress=1400, close_support=1500, efficiency=1800,
                favorable=2000, adverse=8800, favorable_body=1400,
                adverse_body=9000, market_support=1900,
                environment_adverse=8600, recovery=1400,
            ),
        )
    )
    assert result.state is PositionPathState.FAILURE_RISK
    assert result.adverse_persistence_bps >= 5500
    assert result.winner_protection_bps < 6200
    assert result.terminal_failure_risk_bps >= 7200
