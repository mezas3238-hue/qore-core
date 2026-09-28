from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_multi_position_causal_episode_simulator_v36 as v36,
)


def _trade(
    *,
    symbol: str,
    entry_at: str,
    exit_at: str,
) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol=symbol,
        session="NEW_YORK",
        operating_date=entry_at[:10],
        side="LONG",
        entry_at=entry_at,
        exit_at=exit_at,
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r="1",
        exit_reason="TARGET",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def _row(
    *,
    symbol: str,
    entry_at: str,
    trigger_at: str,
    action: str,
    dd: str,
    total: str,
) -> dict[str, object]:
    return {
        "period": "P",
        "symbol": symbol,
        "entry_at": entry_at,
        "trigger_at": trigger_at,
        "surface_mode": "BE_AFTER_050",
        "action": action,
        "entrant_in_surface_max_dd_descent": True,
        "rollout_legacy_dd_r": dd,
        "rollout_total_r": total,
        "dynamic_total_delta_r": total,
        "legacy_dd_relief_r": "0.1",
    }


def test_seed_selection_keeps_tail_min_and_value_max_per_entrant() -> None:
    rows = (
        _row(
            symbol="A",
            entry_at="2026-01-01T10:00:00+00:00",
            trigger_at="2026-01-01T10:05:00+00:00",
            action="BE_AFTER_075",
            dd="5.0",
            total="10",
        ),
        _row(
            symbol="A",
            entry_at="2026-01-01T10:00:00+00:00",
            trigger_at="2026-01-01T10:05:00+00:00",
            action="LOCK025_AFTER_075",
            dd="4.5",
            total="8",
        ),
        _row(
            symbol="A",
            entry_at="2026-01-01T10:00:00+00:00",
            trigger_at="2026-01-01T10:05:00+00:00",
            action="STAGED_075_125_150",
            dd="4.8",
            total="12",
        ),
    )

    seeds = v36._select_episode_seeds(rows, period="P")

    assert len(seeds) == 2
    by_role = {seed.role: seed.action for seed in seeds}
    assert by_role["TAIL_MIN"] == "LOCK025_AFTER_075"
    assert by_role["VALUE_MAX"] == "STAGED_075_125_150"


def test_seed_selection_collapses_same_tail_and_value_action() -> None:
    rows = (
        _row(
            symbol="A",
            entry_at="2026-01-01T10:00:00+00:00",
            trigger_at="2026-01-01T10:05:00+00:00",
            action="BE_AFTER_075",
            dd="4.0",
            total="12",
        ),
        _row(
            symbol="A",
            entry_at="2026-01-01T10:00:00+00:00",
            trigger_at="2026-01-01T10:05:00+00:00",
            action="LOCK025_AFTER_075",
            dd="5.0",
            total="8",
        ),
    )

    seeds = v36._select_episode_seeds(rows, period="P")

    assert len(seeds) == 1
    assert seeds[0].action == "BE_AFTER_075"
    assert seeds[0].role == "TAIL_MIN"


def test_joint_active_trigger_requires_actual_concurrent_position_state() -> None:
    first = v36.EpisodeSeed(
        period="P",
        symbol="A",
        entry_at="2026-01-01T10:00:00+00:00",
        trigger_at="2026-01-01T10:05:00+00:00",
        surface_mode="BE_AFTER_050",
        action="BE_AFTER_075",
        role="TAIL_MIN",
        source_single_total_r="1",
        source_single_legacy_dd_r="5",
        source_dynamic_total_delta_r="0",
        source_legacy_dd_relief_r="0",
    )
    second = v36.EpisodeSeed(
        period="P",
        symbol="B",
        entry_at="2026-01-01T10:03:00+00:00",
        trigger_at="2026-01-01T10:08:00+00:00",
        surface_mode="BE_AFTER_050",
        action="LOCK025_AFTER_075",
        role="VALUE_MAX",
        source_single_total_r="1",
        source_single_legacy_dd_r="5",
        source_dynamic_total_delta_r="0",
        source_legacy_dd_relief_r="0",
    )
    overlap = v36._joint_active_trigger(
        first_seed=first,
        second_seed=second,
        first_row=_trade(
            symbol="A",
            entry_at=first.entry_at,
            exit_at="2026-01-01T10:20:00+00:00",
        ),
        second_row=_trade(
            symbol="B",
            entry_at=second.entry_at,
            exit_at="2026-01-01T10:15:00+00:00",
        ),
    )

    assert overlap is not None
    start, end, trigger = overlap
    assert start.isoformat() == "2026-01-01T10:03:00+00:00"
    assert end.isoformat() == "2026-01-01T10:15:00+00:00"
    assert trigger.isoformat() == "2026-01-01T10:05:00+00:00"


def test_joint_active_trigger_rejects_non_overlapping_positions() -> None:
    first = v36.EpisodeSeed(
        period="P",
        symbol="A",
        entry_at="2026-01-01T10:00:00+00:00",
        trigger_at="2026-01-01T10:05:00+00:00",
        surface_mode="BE_AFTER_050",
        action="BE_AFTER_075",
        role="TAIL_MIN",
        source_single_total_r="1",
        source_single_legacy_dd_r="5",
        source_dynamic_total_delta_r="0",
        source_legacy_dd_relief_r="0",
    )
    second = v36.EpisodeSeed(
        period="P",
        symbol="B",
        entry_at="2026-01-01T10:30:00+00:00",
        trigger_at="2026-01-01T10:35:00+00:00",
        surface_mode="BE_AFTER_050",
        action="LOCK025_AFTER_075",
        role="VALUE_MAX",
        source_single_total_r="1",
        source_single_legacy_dd_r="5",
        source_dynamic_total_delta_r="0",
        source_legacy_dd_relief_r="0",
    )

    overlap = v36._joint_active_trigger(
        first_seed=first,
        second_seed=second,
        first_row=_trade(
            symbol="A",
            entry_at=first.entry_at,
            exit_at="2026-01-01T10:20:00+00:00",
        ),
        second_row=_trade(
            symbol="B",
            entry_at=second.entry_at,
            exit_at="2026-01-01T10:45:00+00:00",
        ),
    )

    assert overlap is None
