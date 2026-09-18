from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r18_memory_driven_cibo_brain import (
    _compression_release_capacity,
    _late_confirmation_capacity,
    _target_depth_decision,
)


class _Context:
    cisd_progress_bucket = "q4:>0.75"
    fvg_before_entry = "yes"
    protected_risk_range_bucket = "q3:<=1.0"
    source_range_state_bucket = "q3:<=1.5"
    reclaim_latency_bucket = "16-30m"
    session = "london"
    weekday = "Tuesday"


class _Setup:
    context = _Context()


def test_named_capacity_paths_are_structural() -> None:
    setup = _Setup()
    regime = {"h4_range_3v20": "compressed<=0.75"}
    assert _late_confirmation_capacity(setup)
    assert _compression_release_capacity(setup, regime)


def test_rank2_requires_named_path_supported_session_and_non_friday() -> None:
    setup = _Setup()
    regime = {"h4_range_3v20": "compressed<=0.75"}
    rank, reason = _target_depth_decision(
        setup=setup,
        regime=regime,
        ladder_size=3,
    )
    assert rank == 2
    assert reason == "RANK2_LATE_CONFIRMATION_AND_COMPRESSION_RELEASE"


def test_friday_keeps_rank1_without_banning_entry() -> None:
    setup = _Setup()
    setup.context.weekday = "Friday"
    regime = {"h4_range_3v20": "compressed<=0.75"}
    rank, reason = _target_depth_decision(
        setup=setup,
        regime=regime,
        ladder_size=3,
    )
    assert rank == 1
    assert reason == "RANK1_FRIDAY_DEPTH_CONSERVATIVE"
    setup.context.weekday = "Tuesday"


def test_new_york_keeps_rank1_without_banning_entry() -> None:
    setup = _Setup()
    setup.context.session = "new-york"
    regime = {"h4_range_3v20": "compressed<=0.75"}
    rank, reason = _target_depth_decision(
        setup=setup,
        regime=regime,
        ladder_size=3,
    )
    assert rank == 1
    assert reason == "RANK1_SESSION_DEPTH_CONSERVATIVE"
    setup.context.session = "london"
