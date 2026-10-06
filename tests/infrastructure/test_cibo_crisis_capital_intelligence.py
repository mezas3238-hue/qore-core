from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10EconomicBucket,
    Genc10ObservedCapitalTwin,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_dynamic_derisking import (
    CiboDeRiskAction,
    CiboDeRiskingInput,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimePosture,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_crisis_capital_intelligence import (
    GENC12_POLICY_SHA256,
    Genc12CapitalResponse,
    Genc12CrisisFact,
    Genc12CrisisFactor,
    Genc12PositionCapitalInput,
    plan_genc12_crisis_capital,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 8, 30, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="genc12-crisis",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _twin(
    *,
    used_risk: str = "2",
    total_risk: str = "10",
    used_margin: str = "20",
    total_margin: str = "100",
) -> Genc10ObservedCapitalTwin:
    buckets = tuple(
        (
            bucket,
            Decimal("100")
            if bucket is Genc10EconomicBucket.ORIGINAL_BASE
            else Decimal(0),
        )
        for bucket in Genc10EconomicBucket
    )
    used_risk_d = Decimal(used_risk)
    total_risk_d = Decimal(total_risk)
    used_margin_d = Decimal(used_margin)
    total_margin_d = Decimal(total_margin)
    with localcontext() as context:
        context.prec = 100
        risk_headroom = total_risk_d - used_risk_d
        margin_headroom = total_margin_d - used_margin_d
    return Genc10ObservedCapitalTwin(
        twin_id="crisis-twin",
        account_identity=_identity(),
        captured_at=T0,
        capital_truth_sha256="sha256:" + "1" * 64,
        compound_cycle_sha256="sha256:" + "2" * 64,
        source_ledger_sha256="sha256:" + "3" * 64,
        provider_registry_sha256="sha256:" + "4" * 64,
        total_realized_capital_usd=Decimal("100"),
        original_base_usd=Decimal("100"),
        compound_economic_value_usd=Decimal("0"),
        protected_floor_usd=Decimal("0"),
        policy_protected_floor_usd=Decimal("0"),
        broker_guaranteed_floor_usd=Decimal("0"),
        economic_buckets=buckets,
        generation_balances=(),
        source_capacities=(),
        total_stop_risk_capacity_usd=total_risk_d,
        used_stop_risk_usd=used_risk_d,
        stop_risk_headroom_usd=risk_headroom,
        total_margin_capacity_usd=total_margin_d,
        used_margin_usd=used_margin_d,
        margin_headroom_usd=margin_headroom,
        active_deployment_count=1,
        provider_capability_counts=(),
    )


def _fact(factor: Genc12CrisisFactor) -> Genc12CrisisFact:
    return Genc12CrisisFact(
        factor=factor,
        observed_at=T0,
        evidence_sha256="sha256:" + "5" * 64,
        active=True,
    )


def test_genc12_policy_digest_is_frozen() -> None:
    assert GENC12_POLICY_SHA256 == (
        "sha256:0a681561b84ffcc681674a37e93ca5629ae69b0ad8765c7f16cf05a155795d49"
    )


def test_genc12_defensive_state_preserves_minimal_seed_when_safe() -> None:
    twin = _twin()
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.2"),
        margin_utilization=Decimal("0.2"),
        drawdown_utilization=Decimal("0.55"),
        opportunity_count=2,
        position_path_adverse=False,
    )
    plan = plan_genc12_crisis_capital(
        plan_id="defensive",
        evaluated_at=T0,
        twin=twin,
        regime_state=regime,
        crisis_facts=(
            _fact(Genc12CrisisFactor.DRAWDOWN_ACCELERATION),
        ),
    )

    assert plan.posture is CiboRegimePosture.DEFENSIVE
    assert Genc12CapitalResponse.MINIMAL_SEED_ELIGIBLE in plan.responses
    assert Genc12CapitalResponse.NO_NEW_DEPLOYMENT not in plan.responses
    assert plan.risk_boundary_overridden is False
    assert plan.productive_authority is False


def test_genc12_correlation_break_removes_false_diversification_tools() -> None:
    twin = _twin(
        used_risk="8",
        total_risk="10",
        used_margin="20",
        total_margin="100",
    )
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.ELEVATED,
        correlation=CorrelationState.BREAK,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.8"),
        margin_utilization=Decimal("0.2"),
        drawdown_utilization=Decimal("0.4"),
        opportunity_count=4,
    )
    plan = plan_genc12_crisis_capital(
        plan_id="correlation-break",
        evaluated_at=T0,
        twin=twin,
        regime_state=regime,
        crisis_facts=(
            _fact(Genc12CrisisFactor.CORRELATION_CONVERGENCE),
        ),
    )

    assert plan.posture is CiboRegimePosture.RECOVERY
    for tool in ("T08", "T09", "T16", "T18"):
        assert tool in plan.blocked_ce2i_tools
    assert Genc12CapitalResponse.NO_NEW_DEPLOYMENT in plan.responses
    assert Genc12CapitalResponse.RESERVE_CAPACITY in plan.responses
    assert Genc12CapitalResponse.RELEASE_CAPACITY in plan.responses


def test_genc12_provider_unavailable_halts_new_capital() -> None:
    twin = _twin()
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.UNAVAILABLE,
        risk_utilization=Decimal("0.2"),
        margin_utilization=Decimal("0.2"),
        drawdown_utilization=Decimal("0.2"),
        opportunity_count=3,
    )
    plan = plan_genc12_crisis_capital(
        plan_id="provider-down",
        evaluated_at=T0,
        twin=twin,
        regime_state=regime,
        crisis_facts=(
            _fact(Genc12CrisisFactor.PROVIDER_DEGRADATION),
        ),
    )

    assert plan.posture is CiboRegimePosture.HALT_NEW_CAPITAL
    assert plan.enabled_ce2i_tools == ("T20",)
    assert Genc12CapitalResponse.NO_NEW_DEPLOYMENT in plan.responses
    assert Genc12CapitalResponse.RELEASE_CAPACITY in plan.responses


