from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_invariant_tail_risk_guardian_v33 as v33,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)


def _trade(index: int, realized_r: str) -> milestone.SimulatedTrade:
    entry = datetime(2026, 1, 5, 8, 0, tzinfo=UTC) + timedelta(
        minutes=index
    )
    return milestone.SimulatedTrade(
        symbol=f"S{index}",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at=entry.isoformat(),
        exit_at=(entry + timedelta(minutes=30)).isoformat(),
        entry_price="100",
        original_stop_price="99",
        final_stop_price="99",
        target_price="102",
        realized_gross_r=realized_r,
        exit_reason="TIME_EXIT",
        mode="ORIGINAL",
        protection_updates=0,
        first_protection_at=None,
        max_milestone_r_seen_before_exit="1",
        same_minute_stop_target_ambiguity=False,
    )


def _model(coefficients: tuple[float, ...]) -> v25.RidgeModel:
    dimension = len(coefficients) - 1
    return v25.RidgeModel(
        period="TRAIN",
        feature_mean=tuple(0.0 for _ in range(dimension)),
        feature_scale=tuple(1.0 for _ in range(dimension)),
        coefficients=coefficients,
        unique_training_trades=50,
        weighted_observations=50.0,
        feature_dimension=dimension,
        weighted_target_mean=coefficients[0],
        weighted_training_rmse=0.1,
        coefficient_l2_norm=sum(
            value * value for value in coefficients[1:]
        ) ** 0.5,
    )


def _head(
    coefficients: tuple[float, ...],
    residual_q20: float = 0.0,
) -> v33.CalibratedHead:
    return v33.CalibratedHead(
        model=_model(coefficients),
        residual_q20=residual_q20,
        chronological_residual_count=20,
    )


def test_episode_relief_targets_sequence_drawdown_not_trade_only() -> None:
    ledger = (
        _trade(0, "2"),
        _trade(1, "-1"),
        _trade(2, "-1"),
        _trade(3, "2"),
    )
    key = (ledger[1].symbol, ledger[1].entry_at)

    relief = v33._episode_relief(
        ledger,
        key=key,
        counterfactual_scaled_r=Decimal("0"),
    )

    assert relief == Decimal("1")


def test_invariant_mask_removes_cross_era_sign_flips() -> None:
    left = _model((0.1, 0.5, -0.2, 0.3))
    right = _model((0.2, 0.4, 0.1, -0.4))

    assert v33._invariant_mask(left, right) == (
        True,
        False,
        False,
    )


def test_pair_lcb_uses_only_invariant_dimensions_and_residual_floor() -> None:
    left = _head((0.2, 0.5, 0.3), residual_q20=-0.1)
    right = _head((0.1, 0.4, -0.2), residual_q20=-0.05)

    left_lcb, right_lcb, count = v33._pair_lcbs(
        left=left,
        right=right,
        features=(1.0, 10.0),
    )

    assert count == 1
    assert round(left_lcb, 8) == 0.6
    assert round(right_lcb, 8) == 0.45


def test_action_requires_well_supported_tail_and_economic_lcbs() -> None:
    features = (1.0,)
    action = "LOCK025_AFTER_075"

    positive_episode_a = _head((0.3, 0.2), residual_q20=-0.05)
    positive_episode_b = _head((0.25, 0.1), residual_q20=-0.05)
    positive_total_a = _head((0.2, 0.1), residual_q20=-0.05)
    positive_total_b = _head((0.15, 0.1), residual_q20=-0.05)
    positive_down_a = _head((0.1, 0.1), residual_q20=-0.05)
    positive_down_b = _head((0.1, 0.1), residual_q20=-0.05)

    selected, score, lcbs, dims, epistemic = v33._choose_action(
        features=features,
        surface_mode="BE_AFTER_050",
        actions=("BE_AFTER_050", action),
        model_a={
            action: v33.ActionHeads(
                episode_relief=positive_episode_a,
                total_delta=positive_total_a,
                downside_delta=positive_down_a,
            )
        },
        model_b={
            action: v33.ActionHeads(
                episode_relief=positive_episode_b,
                total_delta=positive_total_b,
                downside_delta=positive_down_b,
            )
        },
    )

    assert selected == action
    assert score is not None and score > 0
    assert lcbs is not None
    assert min(dims) == 1
    assert epistemic == "WELL_SUPPORTED"


def test_action_fails_closed_when_era_coefficients_conflict() -> None:
    features = (1.0,)
    action = "LOCK025_AFTER_075"
    good = _head((0.4, 0.2))
    conflict = _head((0.4, -0.2))

    selected, score, lcbs, dims, epistemic = v33._choose_action(
        features=features,
        surface_mode="BE_AFTER_050",
        actions=("BE_AFTER_050", action),
        model_a={
            action: v33.ActionHeads(
                episode_relief=good,
                total_delta=good,
                downside_delta=good,
            )
        },
        model_b={
            action: v33.ActionHeads(
                episode_relief=conflict,
                total_delta=conflict,
                downside_delta=conflict,
            )
        },
    )

    assert selected is None
    assert score is None
    assert lcbs is None
    assert dims == (0, 0, 0)
    assert epistemic == "CONFLICTED"



def test_batch_ridge_is_mathematically_equivalent_to_v25_fit() -> None:
    features = (
        (0.0, 1.0),
        (1.0, 0.0),
        (1.0, 1.0),
        (2.0, -1.0),
        (-1.0, 2.0),
        (0.5, -0.5),
    )
    keys = tuple(
        (f"S{index}", f"2026-01-05T08:0{index}:00+00:00")
        for index in range(len(features))
    )
    values = (0.1, -0.2, 0.3, 0.5, -0.4, 0.2)
    target_id = ("LOCK025_AFTER_075", "TOTAL")
    actual = v33._fit_many(
        label="TEST",
        features=features,
        keys=keys,
        targets={target_id: values},
    )[target_id]
    expected = v25._fit_model(
        period="TEST",
        examples=tuple(
            (feature, target, 1.0, key)
            for feature, target, key in zip(
                features,
                values,
                keys,
                strict=True,
            )
        ),
    )

    assert actual.feature_mean == pytest.approx(expected.feature_mean)
    assert actual.feature_scale == pytest.approx(expected.feature_scale)
    assert actual.coefficients == pytest.approx(expected.coefficients)
    assert actual.weighted_target_mean == pytest.approx(
        expected.weighted_target_mean
    )
    assert actual.weighted_training_rmse == pytest.approx(
        expected.weighted_training_rmse
    )



def test_v33_frozen_contract() -> None:
    assert v33.IDENTITY == (
        "QORE_CAPITALIZER_COGNITIVE_INVARIANT_TAIL_RISK_GUARDIAN_V33"
    )
    assert v33.POLICY == (
        "SURFACE_DEFAULT_COGNITIVE_INVARIANT_TAIL_RISK_OVERRIDE"
    )
    assert v33.L2_PRIOR_STRENGTH == 12.0
    assert v33.SOURCE_TRIGGER_STATE_RUN_ID == 36283499014
    assert v33.CHRONOLOGICAL_FOLDS == 5
    assert v33.MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES == 10
    assert v33.RESIDUAL_QUANTILE == 0.20
    assert v33.EXPECTED_FEATURE_DIMENSION == 95
    assert len(v33.ACTION_ORDER) == 9
