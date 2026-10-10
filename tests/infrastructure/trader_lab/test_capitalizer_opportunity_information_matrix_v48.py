import math

import pytest

from qore.infrastructure.trader_lab.capitalizer_opportunity_information_matrix_v48 import (
    V48GateObservation,
    build_information_matrix,
    pair_metrics,
)


def _observations() -> tuple[V48GateObservation, ...]:
    return (
        V48GateObservation("r1", "FTM", {"CISD": True, "PROTECTED_SWING": True, "FVG": True}),
        V48GateObservation("r2", "FTM", {"CISD": True, "PROTECTED_SWING": True, "FVG": False}),
        V48GateObservation("r3", "FTM", {"CISD": True, "PROTECTED_SWING": True, "FVG": True}),
        V48GateObservation("r4", "FTM", {"CISD": False, "PROTECTED_SWING": False, "FVG": False}),
        V48GateObservation("x1", "FRACTAL", {"CISD": True, "PROTECTED_SWING": False, "FVG": True}),
    )


def test_pair_metrics_are_route_scoped() -> None:
    metrics = pair_metrics(
        _observations(),
        route="FTM",
        gate_a="CISD",
        gate_b="PROTECTED_SWING",
    )

    assert metrics.population == 4
    assert metrics.a_true == 3
    assert metrics.b_true == 3
    assert metrics.both_true == 3
    assert metrics.p_b_given_a == 1.0
    assert metrics.p_a_given_b == 1.0
    assert metrics.jaccard == 1.0
    assert metrics.mutual_information_bits > 0.0


def test_matrix_returns_every_unique_pair_without_using_outcomes() -> None:
    matrix = build_information_matrix(
        _observations(),
        route="FTM",
        gate_names=("CISD", "PROTECTED_SWING", "FVG"),
    )

    assert len(matrix.pairs) == 3
    assert matrix.outcome_fields_used is False
    assert matrix.fresh_holdout_used is False
    assert matrix.automatic_gate_removal_allowed is False


def test_pair_metrics_report_partial_overlap() -> None:
    metrics = pair_metrics(
        _observations(),
        route="FTM",
        gate_a="CISD",
        gate_b="FVG",
    )

    assert metrics.p_b_given_a == pytest.approx(2 / 3)
    assert metrics.p_a_given_b == 1.0
    assert metrics.jaccard == pytest.approx(2 / 3)
    assert math.isfinite(metrics.mutual_information_bits)


def test_cross_route_data_does_not_change_ftm_metrics() -> None:
    base = _observations()[:4]
    with_other_route = _observations()

    a = pair_metrics(base, route="FTM", gate_a="CISD", gate_b="FVG")
    b = pair_metrics(with_other_route, route="FTM", gate_a="CISD", gate_b="FVG")

    assert a == b


def test_missing_gate_fails_closed() -> None:
    rows = (
        V48GateObservation("r1", "FTM", {"CISD": True}),
        V48GateObservation("r2", "FTM", {"CISD": False, "FVG": True}),
    )

    with pytest.raises(ValueError, match="missing gate values"):
        pair_metrics(rows, route="FTM", gate_a="CISD", gate_b="FVG")
