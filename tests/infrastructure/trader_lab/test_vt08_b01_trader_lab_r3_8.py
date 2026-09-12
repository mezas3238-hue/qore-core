from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_b01_trader_lab_aggregate_r3_8 import (
    run_vt08_b01_trader_lab_aggregate,
)
from qore.infrastructure.trader_lab.vt08_b01_trader_lab_r3_8 import _metrics, _passes


def test_r38_metrics_reuse_first_cohort_economic_screen() -> None:
    passing = _metrics(
        (
            Decimal("0.002"),
            Decimal("0.002"),
            Decimal("-0.001"),
            Decimal("0.002"),
        )
    )
    failing = _metrics(
        (
            Decimal("-0.001"),
            Decimal("-0.001"),
            Decimal("0.001"),
            Decimal("-0.001"),
        )
    )
    assert _passes(passing) is True
    assert _passes(failing) is False


def _report(symbol: str, *, mean: str) -> dict[str, object]:
    return {
        "schema": "qore.trader_lab.vt08_b01_diagnostics.r3.8.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "trader_code": "vt-08",
        "profile": "author-clarified",
        "bundle_id": "B01_SOURCE_FAITHFUL_HISTORICAL_REPLAY_V1",
        "symbol": symbol,
        "account_fingerprint": "a" * 64,
        "software_sha": "b" * 40,
        "methodology_fingerprint": "c" * 64,
        "full_period": {
            "sample_size": 2,
            "mean_return": mean,
            "win_rate": "0.5",
            "population_variance": "0.000001",
            "profit_factor": "1",
            "maximum_drawdown": "0.001",
        },
        "walk_forward": {
            "in_sample_pass": False,
            "oos_pass": False,
            "stress_pass": False,
        },
        "failure_analysis": {"stage": "IN_SAMPLE_OR_ECONOMIC_FAIL"},
        "exit_reason_counts": {"stop": 2, "h4_containment_exit": 0},
        "trade_records": [
            {
                "signal_at": "2026-01-01T00:00:00+00:00",
                "exited_at": "2026-01-01T01:00:00+00:00",
                "side": "long",
                "exit_reason": "stop",
                "return_rate": "-0.001",
            },
            {
                "signal_at": "2026-01-02T00:00:00+00:00",
                "exited_at": "2026-01-02T01:00:00+00:00",
                "side": "short",
                "exit_reason": "target",
                "return_rate": "0.0005",
            },
        ],
        "abstain_reasons": {"bias-unresolved": 1},
        "lifecycle_gate": {"demo_eligible": False},
    }


def test_seven_market_aggregate_fails_closed_and_registers_hypotheses(
    tmp_path: Path,
) -> None:
    symbols = (
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "USDCAD",
        "USDJPY",
    )
    paths: list[Path] = []
    for index, symbol in enumerate(symbols):
        path = tmp_path / f"{symbol}.json"
        path.write_text(
            json.dumps(_report(symbol, mean="0.0001" if index < 2 else "-0.0001")),
            encoding="utf-8",
        )
        paths.append(path)
    payload = run_vt08_b01_trader_lab_aggregate(paths)
    assert payload["market_count"] == 7
    assert payload["market_positive_mean_count"] == 2
    assert payload["market_negative_mean_count"] == 5
    stage = payload["trader_lab_stage_summary"]
    assert isinstance(stage, dict)
    assert stage["demo_eligible"] is False
    assert "instrument_dependency_candidate" in payload["failure_classifications"]
    assert payload["hypothesis_register"]
