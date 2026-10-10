from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_recovery_probe_position_survival_v16 as lab,
)


def test_stats_reports_mean_negative_rate_and_downside() -> None:
    mean, negative, downside = lab._stats(
        (Decimal("2"), Decimal("-1"), Decimal("-0.5"), Decimal("1"))
    )
    assert mean == Decimal("0.375")
    assert negative == Decimal("0.5")
    assert downside == Decimal("0.375")


def _model(period: str, arm: str | None) -> lab.PeriodArmModel:
    return lab.PeriodArmModel(
        period=period,
        dd_trigger_r="4",
        recovery_support=50,
        selected_arm=arm,
        arms=(),
    )


def test_pair_consensus_requires_same_non_null_arm() -> None:
    arm = milestone.ProtectionMode.BE_AFTER_075.value
    assert lab._pair_consensus(_model("A", arm), _model("B", arm)) == arm
    assert lab._pair_consensus(_model("A", arm), _model("B", None)) is None
    assert (
        lab._pair_consensus(
            _model("A", arm),
            _model("B", milestone.ProtectionMode.STAGED_050_100_150.value),
        )
        is None
    )


def test_recovery_policy_grid_preserves_surface_risk() -> None:
    assert lab.MAX_BASE_MULTIPLIER == Decimal("0.35")
    assert set(lab.POLICY_DD) == {
        "SURVIVAL_DD3",
        "SURVIVAL_DD4",
        "SURVIVAL_DD5",
    }
    assert lab.MIN_SUPPORT == 30


def test_arms_are_existing_position_intelligence_modes() -> None:
    allowed = {mode.value for mode in milestone.ProtectionMode}
    assert set(lab.ARMS).issubset(allowed)
    assert milestone.ProtectionMode.ORIGINAL.value not in lab.ARMS
