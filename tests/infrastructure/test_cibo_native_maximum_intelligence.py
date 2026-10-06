from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveDirectiveKind,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    run_native_maximum_intelligence,
    validate_native_maximum_perception,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
)
from qore.modules.cibo.cognitive_contracts import CiboReasoningMode

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _regime() -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.10"),
        margin_utilization=Decimal("0.10"),
        drawdown_utilization=Decimal("0.05"),
        opportunity_count=1,
        position_path_adverse=False,
        evidence_stale=False,
    )


def _opportunity(
    trader: TraderLineage,
    context: tuple[tuple[str, str], ...],
    *,
    qore_symbol: str | None = None,
    provider_symbol: str | None = None,
) -> TraderOpportunityEnvelope:
    default_symbol = (
        "XAUUSD" if trader is TraderLineage.R34_XAUUSD else "NAS100"
    )
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint="signal-native-max-001",
        qore_symbol=qore_symbol or default_symbol,
        provider_symbol=provider_symbol or default_symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("103"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
        decision_context=context,
    )


def test_native_max_intelligence_is_provider_free_and_max_mode() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    )
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.native_only is True
    assert result.external_ai_call_count == 0
    assert result.external_reasoning_provider_used is False
    assert result.synthesis.reasoning_mode is CiboReasoningMode.MAX
    assert result.synthesis.directive is CiboExecutiveDirectiveKind.RECOMMEND
    assert result.applicable_faculty_count == 16
    assert result.not_applicable_faculty_count == 3
    assert result.semantic_digest.startswith("sha256:")


def test_native_max_intelligence_rejects_fractional_vt31_perception() -> None:
    opportunity = _opportunity(
        TraderLineage.VT31_NAS100,
        tuple((f"ctx_{index}", "x") for index in range(7)),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="VT31 native M1/H1/H4 perception is incomplete",
    ):
        validate_native_maximum_perception((opportunity,))


def test_native_max_intelligence_rejects_vt08_without_native_surface() -> None:
    opportunity = _opportunity(
        TraderLineage.VT08_FOREX,
        tuple((f"ctx_{index}", "x") for index in range(8)),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="VT08 native perception incomplete",
    ):
        validate_native_maximum_perception((opportunity,))


def test_native_max_consumes_context_quality_semantics_into_abstention() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    ) + (
        ("cibo_context_quality_disposition", "ABSTAIN"),
        ("cibo_context_quality_rules", "RULE_A"),
        ("cibo_context_quality_hard_gate_authorized", "true"),
        ("cibo_expectation_basis", "FROZEN_HISTORICAL_PRIOR"),
        ("cibo_expected_value_usd", "1.25"),
        ("cibo_expected_net_utility_usd", "1.00"),
        ("cibo_expected_capital_minutes", "30"),
    )
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.synthesis.directive is CiboExecutiveDirectiveKind.ABSTAIN
    assert result.cognitive_episode.abstention_required is True
    assert result.cognitive_episode.calibration.note == "context-quality-abstention"
    assert result.cognitive_episode.decision_gate_codes == ("CF16",)


def test_native_max_consumes_nonpositive_expected_value_into_abstention() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    ) + (
        ("cibo_context_quality_disposition", "ALLOW"),
        ("cibo_context_quality_rules", "none"),
        ("cibo_expectation_basis", "FROZEN_HISTORICAL_PRIOR"),
        ("cibo_expected_value_usd", "1.25"),
        ("cibo_expected_net_utility_usd", "0"),
        ("cibo_expected_capital_minutes", "30"),
    )
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.synthesis.directive is CiboExecutiveDirectiveKind.ABSTAIN
    assert result.cognitive_episode.abstention_required is True
    assert (
        result.cognitive_episode.calibration.note
        == "nonpositive-causal-expected-net-utility"
    )
    assert result.cognitive_episode.decision_gate_codes == ("CF07",)


def test_native_max_positive_context_remains_recommend_without_fake_gate() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    ) + (
        ("cibo_context_quality_disposition", "ALLOW"),
        ("cibo_context_quality_rules", "none"),
        ("cibo_expectation_basis", "FROZEN_HISTORICAL_PRIOR"),
        ("cibo_expected_value_usd", "1.25"),
        ("cibo_expected_net_utility_usd", "1.00"),
        ("cibo_expected_capital_minutes", "30"),
    )
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.synthesis.directive is CiboExecutiveDirectiveKind.RECOMMEND
    assert result.cognitive_episode.abstention_required is False
    assert result.cognitive_episode.decision_gate_codes == ()


