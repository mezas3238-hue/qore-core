from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r122_promotion_mechanism_attribution as r122,
)


def test_r122_source_is_pinned() -> None:
    assert r122.SOURCE_R121_RUN_ID == 36053069732
    assert r122.SOURCE_R121_ARTIFACT_ID == 10831129600
    assert r122.SOURCE_R121_ARTIFACT_DIGEST == (
        "sha256:583bbb93fbdf536565edcc234fdfff41"
        "8282968686422f7291645d0bd94823e5"
    )


def test_r122_expected_incremental_r_matches_r121() -> None:
    assert r122.EXPECTED_INCREMENTAL["5Y"] == {
        "primary": Decimal("3.157"),
        "secondary": Decimal("2.89775"),
    }
    assert r122.EXPECTED_INCREMENTAL["2Y"] == {
        "primary": Decimal("1.252125"),
        "secondary": Decimal("1.213"),
    }
    assert r122.EXPECTED_INCREMENTAL["R66"] == {
        "primary": Decimal("-0.4600234741784037558685446017"),
        "secondary": Decimal("-0.5375234741784037558685446009"),
    }


def test_r122_delta_metrics_only_measure_incremental_weight() -> None:
    rows = [
        {"outcome_r": "2.5", "delta_weight": "0.10"},
        {"outcome_r": "-1", "delta_weight": "0.05"},
    ]
    metrics = r122._delta_metrics(rows, stress=Decimal("0"))
    assert metrics["sample"] == 2
    assert metrics["total_incremental_r"] == "0.200"
    assert metrics["incremental_profit_factor"] == "5.0"
