from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskCapitalConstraintEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_regime import (
    build_phase20_demo_regime_state,
    phase20_demo_regime_policy_sha256,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.ctrader_demo_compat import (
    CTraderDemoAccountState,
    CTraderDemoSymbolSpecification,
)
from qore.infrastructure.m5_boundary_cache import M5BoundarySnapshot
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)

DECISION = datetime(2026, 9, 27, 19, 0, tzinfo=UTC)
SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "GBPJPY", "AUDJPY")


class _ProviderBudget:
    provider_headroom = Decimal("1000")
    max_risk_at_any_time = Decimal("1000")
    active_mll = Decimal("0")
    hard_breach = False


def _bars(
    symbol_index: int,
    *,
    recent_multiplier: Decimal = Decimal("1"),
) -> tuple[Bar, ...]:
    rows: list[Bar] = []
    base = Decimal("100") + Decimal(symbol_index * 10)
    for index in range(100):
        opened = DECISION - timedelta(minutes=5 * (100 - index))
        drift = Decimal(index) / Decimal("1000")
        width = Decimal("0.20")
        if index >= 88:
            width *= recent_multiplier
        close = base + drift
        rows.append(
            Bar(
                opened_at=opened,
                closed_at=opened + timedelta(minutes=5),
                open=close - Decimal("0.01"),
                high=close + width / Decimal("2"),
                low=close - width / Decimal("2"),
                close=close,
            )
        )
    return tuple(rows)


def _snapshot(
    symbol: str,
    symbol_index: int,
    *,
    observed_at: datetime = DECISION - timedelta(milliseconds=100),
    recent_multiplier: Decimal = Decimal("1"),
) -> M5BoundarySnapshot:
    bars = _bars(symbol_index, recent_multiplier=recent_multiplier)
    return M5BoundarySnapshot(
        symbol=symbol,
        anchor=DECISION,
        evidence=Evidence(symbol=symbol, digits=5, bars=bars),
        current_open=bars[-1].close,
        broker_tick_at=observed_at,
        observed_at=observed_at,
        new_bar_first_seen_at=observed_at,
        market_state_updated_at=observed_at,
        aggregate_finished_at=observed_at,
        complete_bars=bars,
        h1=(),
        h4=(),
        d1=(),
    )


def _spec(
    symbol: str,
    *,
    observed_at: datetime = DECISION - timedelta(milliseconds=100),
) -> CTraderDemoSymbolSpecification:
    mid = Decimal("100")
    return CTraderDemoSymbolSpecification(
        provider_symbol=symbol,
        bid=mid - Decimal("0.005"),
        ask=mid + Decimal("0.005"),
        spread_points=Decimal("1"),
        digits=3,
        point=Decimal("0.01"),
        contract_size=Decimal("1"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("100"),
        volume_step=Decimal("1"),
        minimum_stop_distance_points=Decimal("1"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("10"),
        trade_enabled=True,
        session_open=True,
        observed_at=observed_at,
        open_commission_per_lot_usd=Decimal("0"),
    )


def _account() -> CTraderDemoAccountState:
    return CTraderDemoAccountState(
        balance=Decimal("1000"),
        equity=Decimal("980"),
        margin=Decimal("100"),
        free_margin=Decimal("880"),
        observed_at=DECISION - timedelta(milliseconds=50),
    )


def _risk_snapshot() -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id="demo-regime",
        equity=Decimal("980"),
        margin_used=Decimal("100"),
        free_margin=Decimal("880"),
        open_stop_worst_case_loss=Decimal("50"),
        open_floating_loss=Decimal("20"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("980"),
        provider_budget=_ProviderBudget(),
        reconciled_at=DECISION - timedelta(milliseconds=50),
    )


def _constraints() -> RiskCapitalConstraintEnvelope:
    return RiskCapitalConstraintEnvelope(
        account_binding_id="demo-regime",
        aggregate_pre_order_worst_case_usd=Decimal("50"),
        active_reserved_stop_risk_usd=Decimal("0"),
        active_reserved_margin_usd=Decimal("0"),
        provider_remaining_headroom_usd=Decimal("930"),
        internal_qore_remaining_headroom_usd=Decimal("930"),
        max_risk_remaining_usd=Decimal("930"),
        hard_risk_headroom_usd=Decimal("930"),
        margin_headroom_usd=Decimal("880"),
        provider_hard_breach=False,
        survival_blocked=False,
        reason="demo-regime-test",
        reconciled_at=DECISION - timedelta(milliseconds=50),
    )


def test_demo_regime_uses_only_current_causal_evidence() -> None:
    state = build_phase20_demo_regime_state(
        decision_at=DECISION,
        opportunity_count=2,
        snapshots=tuple(
            _snapshot(symbol, index)
            for index, symbol in enumerate(SYMBOLS)
        ),
        provider_specs=tuple(_spec(symbol) for symbol in SYMBOLS),
        account_state=_account(),
        risk_snapshot=_risk_snapshot(),
        risk_constraints=_constraints(),
        highest_closed_balance=Decimal("1000"),
    )

    assert state.provider_condition is ProviderCondition.HEALTHY
    assert state.liquidity is LiquidityState.NORMAL
    assert state.volatility is VolatilityState.NORMAL
    assert state.opportunity_count == 2
    assert state.risk_utilization == Decimal("50") / Decimal("980")
    assert state.margin_utilization == Decimal("100") / Decimal("980")
    assert state.drawdown_utilization == Decimal("0.02")
    assert state.evidence_stale is False
    assert phase20_demo_regime_policy_sha256().startswith("sha256:")
    assert len(phase20_demo_regime_policy_sha256()) == 71


def test_demo_regime_marks_stale_evidence_fail_closed() -> None:
    stale_at = DECISION - timedelta(seconds=3)
    state = build_phase20_demo_regime_state(
        decision_at=DECISION,
        opportunity_count=0,
        snapshots=tuple(
            _snapshot(symbol, index, observed_at=stale_at)
            for index, symbol in enumerate(SYMBOLS)
        ),
        provider_specs=tuple(
            _spec(symbol, observed_at=stale_at)
            for symbol in SYMBOLS
        ),
        account_state=_account(),
        risk_snapshot=_risk_snapshot(),
        risk_constraints=_constraints(),
        highest_closed_balance=Decimal("1000"),
    )

    assert state.evidence_stale is True


def test_demo_regime_detects_dislocated_recent_volatility() -> None:
    state = build_phase20_demo_regime_state(
        decision_at=DECISION,
        opportunity_count=1,
        snapshots=tuple(
            _snapshot(
                symbol,
                index,
                recent_multiplier=(
                    Decimal("3")
                    if symbol == "XAUUSD"
                    else Decimal("1")
                ),
            )
            for index, symbol in enumerate(SYMBOLS)
        ),
        provider_specs=tuple(_spec(symbol) for symbol in SYMBOLS),
        account_state=_account(),
        risk_snapshot=_risk_snapshot(),
        risk_constraints=_constraints(),
        highest_closed_balance=Decimal("1000"),
    )

    assert state.volatility is VolatilityState.DISLOCATED
