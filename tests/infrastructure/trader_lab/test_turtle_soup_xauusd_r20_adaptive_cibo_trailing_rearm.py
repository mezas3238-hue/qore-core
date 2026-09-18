from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r20_adaptive_cibo_trailing_rearm import (
    _confirmed_swing_candidate,
    _structurally_rearmed,
    _swing_trail_admissible,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side


def test_supportive_does_not_use_generic_swing_trail() -> None:
    admitted, reason = _swing_trail_admissible("SUPPORTIVE", 3)
    assert admitted is False
    assert reason == "SUPPORTIVE_LET_RUN"


def test_cautious_trails_on_first_confirmed_swing() -> None:
    assert _swing_trail_admissible("CAUTIOUS", 1)[0] is True


def test_mixed_requires_second_confirmed_swing() -> None:
    assert _swing_trail_admissible("MIXED", 1)[0] is False
    assert _swing_trail_admissible("MIXED", 2)[0] is True


def test_structural_rearm_requires_new_raid_and_new_source_candle() -> None:
    exit_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    class Context:
        signal = SimpleNamespace(
            raid_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
            c2_opened_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        )

    assert _structurally_rearmed(
        setup=SimpleNamespace(context=Context()),
        trailing_exit_at=exit_at,
    )

    class Stale:
        signal = SimpleNamespace(
            raid_at=datetime(2026, 1, 1, 11, 55, tzinfo=UTC),
            c2_opened_at=datetime(2026, 1, 1, 13, 0, tzinfo=UTC),
        )

    assert not _structurally_rearmed(
        setup=SimpleNamespace(context=Stale()),
        trailing_exit_at=exit_at,
    )


def test_confirmed_swing_must_be_beyond_entry_to_protect_capital() -> None:
    bars = [
        SimpleNamespace(low=102, high=108),
        SimpleNamespace(low=101, high=109),
        SimpleNamespace(low=103, high=110),
    ]
    assert _confirmed_swing_candidate(
        side=Side.LONG,
        bars=bars,
        entry=100,
        target=120,
    ) == 101
