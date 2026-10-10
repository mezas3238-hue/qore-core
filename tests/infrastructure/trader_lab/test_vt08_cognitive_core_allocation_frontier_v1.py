from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_core_allocation_frontier_v1 import (
    CAUTIOUS_MULTIPLIER,
    MIXED_MULTIPLIER,
    SUPPORTIVE_MULTIPLIER,
    CausalTradeRow,
    FrozenStateQuality,
    _weighted_metrics,
    classify_context,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def _row(value: str, *, anchor: str = "5") -> CausalTradeRow:
    trade = ExpansionTrade(
        symbol="EURJPY",
        signal_at=datetime(2025, 1, 1, tzinfo=UTC),
        exited_at=datetime(2025, 1, 1, 1, tzinfo=UTC),
        anchor_hour_ny=int(anchor),
        side=DemoTradingSetupSide.LONG,
        entry=Decimal("160"),
        stop=Decimal("159"),
        target=Decimal("162"),
        exit_price=Decimal("160"),
        exit_reason="test",
        r_multiple=Decimal(value),
    )
    return CausalTradeRow(
        trade=trade,
        anchor=anchor,
        side="long",
        risk_ref_band="MID",
        c2_body_band="MID",
        protected_swing_age_band="FRESH",
        reference_body_alignment="WITH_SIDE",
    )


def test_context_classifier_uses_frozen_votes_only() -> None:
    table = (
        FrozenStateQuality("anchor", "5", 10, Decimal("2"), Decimal("0.2"), 1),
        FrozenStateQuality("side", "long", 10, Decimal("2"), Decimal("0.2"), 1),
    )
    context, score = classify_context(_row("-1"), table)
    assert context == "SUPPORTIVE"
    assert score == 2


def test_capital_weighting_changes_r_not_trade_count() -> None:
    table = (
        FrozenStateQuality("anchor", "5", 10, Decimal("2"), Decimal("0.2"), 1),
        FrozenStateQuality("side", "long", 10, Decimal("2"), Decimal("0.2"), 1),
    )
    rows = (_row("2"), _row("-1"))
    weighted, contexts, audit = _weighted_metrics(rows, table)
    assert weighted["sample_size"] == 2
    assert contexts == {"SUPPORTIVE": 2}
    assert audit[0]["risk_multiplier"] == format(SUPPORTIVE_MULTIPLIER, "f")
    assert weighted["total_r"] == "1.20"


def test_frozen_multipliers_are_bounded_and_nonzero() -> None:
    assert Decimal("0") < CAUTIOUS_MULTIPLIER < MIXED_MULTIPLIER
    assert MIXED_MULTIPLIER < Decimal("1")
    assert SUPPORTIVE_MULTIPLIER > Decimal("1")
    assert SUPPORTIVE_MULTIPLIER <= Decimal("1.20")
