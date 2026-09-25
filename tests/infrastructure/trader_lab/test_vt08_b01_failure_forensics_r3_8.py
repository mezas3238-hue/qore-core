from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_b01_failure_forensics_r3_8 import (
    Vt08B01FailureForensicsError,
    run_vt08_b01_failure_forensics,
)

_SYMBOLS = ("AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD", "USDCAD", "USDJPY")


def _report(symbol: str, *, positive: bool, oos: bool = False) -> dict[str, object]:
    sign = "0.001" if positive else "-0.001"
    return {
        "schema": "qore.trader_lab.vt08_b01_diagnostics.r3.8.v1",
        "research_only": True,
        "read_only": True,
        "trader_code": "vt-08",
        "symbol": symbol,
        "methodology_fingerprint": "a" * 64,
        "full_period": {"mean_return": sign},
        "walk_forward": {"oos_pass": oos, "stress_pass": False},
        "trade_records": [
            {
                "signal_at": "2026-01-06T10:00:00+00:00",
                "exited_at": "2026-01-06T10:30:00+00:00",
                "return_rate": sign,
                "side": "long",
                "exit_reason": "stop" if not positive else "target",
            }
        ],
    }


def _paths(tmp_path: Path) -> list[Path]:
    paths: list[Path] = []
    for index, symbol in enumerate(_SYMBOLS):
        path = tmp_path / f"{symbol}.json"
        path.write_text(
            json.dumps(_report(symbol, positive=index < 2, oos=index == 2)),
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def test_failure_forensics_preserves_holdout_governance(tmp_path: Path) -> None:
    payload = run_vt08_b01_failure_forensics(_paths(tmp_path))
    assert payload["baseline_frozen"] is True
    assert payload["current_evidence_consumed"] is True
    assert payload["independent_validation_reuse_prohibited"] is True
    assert payload["demo_eligible"] is False
    assert payload["stress_pass_markets"] == []
    assert payload["oos_pass_markets"] == ["EURUSD"]
    hypotheses = payload["hypothesis_register"]
    assert isinstance(hypotheses, list)
    assert hypotheses


def test_failure_forensics_requires_exact_seven_markets(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(Vt08B01FailureForensicsError):
        run_vt08_b01_failure_forensics(paths[:-1])
