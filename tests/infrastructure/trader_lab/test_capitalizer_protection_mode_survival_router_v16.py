from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_protection_mode_survival_router_v16 as lab,
)


def _stats(
    *,
    mean: str,
    q20: str,
    negative: str,
    loss: str,
    support: int = 30,
) -> lab.ArmStats:
    return lab.ArmStats(
        support=support,
        mean_r=mean,
        q20_r=q20,
        negative_rate=negative,
        mean_loss_severity_r=loss,
    )


def test_pareto_dominance_requires_no_dimension_to_worsen() -> None:
    surface = _stats(
        mean="0.10",
        q20="-1",
        negative="0.40",
        loss="0.80",
    )
    better = _stats(
        mean="0.12",
        q20="-0.50",
        negative="0.35",
        loss="0.70",
    )
    worse_mean = _stats(
        mean="0.09",
        q20="-0.50",
        negative="0.35",
        loss="0.70",
    )
    assert lab._dominates(better, surface) is True
    assert lab._dominates(worse_mean, surface) is False


def test_state_keys_are_low_dimensional_and_causal() -> None:
    exact, state, dd = lab._keys(
        current_dd=Decimal("4.25"),
        base_multiplier=Decimal("0.20"),
        failure_state="FAIL_SAME",
    )
    assert exact == ("DD_GE4", "FAIL_SAME", "RISK_020")
    assert state == ("DD_GE4", "FAIL_SAME")
    assert dd == ("DD_GE4",)


def test_lookup_falls_back_without_inventing_a_cell() -> None:
    cell = lab.FrozenCell(
        level="GLOBAL",
        key=("GLOBAL",),
        support=100,
        selected_mode=lab.SURFACE,
        surface_stats=_stats(
            mean="0.1",
            q20="-1",
            negative="0.4",
            loss="0.8",
            support=100,
        ),
        selected_stats=_stats(
            mean="0.1",
            q20="-1",
            negative="0.4",
            loss="0.8",
            support=100,
        ),
        pareto_promoted=False,
    )
    import json

    model = {
        json.dumps(
            ["GLOBAL", ["GLOBAL"]],
            separators=(",", ":"),
        ): cell
    }
    selected = lab._lookup(
        model,
        exact_key=("DD_GE4", "FAIL_SAME", "RISK_020"),
        state_key=("DD_GE4", "FAIL_SAME"),
        dd_key=("DD_GE4",),
    )
    assert selected is cell


def test_density_and_strategy_contract_is_mode_routing_only() -> None:
    assert lab.DEVELOPMENT_PERIOD == "DEVELOPMENT_2024_2026"
    assert lab.STRICT_OOS_PERIODS == (
        "CONSUMED_VALIDATION_2022_2024",
        "CONSUMED_RESERVED_2020_2022",
    )
    assert lab.SURFACE in lab.ARMS
    assert "STAGED_050_100_150" in lab.ARMS
