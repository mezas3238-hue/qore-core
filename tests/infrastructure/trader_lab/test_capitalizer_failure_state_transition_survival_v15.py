from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_failure_state_transition_survival_v15 as lab,
)


def _failure(*, exit_reason: str = "STOP") -> lab.StateSnapshot:
    return lab.StateSnapshot(
        symbol="EURUSD",
        session="LONDON",
        side="LONG",
        regime="M15=ALIGNED|H1=ALIGNED|VOL=NORMAL",
        destination="GE_2R",
        entry_at="2026-01-05T10:00:00+00:00",
        exit_at="2026-01-05T10:30:00+00:00",
        factors=("EUR", "USD"),
        exit_reason=exit_reason,
    )


def test_no_failure_never_abstains() -> None:
    assert not lab._should_abstain(
        policy="LOSS_DD4_N2",
        current_dd=Decimal("8"),
        failure=None,
        novelty=0,
    )


def test_drawdown_trigger_is_required() -> None:
    assert not lab._should_abstain(
        policy="LOSS_DD4_N2",
        current_dd=Decimal("3.99"),
        failure=_failure(),
        novelty=0,
    )
    assert lab._should_abstain(
        policy="LOSS_DD4_N2",
        current_dd=Decimal("4"),
        failure=_failure(),
        novelty=1,
    )


def test_novel_transition_reopens_flow() -> None:
    assert not lab._should_abstain(
        policy="LOSS_DD4_N2",
        current_dd=Decimal("5"),
        failure=_failure(),
        novelty=2,
    )


def test_stop_semantics_requires_stop_failure() -> None:
    assert not lab._should_abstain(
        policy="STOP_DD4_N1",
        current_dd=Decimal("5"),
        failure=_failure(exit_reason="SESSION_EXIT"),
        novelty=0,
    )
    assert lab._should_abstain(
        policy="STOP_DD4_N1",
        current_dd=Decimal("5"),
        failure=_failure(exit_reason="STOP"),
        novelty=0,
    )


def test_surface_control_never_abstains() -> None:
    assert not lab._should_abstain(
        policy="SURFACE_CONTROL",
        current_dd=Decimal("99"),
        failure=_failure(),
        novelty=0,
    )


def test_density_floor_remains_owner_anti_gaming_gate() -> None:
    assert lab.MIN_DENSITY_RETENTION == Decimal("0.90")
