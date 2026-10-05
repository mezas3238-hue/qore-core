from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_script() -> ModuleType:
    path = Path("scripts/vt31_nas100_journey_cross_partition_adjudication_v1.py")
    spec = importlib.util.spec_from_file_location("journey_adjudication", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report(
    *,
    partition: str,
    labeled: int,
    giveback: int,
    runner3: int,
    runner5: int,
    failed: int,
    giveback_close: str,
    runner3_close: str,
    runner5_close: str,
) -> dict[str, object]:
    return {
        "partition": partition,
        "market": "NAS100",
        "summary": {
            "labeled": labeled,
            "journey_classes": {
                "GIVEBACK_AFTER_1R": giveback,
                "RUNNER_3R_PLUS": runner3,
                "EXTENDED_RUNNER_5R_PLUS": runner5,
                "FAILED_BEFORE_1R": failed,
                "PARTIAL_DELIVERY_1R_PLUS": 0,
            },
            "milestone_rates": {
                "1.0": {
                    "rate": "0.60",
                    "median_minutes_from_fill": "1",
                }
            },
            "dol_rates": {
                "1": {
                    "rate": "0.13",
                }
            },
        },
        "milestone_1_0r_classes": {
            "GIVEBACK_AFTER_1R": {
                "favorable_close_rate": {
                    "median": giveback_close,
                },
                "overlap": {"median": "0.75"},
                "efficiency": {"median": "1"},
            },
            "RUNNER_3R_PLUS": {
                "favorable_close_rate": {
                    "median": runner3_close,
                },
                "overlap": {"median": "0.75"},
                "efficiency": {"median": "0.90"},
            },
            "EXTENDED_RUNNER_5R_PLUS": {
                "favorable_close_rate": {
                    "median": runner5_close,
                },
                "overlap": {"median": "0.75"},
                "efficiency": {"median": "0.80"},
            },
        },
    }


def test_cross_partition_adjudication_supports_persistence_not_threshold() -> None:
    module = _load_script()
    reports = {
        "r8_fresh": _report(
            partition="r8_fresh",
            labeled=200,
            giveback=60,
            runner3=20,
            runner5=40,
            failed=80,
            giveback_close="0",
            runner3_close="0.5",
            runner5_close="0.45",
        ),
        "r6": _report(
            partition="r6",
            labeled=250,
            giveback=100,
            runner3=25,
            runner5=45,
            failed=80,
            giveback_close="0",
            runner3_close="0.70",
            runner5_close="0.60",
        ),
        "r5": _report(
            partition="r5",
            labeled=300,
            giveback=100,
            runner3=35,
            runner5=50,
            failed=115,
            giveback_close="0.30",
            runner3_close="0.45",
            runner5_close="0.55",
        ),
    }

    result = module.adjudicate(reports)

    assert result["cross_partition"][
        "giveback_after_1r_present_all_partitions"
    ] is True
    assert result["cross_partition"][
        "runner_5r_plus_present_all_partitions"
    ] is True
    assert result["cross_partition"][
        "favorable_close_persistence_at_1r_supported"
    ] is True
    assert result["cross_partition"][
        "overlap_at_1r_stable_discriminator"
    ] is False
    assert result["cross_partition"][
        "path_efficiency_at_1r_runner_higher_all"
    ] is False
    assert result["threshold_selected"] is False
    assert result["runtime_policy_promoted"] is False
    assert result["opens_new_holdout"] is False
    assert result["candidate_certified"] is False
