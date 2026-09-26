from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_conflict_abstention_v12 as lab,
)


def _point(period: str, index: int, value: str) -> v10.ProbePoint:
    x = index / 49.0
    return v10.ProbePoint(
        period=period,
        symbol="NAS100",
        session="NEW_YORK",
        provenance="TEST",
        mode="ORIGINAL",
        regime="NORMAL",
        destination="GE_2R",
        entry_at=f"2026-01-{(index % 28) + 1:02d}T10:{index % 60:02d}:00+00:00",
        vector=(x, x),
        realized_r=value,
    )


def _bad_tail(period: str) -> tuple[v10.ProbePoint, ...]:
    return tuple(
        _point(period, i, "-1" if i < 20 else "1")
        for i in range(50)
    )


def test_lower_tail_is_negative_for_bad_low_rank_population() -> None:
    model = v10._fit_period(_bad_tail("A"), period="A")
    mean, support = lab._lower_tail(model, quantile=0.20)
    assert mean < 0
    assert support >= v10.MIN_TAIL_SUPPORT


def test_abstention_requires_two_period_agreement() -> None:
    a = v10._fit_period(_bad_tail("A"), period="A")
    b = v10._fit_period(_bad_tail("B"), period="B")
    query = v10.ProbePoint(
        period="HELDOUT",
        symbol="NAS100",
        session="NEW_YORK",
        provenance="TEST",
        mode="ORIGINAL",
        regime="NORMAL",
        destination="GE_2R",
        entry_at="2026-03-01T10:00:00+00:00",
        vector=(0.0, 0.0),
    )
    decision, percentiles, means, support = lab._should_abstain(
        (a, b),
        point=query,
        policy="ABSTAIN_Q20",
    )
    assert decision is True
    assert max(percentiles) <= 0.20
    assert max(means) < Decimal("0")
    assert min(support) >= v10.MIN_TAIL_SUPPORT


def test_density_floor_is_predeclared() -> None:
    assert lab.MIN_DENSITY_RETENTION == Decimal("0.90")
