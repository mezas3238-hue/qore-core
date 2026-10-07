import unittest
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
        attack_expected_net_utility_usd=Decimal("1"),
        expected_capital_minutes=Decimal("10"),
        walk_forward_positive_block_count=5,
        walk_forward_nonpositive_block_count=0,
        native_cognition_recommended=True,
        context_quality_disposition="ALLOW",
        minimum_volume=Decimal("1"),
        maximum_multiplier=10,
        stop_risk_per_multiplier_usd=Decimal("1"),
        margin_per_multiplier_usd=Decimal("1"),
        provider_cost_per_multiplier_usd=Decimal("0.1"),
        context_allowed=True,
    )


class CiboThreeModeCapitalLabTest(unittest.TestCase):
    def test_bank_protects_when_regime_is_defensive(self) -> None:
        mode = select_three_mode(
            regime=_regime(volatility=VolatilityState.DISLOCATED),
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.1"),
            cushion_available_usd=Decimal("100"),
            best_candidate=_candidate(),
        )
        self.assertIs(mode, CiboTraderLabMode.BANK)

    def test_medium_builds_until_cushion_can_fund_two_x(self) -> None:
        candidate = _candidate()
        mode = select_three_mode(
            regime=_regime(),
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.1"),
            cushion_available_usd=Decimal("2.19"),
            best_candidate=candidate,
        )
        self.assertEqual(ATTACK_MINIMUM_MULTIPLIER, 2)
        self.assertIs(mode, CiboTraderLabMode.MEDIUM)

    def test_cash_funded_two_x_stays_medium_when_marginal_utility_is_weak(self) -> None:
        candidate = _candidate()
        mode = select_three_mode(
            regime=_regime(),
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.1"),
            cushion_available_usd=Decimal("3.00"),
            best_candidate=candidate,
        )
        self.assertIs(mode, CiboTraderLabMode.MEDIUM)

    def test_attack_requires_cushion_and_positive_marginal_robust_utility(self) -> None:
        candidate = _candidate()
        mode = select_three_mode(
            regime=_regime(),
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.1"),
            cushion_available_usd=Decimal("5"),
            best_candidate=candidate,
        )
        self.assertIs(mode, CiboTraderLabMode.ATTACK)

    def test_medium_positive_profit_splits_fifty_fifty(self) -> None:
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
        self.assertEqual(net, Decimal("1.9"))
        self.assertEqual(state.sovereign_bank_usd, Decimal("60.95"))
        self.assertEqual(state.portfolio_cushion_usd, Decimal("0.95"))

    def test_attack_loss_is_charged_to_cushion_first(self) -> None:
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
        self.assertEqual(state.portfolio_cushion_usd, Decimal("2.8"))
        self.assertEqual(state.sovereign_bank_usd, Decimal("60"))
        self.assertEqual(state.attack_sovereign_breach_usd, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
