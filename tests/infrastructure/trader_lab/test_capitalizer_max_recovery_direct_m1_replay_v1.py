from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)


def test_window_restores_all_global_contracts() -> None:
    frozen_before = (
        direct.frozen_v3.WINDOW_START,
        direct.frozen_v3.WINDOW_END,
        direct.frozen_v3.LOOKBACK_START,
    )
    wait_before = (
        direct.wait5.WINDOW_START,
        direct.wait5.WINDOW_END,
        direct.wait5.LOOKBACK_START,
    )
    v3_before = (
        direct.v3.WINDOW_START,
        direct.v3.WINDOW_END,
        direct.v3.LOOKBACK_START,
    )
    start = datetime(2022, 9, 17, tzinfo=UTC)
    end = datetime(2024, 9, 17, tzinfo=UTC)

    with direct._window(start=start, end=end):
        assert direct.frozen_v3.WINDOW_START == start
        assert direct.frozen_v3.WINDOW_END == end
        assert direct.wait5.WINDOW_START == start
        assert direct.wait5.WINDOW_END == end
        assert direct.v3.WINDOW_START == start
        assert direct.v3.WINDOW_END == end

    assert (
        direct.frozen_v3.WINDOW_START,
        direct.frozen_v3.WINDOW_END,
        direct.frozen_v3.LOOKBACK_START,
    ) == frozen_before
    assert (
        direct.wait5.WINDOW_START,
        direct.wait5.WINDOW_END,
        direct.wait5.LOOKBACK_START,
    ) == wait_before
    assert (
        direct.v3.WINDOW_START,
        direct.v3.WINDOW_END,
        direct.v3.LOOKBACK_START,
    ) == v3_before


def test_dd_utility_matches_frozen_router_semantics() -> None:
    rows = (
        direct.milestone.SimulatedTrade(
            symbol="NAS100",
            session="NEW_YORK",
            operating_date="2026-01-05",
            side="LONG",
            entry_at="2026-01-05T10:00:00+00:00",
            exit_at="2026-01-05T10:10:00+00:00",
            entry_price="100",
            original_stop_price="99",
            final_stop_price="99",
            target_price="102",
            realized_gross_r="2",
            exit_reason="TARGET",
            mode="ORIGINAL",
            protection_updates=0,
            first_protection_at=None,
            max_milestone_r_seen_before_exit="2",
            same_minute_stop_target_ambiguity=False,
        ),
        direct.milestone.SimulatedTrade(
            symbol="NAS100",
            session="NEW_YORK",
            operating_date="2026-01-06",
            side="LONG",
            entry_at="2026-01-06T10:00:00+00:00",
            exit_at="2026-01-06T10:10:00+00:00",
            entry_price="100",
            original_stop_price="99",
            final_stop_price="99",
            target_price="102",
            realized_gross_r="-1",
            exit_reason="STOP",
            mode="ORIGINAL",
            protection_updates=0,
            first_protection_at=None,
            max_milestone_r_seen_before_exit="0",
            same_minute_stop_target_ambiguity=False,
        ),
    )
    # mean = +0.5R, DD = 1R -> 0.5 - 0.03
    assert direct._dd_utility(rows) == Decimal("0.47")
