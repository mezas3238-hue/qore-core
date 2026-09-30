from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_simple_causal_policy_lab_v47_s2d as lab,
)


def test_target_r_band_boundaries_are_frozen() -> None:
    assert lab._target_r_band(Decimal("1.999")) == "<2R"
    assert lab._target_r_band(Decimal("2")) == "[2,4)R"
    assert lab._target_r_band(Decimal("4")) == "[4,8)R"
    assert lab._target_r_band(Decimal("8")) == "[8,16)R"
    assert lab._target_r_band(Decimal("16")) == ">=16R"


def test_policy_family_identity_is_frozen() -> None:
    assert lab.PREDECLARATION_COMMENT_ID == 5902089060
    assert lab.TARGET_R_BANDS == (
        "<2R",
        "[2,4)R",
        "[4,8)R",
        "[8,16)R",
        ">=16R",
    )


def test_baseline_policy_is_not_a_selectable_intervention() -> None:
    policy = lab.Policy(
        policy_id="KEEP_ALL",
        feature="",
        mode="",
        values=(),
        baseline=True,
    )
    assert policy.baseline is True
