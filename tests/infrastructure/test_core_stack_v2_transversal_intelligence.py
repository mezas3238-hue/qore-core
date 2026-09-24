from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2 import (
    CognitiveState,
    JourneyDisposition,
    MarketStabilityEvidence,
    PositionJourneyEvidence,
    StabilityMode,
    TraderStabilityTelemetry,
    assess_drawdown_stability,
    assess_position_journey,
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
