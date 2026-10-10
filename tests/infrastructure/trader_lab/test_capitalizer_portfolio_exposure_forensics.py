from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_portfolio_exposure_forensics import (
    CapitalizerExposureCandidate,
    _assessment,
    _select,
)


def _candidate(
    symbol: str,
    side: CapitalizerSide,
    *,
    entry_minutes: int,
    exit_minutes: int,
    realized: str = "1",
) -> CapitalizerExposureCandidate:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    entry = base + timedelta(minutes=entry_minutes)
    return CapitalizerExposureCandidate(
        symbol=symbol,
        side=side,
        signal_at=entry,
        entry_at=entry,
        exit_at=base + timedelta(minutes=exit_minutes),
        event_labels=("HIGH_ACCEPTANCE",),
        planned_reward_r=Decimal("2"),
        state_family="NO_RECLAIM_FRESH",
        cisd_timing_state="ALL_WITHIN_H1",
        source_age_state="CURRENT_H1_SOURCE",
        boundary_type_state="PRIOR_HIGH_LOW_ONLY",
        reclaim_phase="NO_RECLAIM_OBSERVED",
        realized_r=Decimal(realized),
    )


def test_exposure_assessment_detects_same_direction_shared_jpy_factor() -> None:
    active = _candidate(
        "USDJPY",
        CapitalizerSide.LONG,
        entry_minutes=0,
        exit_minutes=40,
    )
    candidate = _candidate(
        "GBPJPY",
        CapitalizerSide.LONG,
        entry_minutes=10,
        exit_minutes=30,
    )
    assessment = _assessment(candidate, (active,))
    assert assessment.shared_factors == 1
    assert assessment.same_direction_factors == 1
    assert assessment.opposing_direction_factors == 0
    assert assessment.state == "SHARED_FACTOR_SAME_DIRECTION"


def test_exposure_assessment_detects_opposing_shared_usd_factor() -> None:
    active = _candidate(
        "USDJPY",
        CapitalizerSide.LONG,
        entry_minutes=0,
        exit_minutes=40,
    )
    candidate = _candidate(
        "AUDUSD",
        CapitalizerSide.LONG,
        entry_minutes=20,
        exit_minutes=35,
    )
    assessment = _assessment(candidate, (active,))
    assert assessment.shared_factors == 1
    assert assessment.same_direction_factors == 0
    assert assessment.opposing_direction_factors == 1
    assert assessment.state == "SHARED_FACTOR_OPPOSING_DIRECTION"


def test_same_direction_exposure_ablation_is_causal_and_preserves_max3() -> None:
    first = _candidate(
        "USDJPY",
        CapitalizerSide.LONG,
        entry_minutes=0,
        exit_minutes=40,
    )
    blocked = _candidate(
        "GBPJPY",
        CapitalizerSide.LONG,
        entry_minutes=10,
        exit_minutes=30,
    )
    opposing = _candidate(
        "AUDUSD",
        CapitalizerSide.LONG,
        entry_minutes=20,
        exit_minutes=35,
    )
    later = _candidate(
        "GBPJPY",
        CapitalizerSide.LONG,
        entry_minutes=45,
        exit_minutes=70,
    )
    candidates = (first, blocked, opposing, later)

    baseline, baseline_rejected, _ = _select(
        candidates,
        policy="MAX3_BASELINE",
        tie_policy="SYMBOL_ASC",
    )
    assert baseline == candidates[:3]
    assert baseline_rejected == ()

    selected, rejected, _ = _select(
        candidates,
        policy="MAX3_BLOCK_SAME_DIRECTION_SHARED_FACTOR",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (first, opposing, later)
    assert rejected == (blocked,)
    assert len(selected) == 3


def test_any_shared_factor_ablation_is_stricter_than_same_direction_only() -> None:
    first = _candidate(
        "USDJPY",
        CapitalizerSide.LONG,
        entry_minutes=0,
        exit_minutes=40,
    )
    same = _candidate(
        "GBPJPY",
        CapitalizerSide.LONG,
        entry_minutes=10,
        exit_minutes=30,
    )
    opposing = _candidate(
        "AUDUSD",
        CapitalizerSide.LONG,
        entry_minutes=20,
        exit_minutes=35,
    )
    selected, rejected, _ = _select(
        (first, same, opposing),
        policy="MAX3_BLOCK_ANY_SHARED_FACTOR",
        tie_policy="SYMBOL_ASC",
    )
    assert selected == (first,)
    assert rejected == (same, opposing)
