from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r26_specialist_memory_brain as r26,
)


def test_choose_decision_prefers_more_specific_memory() -> None:
    target1 = SimpleNamespace(rank=1, route="A")
    target2 = SimpleNamespace(rank=2, route="B")

    setup = SimpleNamespace(
        context=SimpleNamespace(
            signal=SimpleNamespace(
                side=SimpleNamespace(value="long"),
                protected_swing=Decimal("99"),
            )
        )
    )

    original = r26._decision_for_target
    try:
        def fake(cognitive, setup, *, target, entry):
            if target.rank == 1:
                return r26.SpecialistDecision(
                    target=target,
                    memory_level="anatomy",
                    classification="ROBUST_POSITIVE_010",
                    posture="STATIC",
                    mean_net_010_r=Decimal("1"),
                    observations=100,
                )
            return r26.SpecialistDecision(
                target=target,
                memory_level="causal_core",
                classification="MAJORITY_POSITIVE_010",
                posture="STATIC",
                mean_net_010_r=Decimal("0.1"),
                observations=20,
            )
        r26._decision_for_target = fake
        decision = r26.choose_decision(
            {},
            setup,
            ladder=[target1, target2],
            entry=Decimal("100"),
        )
        assert decision is not None
        assert decision.target.rank == 2
        assert decision.memory_level == "causal_core"
    finally:
        r26._decision_for_target = original


def test_stat_tracks_drawdown_and_losing_streak() -> None:
    trades = [
        SimpleNamespace(net_010_r=Decimal("1")),
        SimpleNamespace(net_010_r=Decimal("-0.5")),
        SimpleNamespace(net_010_r=Decimal("-0.5")),
        SimpleNamespace(net_010_r=Decimal("0.25")),
    ]
    result = r26._stat(trades, "net_010_r")
    assert result["trades"] == 4
    assert Decimal(result["total_r"]) == Decimal("0.25")
    assert Decimal(result["max_drawdown_r"]) == Decimal("1.0")
    assert result["max_losing_streak"] == 2


def test_structural_rearm_requires_new_raid_and_source() -> None:
    exit_at = r26.datetime(2026, 1, 1, 12, 0, tzinfo=r26.UTC)
    good = SimpleNamespace(
        context=SimpleNamespace(
            signal=SimpleNamespace(
                raid_at=r26.datetime(2026, 1, 1, 12, 5, tzinfo=r26.UTC),
                c2_opened_at=r26.datetime(2026, 1, 1, 13, 0, tzinfo=r26.UTC),
            )
        )
    )
    stale = SimpleNamespace(
        context=SimpleNamespace(
            signal=SimpleNamespace(
                raid_at=r26.datetime(2026, 1, 1, 11, 55, tzinfo=r26.UTC),
                c2_opened_at=r26.datetime(2026, 1, 1, 13, 0, tzinfo=r26.UTC),
            )
        )
    )
    assert r26._structurally_rearmed(good, exit_at)
    assert not r26._structurally_rearmed(stale, exit_at)
