from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r10_causal_memory_transfer_atlas import (
    CAPABLE,
    INVALIDATED,
    FeatureSpec,
    FrozenAnchor,
    PairSpec,
    _condition,
    evaluate_anchor,
    evaluate_pair,
    freeze_early_anchor,
)


def _row(year: int, outcome: str, value: str, other: str = "0") -> dict[str, object]:
    return {
        "year": year,
        "outcome_class": outcome,
        "feature": Decimal(value),
        "other": Decimal(other),
    }


def test_early_anchor_is_deterministic_midpoint_not_search() -> None:
    rows = [
        _row(2017, CAPABLE, "4"),
        _row(2018, CAPABLE, "6"),
        _row(2017, INVALIDATED, "1"),
        _row(2018, INVALIDATED, "3"),
    ]
    spec = FeatureSpec(
        code="TEST",
        feature="feature",
        channel="test",
        rationale="test",
    )
    anchor = freeze_early_anchor(rows, spec)
    assert anchor is not None
    assert anchor.direction == ">="
    assert anchor.early_capable_median == Decimal("5")
    assert anchor.early_invalidated_median == Decimal("2")
    assert anchor.threshold == Decimal("3.5")


def test_equal_early_medians_leave_feature_unresolved() -> None:
    rows = [
        _row(2017, CAPABLE, "2"),
        _row(2018, INVALIDATED, "2"),
    ]
    spec = FeatureSpec("TEST", "feature", "test", "test")
    assert freeze_early_anchor(rows, spec) is None


def test_frozen_condition_uses_same_threshold_later() -> None:
    anchor = FrozenAnchor(
        feature_code="TEST",
        feature="feature",
        direction="<=",
        threshold=Decimal("3"),
        early_capable_median=Decimal("2"),
        early_invalidated_median=Decimal("4"),
    )
    assert _condition(_row(2026, CAPABLE, "2.5"), anchor) is True
    assert _condition(_row(2026, INVALIDATED, "3.5"), anchor) is False


def test_anchor_transfer_reports_structural_capacity_not_pnl() -> None:
    anchor = FrozenAnchor(
        feature_code="TEST",
        feature="feature",
        direction=">=",
        threshold=Decimal("3"),
        early_capable_median=Decimal("4"),
        early_invalidated_median=Decimal("2"),
    )
    rows = [
        _row(2017, CAPABLE, "4"),
        _row(2017, INVALIDATED, "1"),
        _row(2022, CAPABLE, "5"),
        _row(2022, INVALIDATED, "2"),
        _row(2025, CAPABLE, "4"),
        _row(2025, INVALIDATED, "2"),
    ]
    report = evaluate_anchor(rows, anchor)
    assert report["recent_2024_2026"]["condition_true_capable_rate"] == "1"
    assert report["recent_2024_2026"]["condition_false_capable_rate"] == "0"
    assert report["recent_2024_2026"]["capable_rate_difference"] == "1"


def test_pair_transfer_requires_both_frozen_conditions() -> None:
    left = FrozenAnchor("LEFT", "feature", ">=", Decimal("3"), Decimal("4"), Decimal("2"))
    right = FrozenAnchor("RIGHT", "other", "<=", Decimal("2"), Decimal("1"), Decimal("3"))
    rows = [
        _row(2025, CAPABLE, "4", "1"),
        _row(2025, INVALIDATED, "4", "4"),
        _row(2025, INVALIDATED, "1", "1"),
    ]
    report = evaluate_pair(rows, left, right)
    recent = report["recent_2024_2026"]
    assert recent["conjunction_true_n"] == 1
    assert recent["conjunction_true_capable_rate"] == "1"
    assert recent["conjunction_false_capable_rate"] == "0"


def test_pair_spec_is_explicit_not_discovered() -> None:
    pair = PairSpec("PAIR", "LEFT", "RIGHT", "pre-registered")
    assert pair.left == "LEFT"
    assert pair.right == "RIGHT"
