from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_specialist_risk_round6 as mod
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab.vt08_index_cibo_2y_management_round5 import (
    ManagedTrade,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def _signal(symbol: str, at: datetime) -> v6.CandidateSignal:
    poi = v6.SourcePoi(
        v6.PoiKind.CISD,
        Decimal("100"),
        Decimal("100"),
        at - timedelta(minutes=15),
    )
    return v6.CandidateSignal(
        symbol=symbol,
        side=DemoTradingSetupSide.LONG,
        model_kind=v6.H4ModelKind.SAME_C2,
        h4_opened_at=at - timedelta(hours=1),
        signal_at=at,
        entry=Decimal("100"),
        stop=Decimal("99"),
        target=Decimal("102.5"),
        poi=poi,
        cisd_level=Decimal("100"),
        cisd_confirmed_at=at,
        protected_swing_extreme=Decimal("99"),
    )


def _outcome(signal: v6.CandidateSignal, r: str) -> ManagedTrade:
    return ManagedTrade(
        symbol=signal.symbol,
        signal_at=signal.signal_at,
        exited_at=signal.signal_at + timedelta(minutes=15),
        r_multiple=Decimal(r),
        exit_reason="fixture",
    )


def test_round6_preserves_fixed_density_and_goal() -> None:
    assert mod.FIXED_DENSITY == 657
    assert mod.GOVERNED_PF_GOAL == Decimal("1.50")
    assert mod.GOVERNED_DD_GOAL == Decimal("6")


def test_management_cell_keys_are_coarse_and_causal() -> None:
    signal = _signal("NAS100", datetime(2017, 1, 1, tzinfo=UTC))
    assert mod._cell_key(signal, "market") == "NAS100"
    assert mod._cell_key(signal, "market-side") == "NAS100:long"


def test_governor_never_skips_trade() -> None:
    signals = (
        _signal("NAS100", datetime(2017, 1, 1, 0, 0, tzinfo=UTC)),
        _signal("SP500", datetime(2017, 1, 1, 1, 0, tzinfo=UTC)),
        _signal("US30", datetime(2017, 1, 1, 2, 0, tzinfo=UTC)),
    )
    outcomes = tuple(_outcome(signal, "-1") for signal in signals)
    governor = mod.RiskGovernor(
        nas100_weight=Decimal("1"),
        sp500_weight=Decimal("0.5"),
        us30_weight=Decimal("1"),
        warn_dd_r=Decimal("1.5"),
        warn_multiplier=Decimal("0.5"),
        hard_dd_r=Decimal("3.5"),
        hard_multiplier=Decimal("0.1"),
        loss_streak_trigger=2,
        loss_streak_multiplier=Decimal("0.25"),
    )
    values, diagnostics = mod._governed_values(
        signals,
        outcomes,
        governor=governor,
        stress=Decimal("0.05"),
    )
    assert len(values) == 3
    assert all(value < 0 for value in values)
    assert diagnostics["zero_weight_trades"] == 0
    assert Decimal(str(diagnostics["minimum_weight_used"])) > 0


def test_drawdown_governor_is_pre_trade_causal() -> None:
    signals = tuple(
        _signal("NAS100", datetime(2017, 1, 1, hour, 0, tzinfo=UTC))
        for hour in range(4)
    )
    outcomes = tuple(_outcome(signal, "-1") for signal in signals)
    governor = mod.RiskGovernor(
        nas100_weight=Decimal("1"),
        sp500_weight=Decimal("1"),
        us30_weight=Decimal("1"),
        warn_dd_r=Decimal("1.5"),
        warn_multiplier=Decimal("0.5"),
        hard_dd_r=Decimal("3.5"),
        hard_multiplier=Decimal("0.1"),
        loss_streak_trigger=99,
        loss_streak_multiplier=Decimal("1"),
    )
    values, diagnostics = mod._governed_values(
        signals,
        outcomes,
        governor=governor,
        stress=Decimal("0"),
    )
    assert values[0] == Decimal("-1")
    assert values[1] == Decimal("-1")
    assert values[2] == Decimal("-0.5")
    assert diagnostics["warn_mode_trades"] >= 1


def test_basic_metrics_profit_factor_and_drawdown() -> None:
    metrics = mod._basic_metrics(
        (Decimal("2"), Decimal("-1"), Decimal("-1"), Decimal("2"))
    )
    assert metrics["profit_factor"] == "2"
    assert metrics["max_drawdown_r"] == "2"
