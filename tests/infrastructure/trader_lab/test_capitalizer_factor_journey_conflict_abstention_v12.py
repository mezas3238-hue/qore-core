from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_conflict_abstention_v12 as lab,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
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


def _trade(symbol: str, side: str) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol=symbol,
        session="NEW_YORK",
        operating_date="2026-01-01",
        side=side,
        entry_at="2026-01-01T15:00:00+00:00",
        exit_at="2026-01-01T16:00:00+00:00",
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
    )


def test_v12_simulation_binds_and_restores_v11_simultaneous_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    left = _trade("EURUSD", "LONG")
    right = _trade("GBPUSD", "LONG")
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]] = {
        milestone.ProtectionMode.ORIGINAL.value: (left, right),
    }
    seen: list[dict[tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]]] = []

    def fake_bound(**_kwargs: Any) -> tuple[dict[str, Any], tuple[lab.AbstainDecision, ...]]:
        seen.append(dict(v11._SIMULTANEOUS))
        return {}, ()

    before = dict(v11._SIMULTANEOUS)
    monkeypatch.setattr(lab, "_simulate_bound", fake_bound)
    lab._simulate(
        period="P",
        policy="SURFACE_CONTROL",
        ledgers=ledgers,
        contexts={},
        contextual_model={},
        models=None,
    )

    assert ("P", "NEW_YORK", left.entry_at) in seen[0]
    assert v11._SIMULTANEOUS == before
