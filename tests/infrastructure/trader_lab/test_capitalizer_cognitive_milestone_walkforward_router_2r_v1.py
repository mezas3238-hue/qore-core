from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_milestone_walkforward_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)


def test_score_policies_penalize_downside() -> None:
    mean_r = Decimal("0.20")
    negative_rate = Decimal("0.40")
    downside = Decimal("0.80")
    dd = Decimal("3")
    assert router._score(
        policy="MEAN_R",
        mean_r=mean_r,
        negative_rate=negative_rate,
        downside=downside,
        dd=dd,
    ) == mean_r
    assert router._score(
        policy="TAIL_UTILITY",
        mean_r=mean_r,
        negative_rate=negative_rate,
        downside=downside,
        dd=dd,
    ) < mean_r


def test_split_keys_is_disjoint_and_complete() -> None:
    rows = tuple(
        milestone.SimulatedTrade(
            symbol="NAS100",
            session="NEW_YORK",
            operating_date=f"2026-01-{index + 1:02d}",
            side="LONG",
            entry_at=f"2026-01-{index + 1:02d}T10:00:00+00:00",
            exit_at=f"2026-01-{index + 1:02d}T10:10:00+00:00",
            entry_price="100",
            original_stop_price="99",
            final_stop_price="99",
            target_price="102",
            realized_gross_r="1",
            exit_reason="TIME_EXIT",
            mode="ORIGINAL",
            protection_updates=0,
            first_protection_at=None,
            max_milestone_r_seen_before_exit="0",
            same_minute_stop_target_ambiguity=False,
        )
        for index in range(9)
    )
    blocks = router._split_keys(rows)
    assert tuple(len(block) for block in blocks) == (3, 3, 3)
    flattened = tuple(key for block in blocks for key in block)
    assert len(flattened) == 9
    assert len(set(flattened)) == 9
