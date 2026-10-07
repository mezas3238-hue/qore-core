from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.trader_lab.cibo_three_mode_capital_lab import (
    ATTACK_MINIMUM_MULTIPLIER,
    CiboThreeModeCandidate,
    CiboThreeModeOpenTrade,
    CiboTraderLabMode,
    CiboTraderLabRegime,
    _State,
    apply_three_mode_settlement,
    select_three_mode,
)


def _regime(**overrides):
    values = dict(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        position_path_adverse=False,
        evidence_stale=False,
    )
    values.update(overrides)
    return CiboTraderLabRegime(**values)


def _candidate() -> CiboThreeModeCandidate:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return CiboThreeModeCandidate(
        signal_fingerprint="s1",
        trader_id="VT31_NAS100",
        decision_at=now,
        exit_at=now,
        gross_r=Decimal("2"),
        expected_net_utility_usd=Decimal("1"),
        expected_capital_minutes=Decimal("10"),
        minimum_volume=Decimal("1"),
        maximum_multiplier=10,
        stop_risk_per_multiplier_usd=Decimal("1"),
        margin_per_multiplier_usd=Decimal("1"),
        provider_cost_per_multiplier_usd=Decimal("0.1"),
        context_allowed=True,
    )


def test_bank_protects_when_regime_is_defensive() -> None:
    mode = select_three_mode(
        regime=_regime(volatility=VolatilityState.DISLOCATED),
        risk_utilization=Decimal("0.1"),
        margin_utilization=Decimal("0.1"),
        drawdown_utilization=Decimal("0.1"),
        cushion_available_usd=Decimal("100"),
        best_candidate=_candidate(),
    )
    assert mode is CiboTraderLabMode.BANK


def test_medium_builds_until_cushion_can_fund_two_x() -> None:
    candidate = _candidate()
    mode = select_three_mode(
        regime=_regime(),
        risk_utilization=Decimal("0.1"),
        margin_utilization=Decimal("0.1"),
        drawdown_utilization=Decimal("0.1"),
        cushion_available_usd=Decimal("2.19"),
        best_candidate=candidate,
    )
    assert ATTACK_MINIMUM_MULTIPLIER == 2
    assert mode is CiboTraderLabMode.MEDIUM


def test_attack_requires_and_uses_cushion() -> None:
    candidate = _candidate()
    mode = select_three_mode(
        regime=_regime(),
        risk_utilization=Decimal("0.1"),
        margin_utilization=Decimal("0.1"),
        drawdown_utilization=Decimal("0.1"),
        cushion_available_usd=Decimal("2.20"),
        best_candidate=candidate,
    )
    assert mode is CiboTraderLabMode.ATTACK


def test_medium_positive_profit_splits_fifty_fifty() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = _State(sovereign_reserved_usd=Decimal("1.1"))
    trade = CiboThreeModeOpenTrade(
        signal_fingerprint="s1",
        trader_id="VT31_NAS100",
        mode=CiboTraderLabMode.MEDIUM,
        multiplier=1,
        exit_at=now,
        gross_r=Decimal("2"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("1"),
        provider_cost_usd=Decimal("0.1"),
        source_reserved_usd=Decimal("1.1"),
    )
    net = apply_three_mode_settlement(state, trade)
    assert net == Decimal("1.9")
    assert state.sovereign_bank_usd == Decimal("60.95")
    assert state.portfolio_cushion_usd == Decimal("0.95")


def test_attack_loss_is_charged_to_cushion_first() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = _State(
        portfolio_cushion_usd=Decimal("5"),
        cushion_reserved_usd=Decimal("2.2"),
    )
    trade = CiboThreeModeOpenTrade(
        signal_fingerprint="s1",
        trader_id="VT31_NAS100",
        mode=CiboTraderLabMode.ATTACK,
        multiplier=2,
        exit_at=now,
        gross_r=Decimal("-1"),
        stop_risk_usd=Decimal("2"),
        margin_usd=Decimal("2"),
        provider_cost_usd=Decimal("0.2"),
        source_reserved_usd=Decimal("2.2"),
    )
    apply_three_mode_settlement(state, trade)
    assert state.portfolio_cushion_usd == Decimal("2.8")
    assert state.sovereign_bank_usd == Decimal("60")
    assert state.attack_sovereign_breach_usd == Decimal("0")
