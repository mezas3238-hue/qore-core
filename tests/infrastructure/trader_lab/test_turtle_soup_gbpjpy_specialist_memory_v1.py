from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_specialist_memory_v1 as specialist,
)


def test_period_partition_is_stable() -> None:
    assert specialist._period(2018) == "early_2016_2020"
    assert specialist._period(2022) == "transition_2021_2023"
    assert specialist._period(2025) == "recent_2024_2026"


def test_context_only_level_never_authorizes() -> None:
    hierarchy = {
        "exact": {"signatures": {}},
        "causal_core": {"signatures": {}},
        "anatomy": {"signatures": {}},
        "compact_anatomy": {
            "signatures": {
                "H1|yes|q1:<=0.25|q2:<=0.50|1|q2:<=1.0": {
                    "decision_authority": "CONTEXT_ONLY",
                    "preferred_posture": "STATIC",
                }
            }
        },
    }
    row = {
        "timeframe": "H1",
        "side": "long",
        "session": "London",
        "weekday": "Monday",
        "prior_body_alignment": "opposed",
        "fvg_before_entry": "yes",
        "exact_equal_liquidity": "no",
        "raid_depth_range_bucket": "q1:<=0.05",
        "reclaim_latency_bucket": "<=5m",
        "cisd_progress_bucket": "q1:<=0.25",
        "protected_risk_range_bucket": "q2:<=0.50",
        "source_range_state_bucket": "q2:<=1.0",
        "body_fraction_bucket": "q2:<=0.50",
        "rejection_wick_bucket": "q2:<=0.25",
        "close_location_bucket": "q3:<=0.75",
        "target_rank": 1,
        "target_route": "SOURCE_OPPOSITE_BOUNDARY:H1",
        "rr_bucket": "q2:<=1.0",
    }
    item, level, signature = specialist.resolve_authoritative(hierarchy, row)
    assert item is None
    assert level is None
    assert signature is None


def test_best_posture_uses_same_confidence_class_then_mean() -> None:
    models = {
        "STATIC": {
            "classification": "ROBUST_POSITIVE_010",
            "combined": {"mean_net_010_r": "0.10"},
        },
        "LET_RUN": {
            "classification": "ROBUST_POSITIVE_010",
            "combined": {"mean_net_010_r": "0.05"},
        },
        "PROTECT": {
            "classification": "MAJORITY_POSITIVE_010",
            "combined": {"mean_net_010_r": "0.50"},
        },
    }
    assert specialist._best_posture(models) == "STATIC"


def test_summary_tracks_both_friction_levels() -> None:
    rows = [
        {
            "STATIC_gross_r": "0.3",
            "STATIC_net_005_r": "0.25",
            "STATIC_net_010_r": "0.20",
            "STATIC_target_reached": True,
            "STATIC_protected_exit": False,
        },
        {
            "STATIC_gross_r": "-0.2",
            "STATIC_net_005_r": "-0.25",
            "STATIC_net_010_r": "-0.30",
            "STATIC_target_reached": False,
            "STATIC_protected_exit": False,
        },
    ]
    summary = specialist._summary(rows, "STATIC")
    assert Decimal(summary["mean_net_005_r"]) == Decimal("0.00")
    assert Decimal(summary["mean_net_010_r"]) == Decimal("-0.05")
