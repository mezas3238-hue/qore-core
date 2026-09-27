from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_deferred_existing_mode_commitment_v30 as v30,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)


def _trade(
    *,
    mode: str,
    first_protection_at: str | None,
    exit_at: str = "2026-01-05T09:00:00+00:00",
) -> milestone.SimulatedTrade:
    return milestone.SimulatedTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T08:00:00+00:00",
        exit_at=exit_at,
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r="1",
        exit_reason="TIME_EXIT",
        mode=mode,
        protection_updates=0,
        first_protection_at=first_protection_at,
        max_milestone_r_seen_before_exit="1",
        same_minute_stop_target_ambiguity=False,
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


def test_mode_reachability_allows_later_mode_at_050() -> None:
    key = ("EURUSD", "2026-01-05T08:00:00+00:00")
    modes = {
        "ORIGINAL": {
            key: _trade(mode="ORIGINAL", first_protection_at=None),
        },
        "BE_AFTER_050": {
            key: _trade(
                mode="BE_AFTER_050",
                first_protection_at="2026-01-05T08:03:00+00:00",
            ),
        },
        "STAGED_075_125_150": {
            key: _trade(
                mode="STAGED_075_125_150",
                first_protection_at="2026-01-05T08:05:00+00:00",
            ),
        },
    }

    assert v30._mode_reachable(
        key=key,
        action="STAGED_075_125_150",
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )
    assert v30._mode_reachable(
        key=key,
        action="ORIGINAL",
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )
    assert not v30._mode_reachable(
        key=key,
        action="BE_AFTER_050",
        trigger_at="2026-01-05T08:04:00+00:00",
        modes=modes,
    )


def test_mode_reachability_rejects_trade_already_exited() -> None:
    key = ("EURUSD", "2026-01-05T08:00:00+00:00")
    modes = {
        "ORIGINAL": {
            key: _trade(
                mode="ORIGINAL",
                first_protection_at=None,
                exit_at="2026-01-05T08:02:00+00:00",
            ),
        },
    }

    assert not v30._mode_reachable(
        key=key,
        action="ORIGINAL",
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )


def test_deferred_commitment_is_detected() -> None:
    key = ("EURUSD", "2026-01-05T08:00:00+00:00")
    modes = {
        "ORIGINAL": {
            key: _trade(mode="ORIGINAL", first_protection_at=None),
        },
        "STAGED_075_125_150": {
            key: _trade(
                mode="STAGED_075_125_150",
                first_protection_at="2026-01-05T08:05:00+00:00",
            ),
        },
        "BE_AFTER_050": {
            key: _trade(
                mode="BE_AFTER_050",
                first_protection_at="2026-01-05T08:03:00+00:00",
            ),
        },
    }

    assert v30._is_deferred_commitment(
        key=key,
        action="STAGED_075_125_150",
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )
    assert v30._is_deferred_commitment(
        key=key,
        action="ORIGINAL",
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )
    assert not v30._is_deferred_commitment(
        key=key,
        action="BE_AFTER_050",
        trigger_at="2026-01-05T08:03:00+00:00",
        modes=modes,
    )


def test_robust_selector_can_choose_later_mode() -> None:
    features = (0.0, 0.0, 0.0)
    same_total = _model(0.20, len(features))
    same_downside = _model(0.10, len(features))
    later_total_a = _model(0.60, len(features))
    later_total_b = _model(0.50, len(features))
    later_downside = _model(0.20, len(features))

    action, score, predictions = v30._choose_mode(
        features=features,
        surface_mode="BE_AFTER_050",
        actions=("BE_AFTER_050", "STAGED_075_125_150"),
        model_a={
            "BE_AFTER_050": (same_total, same_downside),
            "STAGED_075_125_150": (later_total_a, later_downside),
        },
        model_b={
            "BE_AFTER_050": (same_total, same_downside),
            "STAGED_075_125_150": (later_total_b, later_downside),
        },
    )

    assert action == "STAGED_075_125_150"
    assert score == 0.50
    assert predictions == (0.60, 0.50, 0.20, 0.20)


def test_v30_frozen_contract() -> None:
    assert v30.IDENTITY == "QORE_CAPITALIZER_DEFERRED_EXISTING_MODE_COMMITMENT_V30"
    assert v30.POLICY == "TRIGGER_STATE_ROBUST_DEFERRED_EXISTING_MODE_COMMITMENT"
    assert v30.L2_PRIOR_STRENGTH == 12.0
    assert v30.SOURCE_TRIGGER_STATE_RUN_ID == 36283499014
    assert len(v30.ACTION_ORDER) == 9
    assert set(v30.ACTION_ORDER) == {
        mode.value for mode in milestone.ProtectionMode
    }
