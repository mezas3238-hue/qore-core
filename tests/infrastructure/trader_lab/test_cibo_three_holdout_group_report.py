from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "cibo_three_holdout_group_report.py"
)
SPEC = importlib.util.spec_from_file_location(
    "cibo_three_holdout_group_report",
    SCRIPT,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _rows() -> list[dict[str, object]]:
    values = (
        Decimal("1.20"),
        Decimal("-0.30"),
        Decimal("0.90"),
        Decimal("0.60"),
        Decimal("0.80"),
        Decimal("0.50"),
        Decimal("0.70"),
        Decimal("0.40"),
        Decimal("0.65"),
        Decimal("0.75"),
        Decimal("0.55"),
        Decimal("0.85"),
    )
    return [
        {
            "pnl": value,
            "gross": value + Decimal("0.10"),
            "provider_cost": Decimal("0.10"),
            "time": f"2026-01-{index + 1:02d}T00:00:00+00:00",
            "signal": f"s{index}",
            "trader": "VT08_FOREX",
            "kind": "CORE",
        }
        for index, value in enumerate(values)
    ]


def test_scientific_battery_contains_all_required_layers() -> None:
    report = MODULE.scientific_battery(_rows(), salt="unit")
    assert set(report) == {
        "metrics",
        "chronological_blocks",
        "walk_forward",
        "monte_carlo",
        "stress",
    }
    assert set(report["walk_forward"]) == {"5", "6"}
    assert report["monte_carlo"]["simulation_count"] == MODULE.SIMS


def test_stress_contains_provider_slippage_and_concentration() -> None:
    report = MODULE.stress(_rows())
    assert set(report["provider_cost_multiplier_pnl_usd"]) == {
        "1.25",
        "1.50",
        "2.00",
    }
    assert set(
        report["adverse_slippage_provider_cost_fraction_pnl_usd"]
    ) == {"0.25", "0.50", "1.00"}
    assert "remove_best_1_pnl_usd" in report
    assert "remove_best_2_pnl_usd" in report
    assert "remove_best_3_pnl_usd" in report
    assert "losses_first_drawdown_usd" in report
    assert "winners_first_drawdown_usd" in report


def test_wfo_is_chronological_and_uses_no_test_outcomes_for_selection() -> None:
    report = MODULE.chronological_wfo(_rows(), folds=5)
    assert report["mode"] == "EXPANDING_TRAIN_FIXED_CIBO_CONFIG"
    assert report["selection_uses_test_outcomes"] is False
    assert len(report["tests"]) == 4
    assert all(row["train_n"] > 0 for row in report["tests"])
    assert all(row["test_n"] > 0 for row in report["tests"])
