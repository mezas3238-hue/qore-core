from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r59_candidate_freeze as freeze,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r67_r66_failure_forensics as r67,
)


def test_r67_is_bound_to_failed_frozen_r58_identity() -> None:
    assert freeze.CANDIDATE_ID == (
        "VT08_INDEX_R58_EXACT_R47_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert freeze.CANDIDATE_RULE_FINGERPRINT == (
        "e959c8578a7ac71658cd19daf6d61815dfe277ecd06d8100c2655b30a62f48fa"
    )
    assert r67.SOURCE_R66_DECISION == (
        "FAIL_R66_FRESH_HOLDOUT_REJECT_FROZEN_IDENTITY"
    )
    assert r67.SOURCE_R66_RUN_ID == 35502695314
    assert r67.SOURCE_R66_ARTIFACT_ID == 10602364737


def test_r67_window_normalization_is_fixed_and_non_runtime() -> None:
    assert r67._window_days("R66") == 728
    assert r67._window_days("2Y") == 730
    assert r67._window_days("5Y") == 1826
    assert r67.NORMALIZATION_DAYS == Decimal("364")


def test_r67_adds_failure_attribution_dimensions_without_calendar() -> None:
    required = {
        "symbol",
        "side",
        "anchor",
        "poi",
        "market_side_poi",
        "source_day_relationship",
        "previous_source_day_body_alignment",
        "current_source_day_body_alignment",
        "cross_index_state",
        "market_side_anchor",
        "market_side_poi_anchor",
        "r47_demotion_state",
        "r58_rule_family",
        "effective_weight_bucket",
    }
    assert required.issubset(set(r67.DIMENSIONS))
    assert "year" not in r67.DIMENSIONS
    assert "calendar_year" not in r67.DIMENSIONS


def test_r67_weight_buckets_preserve_positive_risk_floor() -> None:
    assert r67._weight_bucket(Decimal("0.005")) == "FLOOR_0_005"
    assert r67._weight_bucket(Decimal("0.025")) == "LOW_LT_0_10"
    assert r67._weight_bucket(Decimal("0.10")) == "MID_0_10_TO_LT_0_25"
    assert r67._weight_bucket(Decimal("0.25")) == "CAP_0_25"


def test_r67_rule_family_collapses_r47_labels_without_hiding_support() -> None:
    assert r67._joined_rule_family(()) == "BASE_CAPPED"
    assert r67._joined_rule_family(
        ("R47:SP500_LONG_H4_61_120",)
    ) == "R47_DEMOTION"
    assert r67._joined_rule_family(
        (
            "STRUCTURAL_REARM",
            "FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE",
        )
    ) == "FVG_CROSS_INDEX_UNANIMOUS_WITH_SIDE+STRUCTURAL_REARM"
