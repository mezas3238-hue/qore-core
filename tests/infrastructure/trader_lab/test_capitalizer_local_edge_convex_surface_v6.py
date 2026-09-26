from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import capitalizer_local_edge_convex_surface_v6 as lab


def test_step_moves_on_supported_ladder() -> None:
    assert lab._step(Decimal("0.20"), direction=1) == Decimal("0.35")
    assert lab._step(Decimal("0.55"), direction=-1) == Decimal("0.35")
    assert lab._step(Decimal("1"), direction=1) == Decimal("1")


def test_balanced_releases_only_on_joint_favorable_evidence() -> None:
    value, reason = lab._local_multiplier(
        policy="LOCAL_CONVEX_BALANCED",
        base=Decimal("0.20"),
        current_dd=Decimal("5"),
        session_adverse=False,
        session_severe=False,
        session_favorable=True,
        adverse_votes=0,
        severe_votes=0,
        favorable_votes=2,
    )
    assert value == Decimal("0.35")
    assert reason == "LOCAL_FAVORABLE_RELEASE"


def test_balanced_tightens_on_severe_local_state() -> None:
    value, reason = lab._local_multiplier(
        policy="LOCAL_CONVEX_BALANCED",
        base=Decimal("0.35"),
        current_dd=Decimal("4"),
        session_adverse=True,
        session_severe=True,
        session_favorable=False,
        adverse_votes=2,
        severe_votes=1,
        favorable_votes=0,
    )
    assert value == Decimal("0.20")
    assert reason == "LOCAL_SEVERE_TIGHTEN"
