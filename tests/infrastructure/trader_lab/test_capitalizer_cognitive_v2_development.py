from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cognitive_v2_development import (
    select_development_trades,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Trade,
)


def _trade(
    *,
    index: int,
    side: CapitalizerSide,
    event: str,
) -> CapitalizerR0Trade:
    signal = datetime(2026, 1, 5, 1, 0, tzinfo=UTC) + timedelta(minutes=5 * index)
    return CapitalizerR0Trade(
        symbol="USDJPY",
        side=side,
        signal_at=signal,
        entry_at=signal,
        exit_at=signal + timedelta(minutes=5),
        event_labels=(event,),
        entry_price=Decimal("100"),
        stop_price=Decimal("99") if side is CapitalizerSide.LONG else Decimal("101"),
        target_price=Decimal("102") if side is CapitalizerSide.LONG else Decimal("98"),
        initial_risk_price=Decimal("1"),
        planned_reward_r=Decimal("2"),
        realized_gross_r=Decimal("1"),
        exit_reason="TARGET",
        bars_held=1,
        same_bar_stop_target_ambiguity=False,
    )


def test_structural_v2_blocks_repeat_and_mixed_without_touching_rejection() -> None:
    fresh = _trade(index=0, side=CapitalizerSide.LONG, event="HIGH_ACCEPTANCE")
    repeat = _trade(index=1, side=CapitalizerSide.SHORT, event="LOW_ACCEPTANCE")
    mixed = _trade(index=2, side=CapitalizerSide.LONG, event="HIGH_ACCEPTANCE")
    rejection = _trade(index=3, side=CapitalizerSide.SHORT, event="HIGH_RAID_REJECTION")
    trades = (fresh, repeat, mixed, rejection)
    state_index = {
        (fresh.signal_at.isoformat(), fresh.side): "NO_RECLAIM_FRESH",
        (repeat.signal_at.isoformat(), repeat.side): "RECLAIM_ALL_REPEAT",
        (mixed.signal_at.isoformat(), mixed.side): "RECLAIM_MIXED_FRESH",
    }

    selected, late, conflict, budget = select_development_trades(
        trades=trades,
        state_index=state_index,
        block_late_acceptance_repeat=True,
        block_journey_conflict=True,
        apply_session_ceiling=False,
    )

    assert selected == (fresh, rejection)
    assert late == 1
    assert conflict == 1
    assert budget == 0


def test_session_ceiling_is_chronological_and_never_a_quota() -> None:
    trades = tuple(
        _trade(index=index, side=CapitalizerSide.LONG, event="HIGH_ACCEPTANCE")
        for index in range(4)
    )
    state_index = {
        (trade.signal_at.isoformat(), trade.side): "NO_RECLAIM_FRESH"
        for trade in trades
    }

    selected, late, conflict, budget = select_development_trades(
        trades=trades,
        state_index=state_index,
        block_late_acceptance_repeat=False,
        block_journey_conflict=False,
        apply_session_ceiling=True,
    )

    assert selected == trades[:3]
    assert late == 0
    assert conflict == 0
    assert budget == 1
