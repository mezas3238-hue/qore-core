from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_full_stop_causal_separability_v37 as v37,
)


def _trade(reason: str) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T08:00:00+00:00",
        exit_at="2026-01-05T09:00:00+00:00",
        entry_price="1.10",
        original_stop_price="1.09",
        final_stop_price="1.09",
        target_price="1.12",
        realized_gross_r="-1" if reason == "STOP" else "2",
        exit_reason=reason,
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="0",
        same_minute_stop_target_ambiguity=False,
    )


def test_original_exit_label_only_accepts_stop_or_target() -> None:
    assert v37._label_original(_trade("STOP")) == "STOP"
    assert v37._label_original(_trade("TARGET")) == "TARGET"
    assert v37._label_original(_trade("SESSION_CLOSE")) is None


def test_auc_is_one_for_perfect_stop_ranking() -> None:
    evidence = v37._auc(
        labels=(0, 0, 1, 1),
        scores=(0.1, 0.2, 0.8, 0.9),
    )

    assert evidence.auc == "1.0"
    assert evidence.stops == 2
    assert evidence.targets == 2
    assert float(evidence.lower_95) > 0.5


def test_auc_is_half_for_complete_ties() -> None:
    evidence = v37._auc(
        labels=(0, 1, 0, 1),
        scores=(0.5, 0.5, 0.5, 0.5),
    )

    assert evidence.auc == "0.5"
    assert float(evidence.lower_95) <= 0.5


def test_quantile_is_deterministic_nearest_rank() -> None:
    values = tuple(float(value) for value in range(1, 11))

    assert v37._quantile(values, 0.90) == 9.0


def test_training_examples_use_labels_only_as_targets() -> None:
    state_stop = v37.LabeledEntryState(
        period="P",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        entry_at="2026-01-05T08:00:00+00:00",
        label="STOP",
        original_realized_r="-1",
        vector=(0.1, 0.2),
    )
    state_target = v37.LabeledEntryState(
        period="P",
        symbol="GBPUSD",
        session="LONDON",
        operating_date="2026-01-05",
        entry_at="2026-01-05T08:10:00+00:00",
        label="TARGET",
        original_realized_r="2",
        vector=(0.3, 0.4),
    )

    examples = v37._training_examples((state_stop, state_target))

    assert examples[0][0] == (0.1, 0.2)
    assert examples[0][1] == 1.0
    assert examples[1][0] == (0.3, 0.4)
    assert examples[1][1] == 0.0
    assert state_stop.label_visible_to_features is False
    assert state_target.label_visible_to_features is False
