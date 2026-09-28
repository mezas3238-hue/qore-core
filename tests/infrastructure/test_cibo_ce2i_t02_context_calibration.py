from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_t02_context_calibration import (
    T02CategoricalObservation,
    calibrate_t02_categorical_structure,
)


_BASE = datetime(2024, 1, 1, tzinfo=UTC)


def _row(
    index: int,
    *,
    state: str,
    stopped: bool,
    outcome: str,
) -> T02CategoricalObservation:
    return T02CategoricalObservation(
        entry_at=_BASE + timedelta(hours=index),
        contexts=(("state", state), ("side", "long")),
        stopped=stopped,
        structural_outcome_r=Decimal(outcome),
    )


def test_t02_context_selection_is_train_only_and_validates_out_of_sample() -> None:
    train = tuple(
        _row(
            index,
            state="precise" if index < 20 else "other",
            stopped=index in {1, 4, 22, 24, 26, 28},
            outcome="-1" if index in {1, 4, 22, 24, 26, 28} else "1",
        )
        for index in range(30)
    )
    validation = tuple(
        _row(
            30 + index,
            state="precise" if index < 10 else "other",
            stopped=index in {1, 11, 12, 13, 14},
            outcome="-1" if index in {1, 11, 12, 13, 14} else "1",
        )
        for index in range(20)
    )
    result = calibrate_t02_categorical_structure(
        lineage="SYNTHETIC",
        observations=train + validation,
        allowed_fields=("state",),
        train_fraction=Decimal("0.60"),
        minimum_train_rows=10,
        minimum_train_fraction=Decimal("0.10"),
        required_train_relative_improvement=Decimal("0.10"),
        minimum_validation_rows=10,
    )

    assert result.selected_field == "state"
    assert result.selected_value == "precise"
    assert result.minimum_validation_support_met is True
    assert result.strict_validation_stop_rate_improvement is True
    assert result.validation_tail_loss_not_worse is True
    assert result.eligible_for_structural_leverage is True


def test_t02_context_rejects_train_winner_that_fails_validation() -> None:
    train = tuple(
        _row(
            index,
            state="precise" if index < 20 else "other",
            stopped=index in {1, 4, 22, 24, 26, 28},
            outcome="-1" if index in {1, 4, 22, 24, 26, 28} else "1",
        )
        for index in range(30)
    )
    validation = tuple(
        _row(
            30 + index,
            state="precise" if index < 10 else "other",
            stopped=index in {0, 1, 2, 3, 4, 11},
            outcome="-1" if index in {0, 1, 2, 3, 4, 11} else "1",
        )
        for index in range(20)
    )
    result = calibrate_t02_categorical_structure(
        lineage="SYNTHETIC",
        observations=train + validation,
        allowed_fields=("state",),
        train_fraction=Decimal("0.60"),
        minimum_train_rows=10,
        minimum_train_fraction=Decimal("0.10"),
        required_train_relative_improvement=Decimal("0.10"),
        minimum_validation_rows=10,
    )

    assert result.selected_field == "state"
    assert result.eligible_for_structural_leverage is False
