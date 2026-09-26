from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_frozen_replay_2y_v1 as frozen_v3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_2y_v1 as wait5,
)


def test_window_restores_all_global_contracts() -> None:
    frozen_before = (
        frozen_v3.__dict__["WINDOW_START"],
        frozen_v3.__dict__["WINDOW_END"],
        frozen_v3.__dict__["LOOKBACK_START"],
    )
    wait_before = (
        wait5.__dict__["WINDOW_START"],
        wait5.__dict__["WINDOW_END"],
        wait5.__dict__["LOOKBACK_START"],
    )
    v3_before = (
        v3.__dict__["WINDOW_START"],
        v3.__dict__["WINDOW_END"],
        v3.__dict__["LOOKBACK_START"],
    )
    start = datetime(2022, 9, 17, tzinfo=UTC)
    end = datetime(2024, 9, 17, tzinfo=UTC)

    with direct._window(start=start, end=end):
        assert frozen_v3.__dict__["WINDOW_START"] == start
        assert frozen_v3.__dict__["WINDOW_END"] == end
        assert wait5.__dict__["WINDOW_START"] == start
        assert wait5.__dict__["WINDOW_END"] == end
        assert v3.__dict__["WINDOW_START"] == start
        assert v3.__dict__["WINDOW_END"] == end

    assert (
        frozen_v3.__dict__["WINDOW_START"],
        frozen_v3.__dict__["WINDOW_END"],
        frozen_v3.__dict__["LOOKBACK_START"],
    ) == frozen_before
    assert (
        wait5.__dict__["WINDOW_START"],
        wait5.__dict__["WINDOW_END"],
        wait5.__dict__["LOOKBACK_START"],
    ) == wait_before
    assert (
        v3.__dict__["WINDOW_START"],
        v3.__dict__["WINDOW_END"],
        v3.__dict__["LOOKBACK_START"],
    ) == v3_before


def test_dd_utility_matches_frozen_router_semantics() -> None:
    rows = (
        milestone.SimulatedTrade(
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
        milestone.SimulatedTrade(
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
