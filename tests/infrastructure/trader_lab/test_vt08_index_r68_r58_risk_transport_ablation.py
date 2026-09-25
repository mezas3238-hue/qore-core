from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r55_distributed_causal_risk as r55,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r68_r58_risk_transport_ablation as r68,
)


def test_r68_ablation_is_small_mechanistic_and_not_grid_search() -> None:
    ids = [policy.policy_id for policy in r68.POLICIES]
    assert ids == [
        "EXACT_R58",
        "CAPPED_R47_BASE",
        "ABLATE_REARM",
        "ABLATE_FVG_CROSS",
        "ABLATE_FVG_H4_CISD",
        "ABLATE_LATE_REVALIDATION",
        "LATE_REVALIDATION_ONLY",
    ]
    assert len(ids) == len(set(ids)) == 7


def test_r68_exact_policy_matches_r58_mechanisms() -> None:
    exact = r68.POLICIES[0]
    assert exact.structural_rearm is True
    assert exact.fvg_cross_index is True
    assert exact.fvg_h4_cisd is True
    assert exact.late_revalidation is True
    assert r68.MAX_REQUESTED_WEIGHT == r55.MAX_REQUESTED_WEIGHT
    assert r68.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
    assert r68.PORTFOLIO_BUDGET_R == Decimal("0.75")


def test_r68_capped_base_and_late_only_are_explicit() -> None:
    capped = r68.POLICIES[1]
    assert not any(
        (
            capped.structural_rearm,
            capped.fvg_cross_index,
            capped.fvg_h4_cisd,
            capped.late_revalidation,
        )
    )

    late = r68.POLICIES[-1]
    assert late.structural_rearm is False
    assert late.fvg_cross_index is False
    assert late.fvg_h4_cisd is False
    assert late.late_revalidation is True


def test_r68_availability_reports_partial_m15_without_repairing_data() -> None:
    provenance = {
        "SP500": {
            "m15_bucket_size_counts": {"1": 10, "2": 20, "3": 70},
            "m15_buckets": 100,
            "raw_m5_rows_loaded": 260,
            "interpolated_prices": 0,
            "synthetic_prices": 0,
        }
    }
    row = r68._availability(provenance)["SP500"]
    assert row["complete_three_m5_buckets"] == 70
    assert row["partial_m15_buckets"] == 30
    assert Decimal(row["complete_fraction"]) == Decimal("0.7")
    assert Decimal(row["partial_fraction"]) == Decimal("0.3")
    assert row["interpolated_prices"] == 0
    assert row["synthetic_prices"] == 0
