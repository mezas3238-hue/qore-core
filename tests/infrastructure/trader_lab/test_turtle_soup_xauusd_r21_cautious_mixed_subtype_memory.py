from __future__ import annotations

from collections import Counter

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r21_cautious_mixed_subtype_memory import (
    ABSTAIN,
    RECOVERABLE,
    UNRESOLVED,
    WAIT,
    _label,
    _stable_label,
    _strict_majority,
)


def test_structural_label_prefers_immediate_capacity() -> None:
    assert _label(
        {"capable": True},
        {"capable": True},
    ) == RECOVERABLE


def test_structural_label_waits_only_when_retest_recovers_capacity() -> None:
    assert _label(
        {"capable": False},
        {"capable": True},
    ) == WAIT


def test_structural_label_abstains_when_neither_entry_preserves_capacity() -> None:
    assert _label(
        {"capable": False},
        {"capable": False},
    ) == ABSTAIN


def test_strict_majority_rejects_ties_and_half() -> None:
    assert _strict_majority(Counter({RECOVERABLE: 3, ABSTAIN: 2})) == RECOVERABLE
    assert _strict_majority(Counter({RECOVERABLE: 2, ABSTAIN: 2})) is None


def test_stable_label_requires_same_majority_all_periods_and_sample_floor() -> None:
    rows = []
    for period in (
        "early_2016_2020",
        "transition_2021_2023",
        "recent_2024_2026",
    ):
        rows.extend(
            {"period": period, "structural_label": RECOVERABLE}
            for _ in range(4)
        )
        rows.append({"period": period, "structural_label": ABSTAIN})
    result = _stable_label(rows)
    assert result["classification"] == RECOVERABLE
    assert result["stable_across_all_periods"] is True

    insufficient = [
        {"period": "early_2016_2020", "structural_label": RECOVERABLE},
        {"period": "transition_2021_2023", "structural_label": RECOVERABLE},
        {"period": "recent_2024_2026", "structural_label": RECOVERABLE},
    ]
    result = _stable_label(insufficient)
    assert result["classification"] == UNRESOLVED
