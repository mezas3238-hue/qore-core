import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_regime_selector import (
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_protected_reinvestment_policy import (
    MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
)
from qore.infrastructure.cibo_position_lifecycle import (
    CiboLifecycleFeature,
    CiboPositionLifecycleInput,
    run_cibo_position_lifecycle,
)
from qore.infrastructure.trader_lab.cibo_three_mode_capital_lab import (
    ATTACK_MINIMUM_MULTIPLIER,
    CiboThreeModeCandidate,
    CiboThreeModeOpenTrade,
    CiboTraderLabMode,
    CiboTraderLabRegime,
    _State,
    apply_three_mode_settlement,
    dynamic_bank_seed_budget_usd,
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
        expected_edge_after_cost_usd=Decimal("1"),
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
    def test_defensive_regime_keeps_trader_entry_under_medium_management(self) -> None:
        mode = select_three_mode(
            regime=_regime(volatility=VolatilityState.DISLOCATED),
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.1"),
            cushion_available_usd=Decimal("100"),
            best_candidate=_candidate(),
        )
        self.assertIs(mode, CiboTraderLabMode.MEDIUM)

    def test_drawdown_blocks_attack_but_keeps_medium_working(self) -> None:
        candidate = _candidate()
        mode = select_three_mode(
            regime=_regime(),
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.60"),
            cushion_available_usd=Decimal("100"),
            best_candidate=candidate,
        )
        self.assertIs(mode, CiboTraderLabMode.MEDIUM)

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

    def test_portfolio_enables_attack_once_cushion_can_fund_two_x(self) -> None:
        candidate = _candidate()
        mode = select_three_mode(
            regime=_regime(),
            risk_utilization=Decimal("0.1"),
            margin_utilization=Decimal("0.1"),
            drawdown_utilization=Decimal("0.1"),
            cushion_available_usd=Decimal("3.00"),
            best_candidate=candidate,
        )
        self.assertIs(mode, CiboTraderLabMode.ATTACK)

    def test_attack_requires_portfolio_cushion_and_favorable_context(self) -> None:
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
        state = _State(
            sovereign_reserved_usd=Decimal("1.1"),
            bank_seed_reserved_usd=Decimal("1.1"),
        )
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


    def test_adverse_loss_cut_requires_persistent_closed_bar_deterioration(self) -> None:
        entry_at = datetime(2026, 1, 1, tzinfo=UTC)
        position = CiboPositionLifecycleInput(
            signal_fingerprint="persistent-loss-cut",
            side="long",
            entry_at=entry_at,
            horizon_at=entry_at + timedelta(minutes=20),
            entry_price=Decimal("100"),
            structural_stop=Decimal("90"),
            technical_target=Decimal("120"),
            provider_cost_per_volume_usd=Decimal("0"),
            stop_risk_per_volume_usd=Decimal("10"),
            original_settlement_gross_r=Decimal("1"),
        )

        class Bar:
            def __init__(self, minute, open_, high, low, close):
                self.opened_at = entry_at + timedelta(minutes=minute)
                self.closed_at = self.opened_at + timedelta(minutes=5)
                self.open = Decimal(open_)
                self.high = Decimal(high)
                self.low = Decimal(low)
                self.close = Decimal(close)

        transient = (
            Bar(0, "100", "100", "91", "92"),
            Bar(5, "92", "96", "91", "96"),
            Bar(10, "96", "99", "95", "98"),
        )
        preserved = run_cibo_position_lifecycle(
            position,
            transient,
            features=frozenset({CiboLifecycleFeature.ADVERSE_LOSS_CUT}),
            adverse_loss_cut_r=Decimal("-0.75"),
            adverse_loss_cut_confirmation_bars=2,
        )
        self.assertEqual(preserved.gross_r, Decimal("1"))
        self.assertNotIn("ADVERSE_LOSS_CUT_NEXT_OPEN", preserved.actions)

        persistent = (
            Bar(0, "100", "100", "91", "92"),
            Bar(5, "92", "95", "90.5", "91"),
            Bar(10, "91.5", "93", "91", "92"),
        )
        cut = run_cibo_position_lifecycle(
            position,
            persistent,
            features=frozenset({CiboLifecycleFeature.ADVERSE_LOSS_CUT}),
            adverse_loss_cut_r=Decimal("-0.75"),
            adverse_loss_cut_confirmation_bars=2,
        )
        self.assertEqual(cut.gross_r, Decimal("-0.85"))
        self.assertEqual(cut.actions, ("ADVERSE_LOSS_CUT_NEXT_OPEN",))

    def test_dynamic_bank_seed_is_four_percent_per_entry(self) -> None:
        self.assertEqual(
            MAX_CAPITAL_NEED_TO_CURRENT_CAPITAL_RATIO,
            Decimal("0.04"),
        )
        self.assertEqual(
            dynamic_bank_seed_budget_usd(Decimal("60")),
            Decimal("2.40"),
        )
        self.assertEqual(
            dynamic_bank_seed_budget_usd(Decimal("600")),
            Decimal("24.00"),
        )
        # The helper is called for every MEDIUM candidate, so two entries
        # at USD60 each receive their own USD2.40 seed envelope.
        self.assertEqual(
            dynamic_bank_seed_budget_usd(Decimal("60"))
            + dynamic_bank_seed_budget_usd(Decimal("60")),
            Decimal("4.80"),
        )

    def test_bank_never_owns_a_trade(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        state = _State()
        trade = CiboThreeModeOpenTrade(
            signal_fingerprint="bank-cannot-trade",
            trader_id="VT31_NAS100",
            mode=CiboTraderLabMode.BANK,
            multiplier=1,
            exit_at=now,
            gross_r=Decimal("1"),
            stop_risk_usd=Decimal("1"),
            margin_usd=Decimal("1"),
            provider_cost_usd=Decimal("0.1"),
            source_reserved_usd=Decimal("1.1"),
        )
        with self.assertRaisesRegex(
            ValueError,
            "BANK cannot own trades",
        ):
            apply_three_mode_settlement(state, trade)

    def test_medium_profit_creates_portfolio_attack_credit(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        state = _State(
            sovereign_reserved_usd=Decimal("1.1"),
            bank_seed_reserved_usd=Decimal("1.1"),
        )
        trade = CiboThreeModeOpenTrade(
            signal_fingerprint="medium-credit",
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
        apply_three_mode_settlement(state, trade)
        self.assertEqual(state.portfolio_attack_credit_usd, Decimal("0.95"))
        self.assertEqual(state.bank_seed_reserved_usd, Decimal("0"))
        self.assertEqual(state.bank_seed_recycled_total_usd, Decimal("1.1"))

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
