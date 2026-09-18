from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    cibo_xauusd_native_market_decision_memory_v2 as native,
)


def test_bucket_is_structural_and_deterministic() -> None:
    assert native._bucket(Decimal("0.4"), native.RR_CUTS) == "q1:<=0.5"
    assert native._bucket(Decimal("1.2"), native.RR_CUTS) == "q3:<=1.5"
    assert native._bucket(None, native.RR_CUTS) == "missing"


def test_classify_requires_temporal_support() -> None:
    rows = []
    for period in ("early_2016_2020", "transition_2021_2023", "recent_2024_2026"):
        for _ in range(native.MIN_PERIOD_N):
            rows.append(
                {
                    "period": period,
                    "STATIC_net_010_r": "0.2",
                    "STATIC_gross_r": "0.3",
                    "STATIC_target_reached": True,
                    "STATIC_protected_exit": False,
                    "STATIC_stop_exit": False,
                }
            )
    result = native._classify(rows, native.POSTURE_STATIC)
    assert result["classification"] == native.ROBUST


def test_majority_classification_is_not_robust() -> None:
    rows = []
    values = {
        "early_2016_2020": "0.2",
        "transition_2021_2023": "0.2",
        "recent_2024_2026": "-0.1",
    }
    for period, value in values.items():
        for _ in range(native.MIN_PERIOD_N):
            rows.append(
                {
                    "period": period,
                    "LET_RUN_net_010_r": value,
                    "LET_RUN_gross_r": str(Decimal(value) + Decimal("0.10")),
                    "LET_RUN_target_reached": value != "-0.1",
                    "LET_RUN_protected_exit": False,
                    "LET_RUN_stop_exit": value == "-0.1",
                }
            )
    result = native._classify(rows, native.POSTURE_LET_RUN)
    assert result["classification"] == native.MAJORITY


def test_best_posture_prefers_freedom_when_robust() -> None:
    item = {
        "postures": {
            native.POSTURE_STATIC: {"classification": native.ROBUST},
            native.POSTURE_LET_RUN: {"classification": native.ROBUST},
            native.POSTURE_PROTECT: {"classification": native.ROBUST},
        }
    }
    posture, classification = native._best_posture(item)
    assert posture == native.POSTURE_LET_RUN
    assert classification == native.ROBUST
