from __future__ import annotations

import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dgr_requires_deep_post_mfe_giveback_state() -> None:
    dgr = _load_script(
        "vt31_nas100_deep_giveback_rescue_frontier_v1.py"
    )
    qualifying = {
        "mfe_r": Decimal("1.6"),
        "current_close_r": Decimal("0.20"),
        "close_giveback_r": Decimal("1.30"),
        "path_efficiency": Decimal("0.05"),
    }

    assert dgr._qualifies(
        qualifying,
        maximum_current_close_r=Decimal("0.25"),
    )

    for field, unsafe in (
        ("mfe_r", Decimal("1.49")),
        ("current_close_r", Decimal("0.26")),
        ("close_giveback_r", Decimal("0.99")),
        ("path_efficiency", Decimal("0.11")),
    ):
        state = dict(qualifying)
        state[field] = unsafe
        assert not dgr._qualifies(
            state,
            maximum_current_close_r=Decimal("0.25"),
        )


def test_dgr_confirmed_swing_only_changes_stop_on_next_bar() -> None:
    dgr = _load_script(
        "vt31_nas100_deep_giveback_rescue_frontier_v1.py"
    )
    path = [
        {"high": "101", "low": "99", "close": "100"},
        {"high": "116", "low": "108", "close": "115"},
        {"high": "106", "low": "100", "close": "104"},
        {"high": "104", "low": "101", "close": "102"},
        {"high": "103", "low": "99", "close": "100"},
        {"high": "104", "low": "98", "close": "101"},
    ]

    result = dgr._rescue(
        path,
        side="long",
        entry=Decimal("100"),
        initial_stop=Decimal("90"),
        risk=Decimal("10"),
        boundary=Decimal("150"),
        maximum_current_close_r=Decimal("0.25"),
    )

    assert result["status"] == "terminal"
    assert result["exit_reason"] == "DEEP_GIVEBACK_RESCUE_STOP"
    assert result["exit_index"] == 4
    assert Decimal(result["r_multiple"]) == Decimal("0")
    assert result["armed_count"] == 1


def test_dgr_is_capped_at_one_structural_rescue_move() -> None:
    dgr = _load_script(
        "vt31_nas100_deep_giveback_rescue_frontier_v1.py"
    )
    path = [
        {"high": "101", "low": "99", "close": "100"},
        {"high": "116", "low": "108", "close": "115"},
        {"high": "106", "low": "100", "close": "104"},
        {"high": "104", "low": "101", "close": "102"},
        {"high": "105", "low": "101", "close": "103"},
        {"high": "117", "low": "110", "close": "116"},
        {"high": "108", "low": "101", "close": "104"},
        {"high": "105", "low": "102", "close": "102"},
        {"high": "104", "low": "101.5", "close": "102"},
        {"high": "103", "low": "100.5", "close": "101"},
    ]

    result = dgr._rescue(
        path,
        side="long",
        entry=Decimal("100"),
        initial_stop=Decimal("90"),
        risk=Decimal("10"),
        boundary=Decimal("150"),
        maximum_current_close_r=Decimal("0.25"),
    )

    assert result["status"] == "terminal"
    assert result["armed_count"] == 1


def test_dgr_never_arms_a_non_improving_protective_swing() -> None:
    dgr = _load_script(
        "vt31_nas100_deep_giveback_rescue_frontier_v1.py"
    )
    path = [
        {"high": "101", "low": "99", "close": "100"},
        {"high": "116", "low": "92", "close": "115"},
        {"high": "106", "low": "89", "close": "104"},
        {"high": "104", "low": "91", "close": "102"},
        {"high": "103", "low": "88", "close": "100"},
    ]

    result = dgr._rescue(
        path,
        side="long",
        entry=Decimal("100"),
        initial_stop=Decimal("90"),
        risk=Decimal("10"),
        boundary=Decimal("150"),
        maximum_current_close_r=Decimal("0.25"),
    )

    assert result["armed_count"] == 0
    assert result["exit_reason"] == "INITIAL_STOP"


def _partition_payload(
    partition: str,
    *,
    neighbor_halfyear_degrades: bool = True,
) -> dict[str, object]:
    baseline = {
        "metrics": {
            "sample": 10,
            "profit_factor": "1.20",
            "mean_r": "0.10",
            "max_drawdown_r": "5",
        },
        "halfyear_metrics": {
            "2020H1": {
                "mean_r": "0.10",
                "total_r": "1.0",
            }
        },
    }
    witness = {
        "metrics": {
            "sample": 10,
            "profit_factor": "1.30",
            "mean_r": "0.12",
            "max_drawdown_r": "4.5",
        },
        "halfyear_metrics": {
            "2020H1": {
                "mean_r": "0.12",
                "total_r": "1.2",
            }
        },
        "winner_preservation": {
            "winner_count_preservation": "1",
            "winner_r_preservation": "1",
        },
        "armed_trade_count": 2,
    }
    neighbor = {
        "metrics": {
            "sample": 10,
            "profit_factor": "1.31",
            "mean_r": "0.13",
            "max_drawdown_r": "4.4",
        },
        "halfyear_metrics": {
            "2020H1": {
                "mean_r": (
                    "0.09"
                    if neighbor_halfyear_degrades
                    else "0.13"
                ),
                "total_r": (
                    "0.9"
                    if neighbor_halfyear_degrades
                    else "1.3"
                ),
            }
        },
        "winner_preservation": {
            "winner_count_preservation": "1",
            "winner_r_preservation": "1",
        },
        "armed_trade_count": 3,
    }
    return {
        "schema": (
            "qore.vt31.nas100."
            "deep_giveback_rescue_frontier.v1"
        ),
        "partition": partition,
        "variant_reports": {
            "BASELINE": baseline,
            "DGR_CURRENT_CLOSE_MAX_0_25": witness,
            "DGR_CURRENT_CLOSE_MAX_0_50": neighbor,
            "DGR_CURRENT_CLOSE_MAX_0_75": neighbor,
            "DGR_CURRENT_CLOSE_MAX_1_00": neighbor,
        },
        "governance": {
            "consumed_evidence_only": True,
            "opens_new_holdout": False,
        },
    }


def test_cross_partition_witness_requires_temporal_non_degradation(
    tmp_path: Path,
) -> None:
    adjudicator = _load_script(
        "vt31_nas100_deep_giveback_cross_partition_v1.py"
    )
    paths: list[Path] = []
    for partition in ("r8_fresh", "r6", "r5"):
        path = tmp_path / f"{partition}.json"
        path.write_text(
            json.dumps(_partition_payload(partition)),
            encoding="utf-8",
        )
        paths.append(path)

    result = adjudicator.adjudicate(paths)

    assert result["adjudication"] == (
        "SUPPORTED_CROSS_PARTITION_RESEARCH_WITNESS"
    )
    assert result["research_witness"] == (
        "DGR_CURRENT_CLOSE_MAX_0_25"
    )
    assert result[
        "witness_perfect_winner_preservation_3_of_3"
    ] is True
    assert result["wider_frontier_failure_partitions"][
        "DGR_CURRENT_CLOSE_MAX_0_50"
    ] == ["r8_fresh", "r6", "r5"]


def test_cross_partition_adjudication_rejects_missing_fold(
    tmp_path: Path,
) -> None:
    adjudicator = _load_script(
        "vt31_nas100_deep_giveback_cross_partition_v1.py"
    )
    path = tmp_path / "r8.json"
    path.write_text(
        json.dumps(_partition_payload("r8_fresh")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires exactly"):
        adjudicator.adjudicate([path])
