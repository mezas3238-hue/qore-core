from __future__ import annotations

from types import SimpleNamespace

from qore.infrastructure.trader_lab import cibo_xauusd_trader_memory_bridge_v1 as memory
from qore.infrastructure.trader_lab.turtle_soup_xauusd_r19_full_cibo_memory_trailing_brain import (
    _confirmed_swing_candidate,
    _improves_stop,
    _memory_target_depth,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side


def _memory(state: str) -> memory.CiboXauusdMemoryContext:
    return memory.CiboXauusdMemoryContext(
        overall={},
        dimensions=(),
        support_votes=4 if state == "SUPPORTIVE" else 1,
        caution_votes=4 if state == "CAUTIOUS" else 1,
        mixed_votes=0,
        state=state,
    )


def test_trailing_stop_must_improve_and_not_cross_target() -> None:
    assert _improves_stop(
        side=Side.LONG,
        previous=90,
        candidate=101,
        target=110,
    )
    assert not _improves_stop(
        side=Side.LONG,
        previous=101,
        candidate=100,
        target=110,
    )
    assert _improves_stop(
        side=Side.SHORT,
        previous=110,
        candidate=99,
        target=90,
    )
    assert not _improves_stop(
        side=Side.SHORT,
        previous=99,
        candidate=100,
        target=90,
    )


def test_confirmed_swing_only_locks_beyond_entry() -> None:
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

    weak = [
        SimpleNamespace(low=99, high=108),
        SimpleNamespace(low=98, high=109),
        SimpleNamespace(low=100, high=110),
    ]
    assert _confirmed_swing_candidate(
        side=Side.LONG,
        bars=weak,
        entry=100,
        target=120,
    ) is None


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


def test_full_cibo_caution_can_reduce_extension_depth() -> None:
    setup = _Setup()
    rank, reason = _memory_target_depth(
        setup=setup,
        regime={"h4_range_3v20": "compressed<=0.75"},
        ladder_size=3,
        memory=_memory("CAUTIOUS"),
    )
    assert rank == 1
    assert reason == "RANK1_FULL_CIBO_MEMORY_CAUTION"


def test_full_cibo_support_can_confirm_displacement_extension() -> None:
    setup = _Setup()
    setup.context.cisd_progress_bucket = "q2:<=0.50"
    rank, reason = _memory_target_depth(
        setup=setup,
        regime={"h4_range_3v20": "normal_0.75_1.25"},
        ladder_size=3,
        memory=_memory("SUPPORTIVE"),
    )
    assert rank == 2
    assert reason == "RANK2_FULL_CIBO_MEMORY_SUPPORTIVE_DISPLACEMENT"
    setup.context.cisd_progress_bucket = "q4:>0.75"
