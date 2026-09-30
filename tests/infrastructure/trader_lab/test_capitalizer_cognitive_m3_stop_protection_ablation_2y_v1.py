from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_m3_stop_protection_ablation_2y_v1 as ablation,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import Pivot


def test_long_m3_swing_can_only_tighten_stop() -> None:
    confirmed = datetime(2026, 1, 5, 9, 6, tzinfo=UTC)
    pivot = Pivot(
        occurred_at=datetime(2026, 1, 5, 9, 3, tzinfo=UTC),
        confirmed_at=confirmed,
        price=Decimal("1.2496"),
        kind="LOW",
    )

    candidate = ablation._candidate_stop(
        pivot=pivot,
        side=CapitalizerSide.LONG,
        entry=Decimal("1.2500"),
        active_stop=Decimal("1.2490"),
        confirmation_close=Decimal("1.2502"),
        profitable_only=False,
    )

    assert candidate == Decimal("1.2496")


def test_profitable_lock_rejects_tighter_but_negative_long_stop() -> None:
    pivot = Pivot(
        occurred_at=datetime(2026, 1, 5, 9, 3, tzinfo=UTC),
        confirmed_at=datetime(2026, 1, 5, 9, 6, tzinfo=UTC),
        price=Decimal("1.2496"),
        kind="LOW",
    )

    candidate = ablation._candidate_stop(
        pivot=pivot,
        side=CapitalizerSide.LONG,
        entry=Decimal("1.2500"),
        active_stop=Decimal("1.2490"),
        confirmation_close=Decimal("1.2502"),
        profitable_only=True,
    )

    assert candidate is None


def test_profitable_lock_accepts_confirmed_long_swing_above_entry() -> None:
    pivot = Pivot(
        occurred_at=datetime(2026, 1, 5, 9, 3, tzinfo=UTC),
        confirmed_at=datetime(2026, 1, 5, 9, 6, tzinfo=UTC),
        price=Decimal("1.2501"),
        kind="LOW",
    )

    candidate = ablation._candidate_stop(
        pivot=pivot,
        side=CapitalizerSide.LONG,
        entry=Decimal("1.2500"),
        active_stop=Decimal("1.2490"),
        confirmation_close=Decimal("1.2504"),
        profitable_only=True,
    )

    assert candidate == Decimal("1.2501")
