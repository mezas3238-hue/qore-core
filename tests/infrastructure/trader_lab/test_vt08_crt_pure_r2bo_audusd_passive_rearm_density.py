from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    EntryArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bo_audusd_passive_rearm_density import (
    ARM,
    IDENTITY,
    MAX_ATTEMPTS_PER_PARENT,
    _attempt_fill,
)


def _bar(*, low: int, high: int) -> SimpleNamespace:
    return SimpleNamespace(low_price=low, high_price=high)


def test_r2bo_contract_freezes_bm_winner_without_bj() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BO_AUDUSD_PASSIVE_REARM_DENSITY_001"
    assert ARM is EntryArm.CONF_RANGE_MID
    assert MAX_ATTEMPTS_PER_PARENT == 2


def test_r2bo_no_fill_resolves_at_frozen_horizon() -> None:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    bars = {
        start: _bar(low=101, high=110),
        start.replace(minute=5): _bar(low=101, high=110),
        start.replace(minute=10): _bar(low=101, high=110),
        start.replace(minute=15): _bar(low=101, high=110),
        start.replace(minute=20): _bar(low=101, high=110),
        start.replace(minute=25): _bar(low=101, high=110),
    }
    fill, state, resolved = _attempt_fill(
        level=100,
        stop=90,
        bullish=True,
        decision_at=start,
        c3_closed_at=start.replace(hour=16),
        m5_by_time=bars,
    )
    assert fill is None
    assert state == "NO_FILL_WITHIN_30M"
    assert resolved == start.replace(minute=30)


def test_r2bo_stop_before_fill_resolves_after_observed_m5() -> None:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    fill, state, resolved = _attempt_fill(
        level=100,
        stop=90,
        bullish=True,
        decision_at=start,
        c3_closed_at=start.replace(hour=16),
        m5_by_time={start: _bar(low=89, high=95)},
    )
    assert fill is None
    assert state == "STOP_INVALIDATED_BEFORE_FILL"
    assert resolved == start.replace(minute=5)
