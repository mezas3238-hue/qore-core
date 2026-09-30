from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_causal_information_frontier_v1 as cif,
)


def test_oracle_class_preserve_optionality() -> None:
    label, regret, optimal = cif._oracle_class(
        surface_mode="BE_AFTER_050",
        family="TRIGGER_050",
        action_values={
            "ORIGINAL": Decimal("2"),
            "BE_AFTER_050": Decimal("0"),
            "BE_AFTER_075": Decimal("0"),
            "BE_AFTER_100": Decimal("0"),
            "LOCK025_AFTER_075": Decimal("0.25"),
            "LOCK025_AFTER_100": Decimal("0.25"),
            "LOCK050_AFTER_100": Decimal("0.50"),
            "STAGED_050_100_150": Decimal("0.25"),
            "STAGED_075_125_150": Decimal("0.25"),
        },
    )

    assert label == cif.PRESERVE_OPTIONALITY
    assert regret == Decimal("2")
    assert optimal == ("ORIGINAL",)


def test_oracle_class_intervene_now() -> None:
    label, regret, optimal = cif._oracle_class(
        surface_mode="BE_AFTER_050",
        family="TRIGGER_050",
        action_values={
            "ORIGINAL": Decimal("-1"),
            "BE_AFTER_050": Decimal("-1"),
            "BE_AFTER_075": Decimal("-1"),
            "BE_AFTER_100": Decimal("-1"),
            "LOCK025_AFTER_075": Decimal("-1"),
            "LOCK025_AFTER_100": Decimal("-1"),
            "LOCK050_AFTER_100": Decimal("-1"),
            "STAGED_050_100_150": Decimal("0"),
            "STAGED_075_125_150": Decimal("-1"),
        },
    )

    assert label == cif.INTERVENE_NOW
    assert regret == Decimal("1")
    assert optimal == ("STAGED_050_100_150",)


def test_surface_optimal_takes_precedence_over_tied_horizons() -> None:
    label, regret, optimal = cif._oracle_class(
        surface_mode="BE_AFTER_050",
        family="TRIGGER_050",
        action_values={
            "ORIGINAL": Decimal("0"),
            "BE_AFTER_050": Decimal("0"),
            "BE_AFTER_075": Decimal("-1"),
            "BE_AFTER_100": Decimal("-1"),
            "LOCK025_AFTER_075": Decimal("-1"),
            "LOCK025_AFTER_100": Decimal("-1"),
            "LOCK050_AFTER_100": Decimal("-1"),
            "STAGED_050_100_150": Decimal("-1"),
            "STAGED_075_125_150": Decimal("-1"),
        },
    )

    assert label == cif.SURFACE_OPTIMAL
    assert regret == Decimal("0")
    assert optimal == ("ORIGINAL", "BE_AFTER_050")


def test_geometry_distance_is_zero_for_same_vector() -> None:
    rows = (
        cif._StateSample(
            period="P",
            symbol="A",
            entry_at="2026-01-01T00:00:00+00:00",
            family="TRIGGER_050",
            surface_mode="BE_AFTER_050",
            trigger_at="2026-01-01T00:01:00+00:00",
            current_dd_r=Decimal("1"),
            active_drawdown=True,
            entrant_in_max_dd_descent=True,
            vector=tuple(float(index) for index in range(cif.EXPECTED_FEATURE_DIMENSION)),
            surface_scaled_r=Decimal("0"),
            best_scaled_r=Decimal("1"),
            surface_regret_r=Decimal("1"),
            optimal_actions=("ORIGINAL",),
            oracle_class=cif.PRESERVE_OPTIONALITY,
            action_deltas=(("ORIGINAL", Decimal("1")),),
        ),
        cif._StateSample(
            period="P",
            symbol="B",
            entry_at="2026-01-01T00:02:00+00:00",
            family="TRIGGER_050",
            surface_mode="BE_AFTER_050",
            trigger_at="2026-01-01T00:03:00+00:00",
            current_dd_r=Decimal("1"),
            active_drawdown=True,
            entrant_in_max_dd_descent=False,
            vector=tuple(
                float(index + 1)
                for index in range(cif.EXPECTED_FEATURE_DIMENSION)
            ),
            surface_scaled_r=Decimal("0"),
            best_scaled_r=Decimal("1"),
            surface_regret_r=Decimal("1"),
            optimal_actions=("ORIGINAL",),
            oracle_class=cif.PRESERVE_OPTIONALITY,
            action_deltas=(("ORIGINAL", Decimal("1")),),
        ),
    )
    geometry = cif._geometry(rows)

    assert cif._distance(geometry, rows[0].vector, rows[0].vector) == 0.0
    assert cif._distance(geometry, rows[0].vector, rows[1].vector) > 0.0


def test_causal_information_frontier_contract() -> None:
    assert cif.IDENTITY == "QORE_CAPITALIZER_CAUSAL_INFORMATION_FRONTIER_V1"
    assert cif.EXPECTED_FEATURE_DIMENSION == 95
    assert cif.ORACLE_CLASSES == (
        "SURFACE_OPTIMAL",
        "INTERVENE_NOW",
        "PRESERVE_OPTIONALITY",
        "MIXED_OPTIMUM",
    )
