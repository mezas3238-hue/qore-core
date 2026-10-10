from types import SimpleNamespace
from typing import cast

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_hypothesis_survival_model_v21 as v21,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)


def _row(**overrides: object) -> v21.Observation:
    values: dict[str, object] = {
        "period": "P",
        "symbol": "EURUSD",
        "session": "LONDON",
        "operating_date": "2026-01-01",
        "side": "LONG",
        "entry_at": "2026-01-01T10:00:00+00:00",
        "observed_at": "2026-01-01T10:05:00+00:00",
        "phase": "INVALIDATING",
        "elapsed_full_bars": 5,
        "max_favorable_r": "0.10",
        "close_r": "-0.30",
        "adverse_close_count": 2,
        "invalidating_age": 1,
        "adverse_displacement_observed": True,
        "displacement_midpoint_reclaimed": False,
        "adverse_extreme_extended": False,
        "recovered_since_deterioration": False,
    }
    values.update(overrides)
    return v21.Observation(**values)  # type: ignore[arg-type]


def test_augmentation_encodes_velocity_availability() -> None:
    rows = (
        _row(observed_at="2026-01-01T10:01:00+00:00", close_r="-0.10"),
        _row(observed_at="2026-01-01T10:02:00+00:00", close_r="-0.15"),
        _row(observed_at="2026-01-01T10:03:00+00:00", close_r="-0.05"),
    )
    augmented = v25._augment_observations(rows)
    assert augmented[0].velocity_1_available is False
    assert augmented[0].velocity_2_available is False
    assert augmented[1].velocity_1_available is True
    assert augmented[1].velocity_2_available is False
    assert abs(augmented[1].velocity_1_r + 0.05) < 1e-12
    assert augmented[2].velocity_2_available is True
    assert abs(augmented[2].velocity_2_r - 0.05) < 1e-12


def test_trade_weights_sum_to_one_per_trade() -> None:
    examples: tuple[v25.TrainingExample, ...] = (
        ((1.0, 0.0), 1.0, 0.5, ("A", "1")),
        ((2.0, 0.0), 2.0, 0.5, ("A", "1")),
        ((0.0, 1.0), -1.0, 1.0, ("B", "2")),
    )
    total_by_trade: dict[tuple[str, str], float] = {}
    for _features, _target, weight, key in examples:
        total_by_trade[key] = total_by_trade.get(key, 0.0) + weight
    assert total_by_trade == {("A", "1"): 1.0, ("B", "2"): 1.0}


def test_ridge_model_is_regularized_and_predicts_direction() -> None:
    examples: tuple[v25.TrainingExample, ...] = (
        ((-2.0,), -1.0, 1.0, ("A", "1")),
        ((-1.0,), -0.5, 1.0, ("B", "2")),
        ((1.0,), 0.5, 1.0, ("C", "3")),
        ((2.0,), 1.0, 1.0, ("D", "4")),
    )
    model = v25._fit_model(period="TRAIN", examples=examples)
    assert model.unique_training_trades == 4
    assert model.feature_dimension == 1
    assert model.coefficient_l2_norm > 0
    assert v25._predict(model, (2.0,)) > 0
    assert v25._predict(model, (-2.0,)) < 0


def test_feature_vector_excludes_identity_and_includes_mode() -> None:
    item = v25.AugmentedObservation(
        row=_row(),
        velocity_1_r=-0.1,
        velocity_1_available=True,
        velocity_2_r=-0.2,
        velocity_2_available=True,
    )
    pretrade = SimpleNamespace(
        point=SimpleNamespace(vector=(0.1, 0.2, 0.3)),
        base_multiplier=0.75,
        mode=v25.MODE_VALUES[0],
    )
    features = v25._feature_vector(item, cast(v10.Pretrade, pretrade))
    assert features[:3] == (0.1, 0.2, 0.3)
    assert features[3] == 0.75
    assert len(features) == (
        3 + 1 + len(v25.MODE_VALUES) + 10 + len(v25.PHASE_VALUES) + 4
    )


def test_v25_frozen_contract() -> None:
    assert v25.POLICY == "INVALIDATING_RIDGE_POSBOTH_P2"
    assert v25.L2_PRIOR_STRENGTH == 12.0
    assert v25.PERSISTENCE_REQUIRED == 2
