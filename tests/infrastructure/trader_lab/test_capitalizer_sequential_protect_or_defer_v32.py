from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_causal_trigger_state_veto_policy_v29 as v29,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequential_protect_or_defer_v32 as v32,
)


def _model(intercept: float, dimension: int) -> v25.RidgeModel:
    return v25.RidgeModel(
        period="TRAIN",
        feature_mean=tuple(0.0 for _ in range(dimension)),
        feature_scale=tuple(1.0 for _ in range(dimension)),
        coefficients=(intercept, *tuple(0.0 for _ in range(dimension))),
        unique_training_trades=50,
        weighted_observations=50.0,
        feature_dimension=dimension,
        weighted_target_mean=intercept,
        weighted_training_rmse=0.1,
        coefficient_l2_norm=abs(intercept),
    )





def _trigger_state(family: str, trigger_at: str) -> v29.TriggerState:
    return v29.TriggerState(
        period="DEVELOPMENT_2024_2026",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        entry_at="2026-01-05T08:00:00+00:00",
        family=family,
        trigger_at=trigger_at,
        completed_m1_bars=3,
        vector=tuple(0.0 for _ in range(v29.TRAJECTORY_FEATURE_DIMENSION)),
    )


def _trade() -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T08:00:00+00:00",
        exit_at="2026-01-05T09:00:00+00:00",
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r="1",
        exit_reason="TIME_EXIT",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="1",
        same_minute_stop_target_ambiguity=False,
    )


def test_current_family_actions_never_select_future_family_early() -> None:
    assert v32.CURRENT_FAMILY_ACTIONS["TRIGGER_050"] == (
        "BE_AFTER_050",
        "STAGED_050_100_150",
    )
    assert v32.CURRENT_FAMILY_ACTIONS["TRIGGER_075"] == (
        "BE_AFTER_075",
        "LOCK025_AFTER_075",
        "STAGED_075_125_150",
    )
    assert v32.CURRENT_FAMILY_ACTIONS["TRIGGER_100"] == (
        "BE_AFTER_100",
        "LOCK025_AFTER_100",
        "LOCK050_AFTER_100",
    )


def test_selector_commits_only_when_both_external_models_pass() -> None:
    features = (0.0, 0.0, 0.0)
    action = "BE_AFTER_050"
    total_a = _model(0.40, len(features))
    total_b = _model(0.30, len(features))
    downside = _model(0.10, len(features))

    selected, score, predictions = v32._choose_current_action(
        features=features,
        actions=(action,),
        model_a={action: (total_a, downside)},
        model_b={action: (total_b, downside)},
    )

    assert selected == action
    assert score == 0.30
    assert predictions == (0.40, 0.30, 0.10, 0.10)


def test_selector_defers_when_one_external_model_rejects() -> None:
    features = (0.0, 0.0)
    action = "LOCK025_AFTER_075"
    positive = _model(0.20, len(features))
    negative = _model(-0.01, len(features))
    downside = _model(0.10, len(features))

    selected, score, predictions = v32._choose_current_action(
        features=features,
        actions=(action,),
        model_a={action: (positive, downside)},
        model_b={action: (negative, downside)},
    )

    assert selected is None
    assert score is None
    assert predictions is None


def test_next_event_time_preserves_global_chronology() -> None:
    ordered = (_trade(),)
    trigger = datetime(2026, 1, 5, 8, 5, tzinfo=UTC)
    pending = {
        ("GBPUSD", "2026-01-05T07:30:00+00:00"): (
            trigger,
            "TRIGGER_050",
            0,
        )
    }

    assert v32._next_event_time(
        ordered=ordered,
        pointer=0,
        pending=pending,
    ) == datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    assert v32._next_event_time(
        ordered=ordered,
        pointer=1,
        pending=pending,
    ) == trigger



def test_trigger_sequence_coalesces_same_timestamp_to_highest_family() -> None:
    period = "DEVELOPMENT_2024_2026"
    entry_at = "2026-01-05T08:00:00+00:00"
    native = {
        (period, "EURUSD", entry_at, "TRIGGER_050"): _trigger_state(
            "TRIGGER_050",
            "2026-01-05T08:03:00+00:00",
        ),
        (period, "EURUSD", entry_at, "TRIGGER_075"): _trigger_state(
            "TRIGGER_075",
            "2026-01-05T08:03:00+00:00",
        ),
        (period, "EURUSD", entry_at, "TRIGGER_100"): _trigger_state(
            "TRIGGER_100",
            "2026-01-05T08:05:00+00:00",
        ),
    }

    sequence = v32._trigger_sequence(
        period=period,
        symbol="EURUSD",
        entry_at=entry_at,
        native_states=native,
    )

    assert tuple((at.isoformat(), family) for at, family, _state in sequence) == (
        ("2026-01-05T08:03:00+00:00", "TRIGGER_075"),
        ("2026-01-05T08:05:00+00:00", "TRIGGER_100"),
    )


def test_trigger_sequence_rejects_true_reverse_chronology() -> None:
    period = "DEVELOPMENT_2024_2026"
    entry_at = "2026-01-05T08:00:00+00:00"
    native = {
        (period, "EURUSD", entry_at, "TRIGGER_050"): _trigger_state(
            "TRIGGER_050",
            "2026-01-05T08:05:00+00:00",
        ),
        (period, "EURUSD", entry_at, "TRIGGER_075"): _trigger_state(
            "TRIGGER_075",
            "2026-01-05T08:04:00+00:00",
        ),
    }

    with pytest.raises(ValueError, match="reverse chronology"):
        v32._trigger_sequence(
            period=period,
            symbol="EURUSD",
            entry_at=entry_at,
            native_states=native,
        )


def test_v32_frozen_contract() -> None:
    assert v32.IDENTITY == "QORE_CAPITALIZER_SEQUENTIAL_PROTECT_OR_DEFER_V32"
    assert v32.POLICY == "ROBUST_STAGEWISE_CURRENT_FAMILY_OR_DEFER"
    assert v32.REFERENCE_MODE == "ORIGINAL"
    assert v32.L2_PRIOR_STRENGTH == 12.0
    assert v32.SOURCE_TRIGGER_STATE_RUN_ID == 36283499014
    assert v32.EXPECTED_FEATURE_DIMENSION == 95
    assert v32.FAMILY_ORDER == (
        "TRIGGER_050",
        "TRIGGER_075",
        "TRIGGER_100",
    )
