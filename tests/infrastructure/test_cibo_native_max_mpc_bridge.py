from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_cognitive_scenarios import ScenarioFamily
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
    CiboObservedOpportunityState,
)
from qore.infrastructure.cibo_native_max_mpc_bridge import (
    build_native_max_mpc_inputs,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    run_native_maximum_intelligence,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
)


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
    )


def _trader_opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="native-mpc-signal",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
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
        decision_context=tuple(
            (f"ctx_native_{index:02d}", f"value-{index:02d}")
            for index in range(30)
        ),
    )


def _episode():
    opportunity = _trader_opportunity()
    consultation = consult_cibo_economic_faculties(
        decision_at=NOW,
        opportunities=(opportunity,),
        regime_state=_regime(),
    )
    return run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=_regime(),
    ).cognitive_episode


def _twin() -> CiboObservedEconomicTwin:
    opportunity = CiboObservedOpportunityState(
        option_id="native-mpc-option",
        trader_id=TraderLineage.R34_XAUUSD.value,
        qore_symbol="XAUUSD",
        known_at=NOW,
        earliest_action_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        requested_capital_usd=Decimal("1"),
        expected_net_value_usd=Decimal("0.20"),
        expected_capital_minutes=Decimal("1"),
        stop_risk_usd=Decimal("0.10"),
        margin_usd=Decimal("0.20"),
        provider_cost_usd=Decimal("0.01"),
        uncertainty_penalty=Decimal("0"),
        context_allowed=True,
        provider_viable=True,
        capital_source_eligible=True,
        evidence_sha256="sha256:" + "a" * 64,
    )
    twin = object.__new__(CiboObservedEconomicTwin)
    object.__setattr__(twin, "captured_at", NOW)
    object.__setattr__(twin, "opportunities", (opportunity,))
    return twin


def test_native_max_scenarios_become_exact_four_mpc_worlds() -> None:
    paths, schedules = build_native_max_mpc_inputs(
        episode=_episode(),
        twin=_twin(),
    )

    assert len(paths) == 4
    assert len({item.path_id for item in paths}) == 4
    assert {item.path_id for item in paths} == {
        "native-max:" + family.value for family in ScenarioFamily
    }
    assert all(len(item.steps) == 2 for item in paths)
    assert schedules[0].option_id == "native-mpc-option"
    assert schedules[0].decision_step == 1


def test_native_max_mpc_bridge_never_invents_probability_outcome_or_capacity_shock() -> None:
    paths, _ = build_native_max_mpc_inputs(
        episode=_episode(),
        twin=_twin(),
    )

    for path in paths:
        assert path.market_probability_claimed is False
        assert path.future_outcome_used is False
        for step in path.steps:
            scenario = step.scenario
            assert scenario.stop_risk_capacity_delta_usd == Decimal("0")
            assert scenario.stop_risk_usage_delta_usd == Decimal("0")
            assert scenario.margin_capacity_delta_usd == Decimal("0")
            assert scenario.margin_usage_delta_usd == Decimal("0")
            assert scenario.market_probability_claimed is False
            assert scenario.actual_future_outcome_used is False
            assert scenario.productive_authority is False


def test_native_max_mpc_bridge_preserves_distinct_cognitive_world_kinds() -> None:
    paths, _ = build_native_max_mpc_inputs(
        episode=_episode(),
        twin=_twin(),
    )

    assert len({item.world_kind for item in paths}) == 4
