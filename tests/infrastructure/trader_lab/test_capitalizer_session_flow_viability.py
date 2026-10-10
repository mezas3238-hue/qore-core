from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)
from qore.infrastructure.trader_lab.capitalizer_session_flow_viability import _select


def _trade(index: int, realized: str) -> CapitalizerR0Trade:
    entry = datetime(2026, 1, 5, 1, 0, tzinfo=UTC) + timedelta(minutes=10 * index)
    return CapitalizerR0Trade(
        symbol="USDJPY",
        side=CapitalizerSide.LONG,
        signal_at=entry,
        entry_at=entry,
        exit_at=entry + timedelta(minutes=5),
        event_labels=("HIGH_ACCEPTANCE",),
        entry_price=Decimal("100"),
        stop_price=Decimal("99"),
        target_price=Decimal("102"),
        initial_risk_price=Decimal("1"),
        planned_reward_r=Decimal("2"),
        realized_gross_r=Decimal(realized),
        exit_reason="TARGET" if Decimal(realized) > 0 else "STOP",
        bars_held=1,
        same_bar_stop_target_ambiguity=False,
    )


def test_max3_accepts_three_and_rejects_fourth() -> None:
    trades = tuple(_trade(i, "1") for i in range(4))
    assert _select(trades, mode="MAX3_ANY_VALID") == trades[:3]


def test_positive_continuation_accepts_third_after_realized_profit() -> None:
    trades = tuple(_trade(i, "1") for i in range(3))
    assert _select(
        trades,
        mode="MAX3_POSITIVE_REALIZED_CONTINUATION",
    ) == trades


def test_positive_continuation_rejects_third_when_realized_pnl_nonpositive() -> None:
    trades = (_trade(0, "-1"), _trade(1, "0.5"), _trade(2, "1"))
    assert _select(
        trades,
        mode="MAX3_POSITIVE_REALIZED_CONTINUATION",
    ) == trades[:2]
