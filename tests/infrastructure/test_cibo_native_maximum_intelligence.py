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
from qore.infrastructure.cibo_executive_brain import CiboExecutiveDirectiveKind
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
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint="signal-native-max-001",
        qore_symbol="XAUUSD" if trader is TraderLineage.R34_XAUUSD else "NAS100",
        provider_symbol="XAUUSD" if trader is TraderLineage.R34_XAUUSD else "USTEC",
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
        ("cibo_context_quality_rules", ""),
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
        ("cibo_context_quality_rules", ""),
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
