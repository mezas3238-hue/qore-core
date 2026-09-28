from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_t02_burned_calibration import (
    T02StructuralObservation,
    calibrate_t02_structural_precision,
)

_BASE = datetime(2024, 1, 1, tzinfo=UTC)


def _row(
    index: int,
    *,
    ratio: str,
    stopped: bool,
    outcome_r: str,
) -> T02StructuralObservation:
    return T02StructuralObservation(
        entry_at=_BASE + timedelta(hours=index),
        stop_to_target_ratio=Decimal(ratio),
        stopped=stopped,
        structural_outcome_r=Decimal(outcome_r),
    )


def test_t02_probe_requires_strict_oos_stop_rate_improvement() -> None:
    train = tuple(
        _row(index, ratio="0.50", stopped=False, outcome_r="1")
        for index in range(10)
    )
    validation = (
        _row(10, ratio="0.40", stopped=False, outcome_r="1"),
        _row(11, ratio="0.45", stopped=False, outcome_r="1"),
        _row(12, ratio="0.48", stopped=False, outcome_r="1"),
        _row(13, ratio="0.80", stopped=True, outcome_r="-1"),
        _row(14, ratio="0.90", stopped=True, outcome_r="-1"),
        _row(15, ratio="1.00", stopped=True, outcome_r="-1"),
    )
    result = calibrate_t02_structural_precision(
        lineage="SYNTHETIC",
        observations=train + validation,
        train_fraction=Decimal("0.625"),
        minimum_validation_candidate_rows=3,
    )

    assert result.strict_stop_rate_improvement is True
    assert result.tail_loss_not_worse is True
    assert result.minimum_validation_sample_met is True
    assert result.eligible_for_structural_leverage is True


def test_t02_probe_falsifies_non_improving_precision_proxy() -> None:
    train = tuple(
        _row(index, ratio="0.50", stopped=False, outcome_r="1")
        for index in range(10)
    )
    validation = (
        _row(10, ratio="0.40", stopped=True, outcome_r="-1"),
        _row(11, ratio="0.45", stopped=True, outcome_r="-1"),
        _row(12, ratio="0.48", stopped=True, outcome_r="-1"),
        _row(13, ratio="0.80", stopped=False, outcome_r="1"),
        _row(14, ratio="0.90", stopped=False, outcome_r="1"),
        _row(15, ratio="1.00", stopped=False, outcome_r="1"),
    )
    result = calibrate_t02_structural_precision(
        lineage="SYNTHETIC",
        observations=train + validation,
        train_fraction=Decimal("0.625"),
        minimum_validation_candidate_rows=3,
    )

    assert result.strict_stop_rate_improvement is False
    assert result.eligible_for_structural_leverage is False
