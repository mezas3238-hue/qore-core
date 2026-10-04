from __future__ import annotations

import pytest

from scripts.shared_wp11_exact_blocker_audit import audit_blockers


def _baseline():
    mc23 = (
        {
            "identity": "mc23-detection",
            "status": "MC23_REAL_NOVELTY_DETECTION_BOUND_PASS",
            "real_novelty_detection_bound": True,
            "real_novel_regime_validated_adaptation": False,
        },
    )
    mc24 = (
        {
            "identity": "mc24-regression",
            "status": "MC24_REAL_REGRESSION_SUITE_BOUND_PASS",
            "real_adaptation_regression_suite_bound": True,
            "mc23_real_regime_adaptation_bound": False,
            "empirical_half_life_validated": False,
        },
    )
    mc25 = (
        {
            "identity": "mc25-lineage",
            "status": "MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_PASS",
            "lineage_integrity_stress_pass": True,
        },
    )
    return mc23, mc24, mc25


def test_initial_wp11_inventory_has_eight_blockers() -> None:
    mc23, mc24, mc25 = _baseline()
    result = audit_blockers(mc23_rows=mc23, mc24_rows=mc24, mc25_rows=mc25)
    assert result["blocker_count"] == 8
    assert result["zero_open_work"] is False


def test_performance_stress_closes_only_its_own_blocker() -> None:
    mc23, mc24, mc25 = _baseline()
    performance = {
        "identity": "mc25-performance",
        "status": "MC25_WP04_V3B_PERFORMANCE_STRESS_PASS",
        "performance_stress_bound": True,
        "performance_stress_pass": True,
        "formal_stress_stage_completed": False,
    }
    result = audit_blockers(
        mc23_rows=mc23,
        mc24_rows=mc24,
        mc25_rows=mc25 + (performance,),
    )
    assert result["blocker_count"] == 7
    assert "MC25_SAME_LINEAGE_PERFORMANCE_STRESS" not in result["blockers"]
    assert "MC25_FORMAL_STRESS_STAGE" in result["blockers"]


def test_previous_audit_enforces_monotonic_reduction() -> None:
    mc23, mc24, mc25 = _baseline()
    initial = audit_blockers(mc23_rows=mc23, mc24_rows=mc24, mc25_rows=mc25)
    performance = {
        "identity": "mc25-performance",
        "status": "MC25_WP04_V3B_PERFORMANCE_STRESS_PASS",
        "performance_stress_bound": True,
        "performance_stress_pass": True,
        "formal_stress_stage_completed": False,
    }
    advanced = audit_blockers(
        mc23_rows=mc23,
        mc24_rows=mc24,
        mc25_rows=mc25 + (performance,),
        previous=initial,
    )
    assert advanced["monotonic_reduction_verified"] is True
    assert set(advanced["blockers"]) < set(initial["blockers"])


def test_reopening_a_closed_blocker_is_rejected() -> None:
    mc23, mc24, mc25 = _baseline()
    previous = {
        "blockers": [
            blocker
            for blocker in audit_blockers(
                mc23_rows=mc23,
                mc24_rows=mc24,
                mc25_rows=mc25,
            )["blockers"]
            if blocker != "MC25_SAME_LINEAGE_PERFORMANCE_STRESS"
        ]
    }
    with pytest.raises(AssertionError, match="monotonicity"):
        audit_blockers(
            mc23_rows=mc23,
            mc24_rows=mc24,
            mc25_rows=mc25,
            previous=previous,
        )