def _walk_forward_confidence_context(*, mature: bool) -> tuple[tuple[str, str], ...]:
    return (
        ("cibo_context_quality_disposition", "ALLOW"),
        ("cibo_context_quality_rules", "none"),
        ("cibo_context_quality_hard_gate_authorized", "false"),
        ("cibo_expectation_basis", "WALK_FORWARD_EMPIRICAL_FORECAST"),
        ("cibo_expected_value_usd", "1.25"),
        ("cibo_expected_net_utility_usd", "1.00"),
        ("cibo_expected_capital_minutes", "30"),
        ("cibo_walk_forward_observation_count", "25" if mature else "10"),
        ("cibo_walk_forward_maturity", "MATURE" if mature else "PROVISIONAL"),
        (
            "cibo_walk_forward_mature_for_capital_consideration",
            "true" if mature else "false",
        ),
        ("cibo_walk_forward_positive_block_count", "4"),
        ("cibo_walk_forward_nonpositive_block_count", "1"),
        ("cibo_walk_forward_block_dispersion_r", "1.25"),
        ("cibo_walk_forward_median_absolute_deviation_r", "0.20"),
        ("cibo_walk_forward_maturity_fraction", "1" if mature else "0.4"),
        ("cibo_walk_forward_evidence_age_minutes", "15"),
    )


def test_native_max_abstains_on_provisional_walk_forward_forecast() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    ) + _walk_forward_confidence_context(mature=False)
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.synthesis.directive is CiboExecutiveDirectiveKind.ABSTAIN
    assert result.cognitive_episode.abstention_required is True
    assert (
        result.cognitive_episode.calibration.note
        == "walk-forward-provisional-forecast-history-required"
    )
    assert result.cognitive_episode.calibration.confidence_band == 40
    assert result.cognitive_episode.decision_gate_codes == ("CF07",)


def test_native_max_admits_mature_positive_walk_forward_forecast() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    ) + _walk_forward_confidence_context(mature=True)
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.synthesis.directive is CiboExecutiveDirectiveKind.RECOMMEND
    assert result.cognitive_episode.abstention_required is False
    assert result.cognitive_episode.calibration.confidence_band == 90
    assert result.cognitive_episode.decision_gate_codes == ()


def test_native_max_perception_accepts_universal_trader_market_contract() -> None:
    opportunity = _opportunity(
        TraderLineage("UNIVERSAL_TRADER_001"),
        (
            ("cibo_native_perception_complete", "true"),
            ("cibo_native_perception_version", "universal-v1"),
            ("source_context_causal", "true"),
            ("market_structure_state", "balanced"),
        ),
        qore_symbol="BTCUSD",
        provider_symbol="BTC-USD",
    )

    counts = validate_native_maximum_perception((opportunity,))

    assert counts == (("signal-native-max-001", 4),)
    assert opportunity.trader_id.value == "UNIVERSAL_TRADER_001"
    assert opportunity.qore_symbol == "BTCUSD"
    assert opportunity.provider_symbol == "BTC-USD"


def test_native_max_perception_rejects_incomplete_universal_contract() -> None:
    opportunity = _opportunity(
        TraderLineage("UNIVERSAL_TRADER_002"),
        (
            ("cibo_native_perception_complete", "true"),
            ("cibo_native_perception_version", "universal-v1"),
        ),
        qore_symbol="ES",
        provider_symbol="ESZ6",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="universal native perception contract incomplete",
    ):
        validate_native_maximum_perception((opportunity,))


def test_native_max_treats_burned_context_abstain_as_advisory() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    ) + (
        ("cibo_context_quality_disposition", "ABSTAIN"),
        ("cibo_context_quality_rules", "RULE_A"),
        ("cibo_context_quality_research_mode", (
            "NON_CERTIFYING_REUSED_HOLDOUT_ADAPTIVE_RESEARCH"
        )),
        ("cibo_context_quality_hard_gate_authorized", "false"),
        ("cibo_expectation_basis", "FROZEN_HISTORICAL_PRIOR"),
        ("cibo_expected_value_usd", "1.25"),
        ("cibo_expected_net_utility_usd", "1.00"),
        ("cibo_expected_capital_minutes", "30"),
    )
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.synthesis.directive is CiboExecutiveDirectiveKind.RECOMMEND
    assert result.cognitive_episode.abstention_required is False
    assert result.cognitive_episode.decision_gate_codes == ()


def test_native_max_distinguishes_walk_forward_cold_start() -> None:
    context = tuple(
        (f"ctx_native_{index:02d}", f"value-{index:02d}")
        for index in range(30)
    ) + (
        ("cibo_context_quality_disposition", "ALLOW"),
        ("cibo_context_quality_rules", "none"),
        ("cibo_context_quality_hard_gate_authorized", "false"),
        ("cibo_expectation_basis", "COLD_START_NO_FORECAST"),
        ("cibo_expected_value_usd", "0"),
        ("cibo_expected_net_utility_usd", "-0.10"),
        ("cibo_expected_capital_minutes", "1"),
    )
    opportunity = _opportunity(TraderLineage.R34_XAUUSD, context)
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )

    result = run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    )

    assert result.synthesis.directive is CiboExecutiveDirectiveKind.ABSTAIN
    assert result.cognitive_episode.abstention_required is True
    assert (
        result.cognitive_episode.calibration.note
        == "walk-forward-cold-start-history-required"
    )
    assert result.cognitive_episode.decision_gate_codes == ("CF07",)
