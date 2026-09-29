from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_target_ambiguity_v47_s1r_d as target,
)


def test_target_pair_classifier_distinguishes_all_frozen_ambiguity_classes() -> None:
    assert (
        target.classify_target_pairs(set())
        is target.TargetAmbiguityClass.ZERO_ELIGIBLE_TARGETS
    )
    assert target.classify_target_pairs(
        {("HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE", Decimal("101"))}
    ) is target.TargetAmbiguityClass.ONE_UNIQUE_PRICE_AND_KIND
    assert target.classify_target_pairs(
        {
            ("HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE", Decimal("101")),
            ("HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE", Decimal("102")),
        }
    ) is target.TargetAmbiguityClass.MULTIPLE_DISTINCT_PRICES_SAME_KIND
    assert target.classify_target_pairs(
        {
            ("HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE", Decimal("101")),
            ("RECENT_DAILY_HIGH_LOW", Decimal("101")),
        }
    ) is target.TargetAmbiguityClass.SAME_PRICE_MULTIPLE_KINDS
    assert target.classify_target_pairs(
        {
            ("HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE", Decimal("101")),
            ("RECENT_DAILY_HIGH_LOW", Decimal("102")),
        }
    ) is target.TargetAmbiguityClass.MULTIPLE_DISTINCT_PRICES_AND_KINDS


def test_target_period_report_requires_exhaustive_resolution_partition() -> None:
    with pytest.raises(ValueError, match="classification coverage drift"):
        target.TargetPeriodMarketReport(
            identity=target.IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            source_events=10,
            aligned_h1_strict_m15_events=2,
            ambiguity_counts={
                target.TargetAmbiguityClass.ONE_UNIQUE_PRICE_AND_KIND.value: 1
            },
            provenance_counts={},
            resolved_under_current_s0=1,
            unresolved_under_current_s0=1,
        )
