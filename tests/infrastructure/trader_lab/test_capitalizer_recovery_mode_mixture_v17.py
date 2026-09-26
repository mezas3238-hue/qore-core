from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_recovery_mode_mixture_v17 as lab,
)


def test_dominance_requires_minimum_support() -> None:
    controls = tuple(Decimal("0.1") for _ in range(10))
    arms = tuple(Decimal("0.2") for _ in range(10))
    assert not lab._dominates(
        control_values=controls,
        arm_values=arms,
        minimum=12,
    )


def test_dominance_requires_no_tradeoff_against_control() -> None:
    controls = (
        Decimal("1"),
        Decimal("1"),
        Decimal("-0.2"),
        Decimal("0.2"),
    ) * 5
    better_mean_worse_downside = (
        Decimal("1"),
        Decimal("1"),
        Decimal("-1"),
        Decimal("1"),
    ) * 5
    assert not lab._dominates(
        control_values=controls,
        arm_values=better_mean_worse_downside,
        minimum=18,
    )


def test_cell_hierarchy_is_predeclared_and_coarse() -> None:
    assert list(lab.MIN_SUPPORT) == [
        "CONTEXT",
        "DEST_VOL",
        "DEST_ALIGN",
        "DEST",
    ]
    assert min(lab.MIN_SUPPORT.values()) >= 12


def test_mixture_keeps_surface_risk_and_existing_arms() -> None:
    assert lab.MAX_BASE_MULTIPLIER == Decimal("0.35")
    assert lab.ARMS == lab.v16.ARMS
    assert set(lab.POLICY_DD) == {
        "SURVIVAL_DD3",
        "SURVIVAL_DD4",
        "SURVIVAL_DD5",
    }


def test_cell_id_is_deterministic() -> None:
    assert lab._cell_id("DEST", ("GE_2R",)) == (
        '{"level":"DEST","values":["GE_2R"]}'
    )
