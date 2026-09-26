from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_drawdown_path_causal_budget_v14 as lab,
)


def test_budget_requires_both_path_stress_and_causal_conflict() -> None:
    assert not lab._should_abstain(
        policy="BUDGET600_C2",
        projected_path_r=Decimal("5.99"),
        conflict_score=5,
        recovery_evidence=False,
    )
    assert not lab._should_abstain(
        policy="BUDGET600_C2",
        projected_path_r=Decimal("6.01"),
        conflict_score=1,
        recovery_evidence=False,
    )
    assert lab._should_abstain(
        policy="BUDGET600_C2",
        projected_path_r=Decimal("6.01"),
        conflict_score=2,
        recovery_evidence=False,
    )


def test_recovery_variant_preserves_trade_when_recovery_is_supported() -> None:
    assert not lab._should_abstain(
        policy="BUDGET600_C2_RECOVERY",
        projected_path_r=Decimal("6.50"),
        conflict_score=4,
        recovery_evidence=True,
    )
    assert lab._should_abstain(
        policy="BUDGET600_C2_RECOVERY",
        projected_path_r=Decimal("6.50"),
        conflict_score=4,
        recovery_evidence=False,
    )


def test_surface_control_never_adds_abstention() -> None:
    assert not lab._should_abstain(
        policy="SURFACE_CONTROL",
        projected_path_r=Decimal("99"),
        conflict_score=99,
        recovery_evidence=False,
    )


def test_active_open_risk_is_strictly_prior_and_still_open() -> None:
    rows = (
        lab.OpenRisk(
            symbol="EURUSD",
            side="LONG",
            entry_at="2026-01-05T10:00:00+00:00",
            exit_at="2026-01-05T11:00:00+00:00",
            risk_r=Decimal("0.35"),
        ),
        lab.OpenRisk(
            symbol="GBPUSD",
            side="LONG",
            entry_at="2026-01-05T10:30:00+00:00",
            exit_at="2026-01-05T12:00:00+00:00",
            risk_r=Decimal("0.55"),
        ),
    )
    active = lab._active(
        rows,
        entry_at="2026-01-05T10:30:00+00:00",
    )
    assert len(active) == 1
    assert active[0].symbol == "EURUSD"
    assert not lab._active(
        rows,
        entry_at="2026-01-05T12:00:00+00:00",
    )


def test_policy_grid_preserves_density_anti_gaming_floor() -> None:
    assert lab.MIN_DENSITY_RETENTION == Decimal("0.90")
    assert all(
        budget in {Decimal("5.75"), Decimal("6.00")}
        for budget, _conflict, _recovery in lab.POLICY_SPECS.values()
    )
