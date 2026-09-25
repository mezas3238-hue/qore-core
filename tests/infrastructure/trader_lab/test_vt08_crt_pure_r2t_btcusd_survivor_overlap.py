from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_r2t_btcusd_survivor_overlap import (
    B2,
    B3,
    B4,
    END,
    START,
)


def test_r2t_consumed_window_preserves_final_fresh_year() -> None:
    assert START == datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
    assert B2 == datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
    assert B3 == datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
    assert B4 == datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
    assert END == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