def test_genc12_uses_existing_t14_for_minimum_required_reduction() -> None:
    twin = _twin(
        used_risk="8",
        total_risk="10",
        used_margin="80",
        total_margin="100",
    )
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.DISLOCATED,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.8"),
        margin_utilization=Decimal("0.8"),
        drawdown_utilization=Decimal("0.8"),
        opportunity_count=2,
    )
    position = Genc12PositionCapitalInput(
        signal_fingerprint="position-a",
        evidence=CiboDeRiskingInput(
            current_volume=Decimal("1.0"),
            minimum_retained_volume=Decimal("0.1"),
            volume_step=Decimal("0.1"),
            stop_risk_per_volume_usd=Decimal("5"),
            margin_per_volume_usd=Decimal("10"),
            maximum_retained_stop_risk_usd=Decimal("3"),
            maximum_retained_margin_usd=Decimal("10"),
            methodology_position_valid=True,
        ),
    )
    plan = plan_genc12_crisis_capital(
        plan_id="derisk",
        evaluated_at=T0,
        twin=twin,
        regime_state=regime,
        crisis_facts=(
            _fact(Genc12CrisisFactor.VOLATILITY_DISLOCATION),
        ),
        positions=(position,),
    )

    assert plan.posture is CiboRegimePosture.RECOVERY
    assert len(plan.position_plans) == 1
    decision = plan.position_plans[0].decision
    assert decision.action is CiboDeRiskAction.REDUCE
    assert decision.retained_volume == Decimal("0.6")
    assert decision.released_stop_risk_usd == Decimal("2")
    assert Genc12CapitalResponse.REDUCE_EXPOSURE in plan.responses


def test_genc12_regime_utilization_must_match_digital_twin() -> None:
    twin = _twin()
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.3"),
        margin_utilization=Decimal("0.2"),
        drawdown_utilization=Decimal("0.2"),
        opportunity_count=1,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="risk utilization differs",
    ):
        plan_genc12_crisis_capital(
            plan_id="drift",
            evaluated_at=T0,
            twin=twin,
            regime_state=regime,
            crisis_facts=(),
        )


def test_genc12_regime_requires_matching_crisis_fact() -> None:
    twin = _twin()
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.STRESSED,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.2"),
        margin_utilization=Decimal("0.2"),
        drawdown_utilization=Decimal("0.2"),
        opportunity_count=1,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="lacks matching evidence facts",
    ):
        plan_genc12_crisis_capital(
            plan_id="missing-fact",
            evaluated_at=T0,
            twin=twin,
            regime_state=regime,
            crisis_facts=(),
        )


def test_genc12_rejects_future_crisis_fact() -> None:
    twin = _twin()
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.2"),
        margin_utilization=Decimal("0.2"),
        drawdown_utilization=Decimal("0.2"),
        opportunity_count=1,
    )
    future = Genc12CrisisFact(
        factor=Genc12CrisisFactor.CAPITAL_LOCKUP,
        observed_at=T0 + timedelta(seconds=1),
        evidence_sha256="sha256:" + "6" * 64,
        active=True,
    )
    with pytest.raises(
        CiboCapitalManagementError,
        match="comes from the future",
    ):
        plan_genc12_crisis_capital(
            plan_id="future",
            evaluated_at=T0,
            twin=twin,
            regime_state=regime,
            crisis_facts=(future,),
        )

def test_genc12_frozen_engine_accepts_historical_causal_regime() -> None:
    from dataclasses import replace

    historical_at = datetime(2021, 1, 4, 12, 0, tzinfo=UTC)
    twin = replace(_twin(), captured_at=historical_at)
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0.2"),
        margin_utilization=Decimal("0.2"),
        drawdown_utilization=Decimal("0.55"),
        opportunity_count=2,
    )
    fact = replace(
        _fact(Genc12CrisisFactor.DRAWDOWN_ACCELERATION),
        observed_at=historical_at,
    )

    plan = plan_genc12_crisis_capital(
        plan_id="historical-crisis",
        evaluated_at=historical_at,
        twin=twin,
        regime_state=regime,
        crisis_facts=(fact,),
    )

    assert plan.evaluated_at == historical_at
    assert plan.posture is CiboRegimePosture.DEFENSIVE
    assert plan.future_outcome_used is False




def test_genc12_long_decimal_utilization_matches_twin_exactly() -> None:
    used_risk = Decimal("1.2345678901234567890123456789012345678901")
    total_risk = Decimal("9.8765432109876543210987654321098765432109")
    used_margin = Decimal("2.3456789012345678901234567890123456789012")
    total_margin = Decimal("19.876543210987654321098765432109876543210")
    with localcontext() as context:
        context.prec = 100
        risk_utilization = used_risk / total_risk
        margin_utilization = used_margin / total_margin

    twin = _twin(
        used_risk=format(used_risk, "f"),
        total_risk=format(total_risk, "f"),
        used_margin=format(used_margin, "f"),
        total_margin=format(total_margin, "f"),
    )
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=risk_utilization,
        margin_utilization=margin_utilization,
        drawdown_utilization=Decimal("0"),
        opportunity_count=1,
    )

    plan = plan_genc12_crisis_capital(
        plan_id="long-decimal-utilization",
        evaluated_at=T0,
        twin=twin,
        regime_state=regime,
        crisis_facts=(),
    )

    assert plan.risk_boundary_overridden is False
    assert plan.future_outcome_used is False
