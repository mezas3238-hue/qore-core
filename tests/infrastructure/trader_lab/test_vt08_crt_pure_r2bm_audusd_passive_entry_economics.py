from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    EntryArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bm_audusd_passive_entry_economics import (
    BE_TRIGGER_R,
    COST_STRESS_R,
    IDENTITY,
    TARGET_R,
    _find_fill,
)


def _bar(*, low: int, high: int) -> SimpleNamespace:
    return SimpleNamespace(low_price=low, high_price=high)


def test_r2bm_contract_is_frozen_from_r2bk() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BM_AUDUSD_PASSIVE_ENTRY_ECONOMICS_001"
    assert TARGET_R == 1.5
    assert BE_TRIGGER_R == 0.75
    assert COST_STRESS_R == (0.02, 0.05)
    assert tuple(EntryArm) == (
        EntryArm.NEXT_OPEN_CONTROL,
        EntryArm.CONF_BODY_MID,
        EntryArm.CONF_RANGE_MID,
        EntryArm.SOURCE_OPEN,
    )


def test_r2bm_pending_order_is_killed_by_prior_structural_stop() -> None:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    fill, state = _find_fill(
        arm=EntryArm.SOURCE_OPEN,
        level=100,
        stop=90,
        bullish=True,
        decision_at=start,
        c3_closed_at=start.replace(hour=16),
        m5_by_time={
            start: _bar(low=89, high=95),
        },
    )
    assert fill is None
    assert state == "STOP_INVALIDATED_BEFORE_FILL"


def test_r2bm_same_m5_fill_and_stop_is_conservative_fill_then_stop() -> None:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    fill, state = _find_fill(
        arm=EntryArm.SOURCE_OPEN,
        level=100,
        stop=90,
        bullish=True,
        decision_at=start,
        c3_closed_at=start.replace(hour=16),
        m5_by_time={
            start: _bar(low=89, high=101),
        },
    )
    assert fill == start
    assert state == "FILL_AND_STOP_SAME_M5"
