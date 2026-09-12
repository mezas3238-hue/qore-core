from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.ctrader_demo_lab_historical_holdout_probe import (
    ACQUISITION_OPENED_AT,
    CONSUMED_BASELINE_BOUNDARY,
    EVALUATION_CLOSED_AT,
    EVALUATION_OPENED_AT,
    EXPECTED_SOURCE_CONTRACT_FINGERPRINT,
    _validate_preregistration,
)
from qore.infrastructure.trader_lab.vt08_b01_fresh_holdout_r3_10 import (
    compile_market_holdout,
)
from qore.infrastructure.traders.vt08_b01_source_contract_r3_9 import (
    source_contract_fingerprint,
)


def _write_parent(path: Path) -> None:
    payload = {
        "schema": "qore.trader_lab.vt08_b01_backtest.r3.8.v1",
        "trader_code": "vt-08",
        "symbol": "EURUSD",
        "software_sha": "a" * 40,
        "methodology_fingerprint": "b" * 64,
        "sample_size": 3,
        "trades": [
            {
                "signal_at": "2022-08-12T05:00:00+00:00",
                "exited_at": "2022-08-12T09:00:00+00:00",
                "side": "LONG",
                "entry": "1.0",
                "stop": "0.9",
                "target": "1.2",
                "exit_price": "1.2",
                "exit_reason": "target",
                "return_rate": "0.2",
            },
            {
                "signal_at": "2023-01-10T10:00:00+00:00",
                "exited_at": "2023-01-10T14:00:00+00:00",
                "side": "LONG",
                "entry": "1.0",
                "stop": "0.9",
                "target": "1.2",
                "exit_price": "1.2",
                "exit_reason": "target",
                "return_rate": "0.2",
            },
            {
                "signal_at": "2024-08-12T00:00:00+00:00",
                "exited_at": "2024-08-12T04:00:00+00:00",
                "side": "SHORT",
                "entry": "1.0",
                "stop": "1.1",
                "target": "0.8",
                "exit_price": "1.1",
                "exit_reason": "stop",
                "return_rate": "-0.1",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_preregistered_window_is_frozen_and_non_overlapping() -> None:
    _validate_preregistration()
    assert (EVALUATION_CLOSED_AT - EVALUATION_OPENED_AT).days == 730
    assert ACQUISITION_OPENED_AT < EVALUATION_OPENED_AT
    assert EVALUATION_CLOSED_AT < CONSUMED_BASELINE_BOUNDARY
    assert source_contract_fingerprint() == EXPECTED_SOURCE_CONTRACT_FINGERPRINT


def test_market_holdout_uses_only_frozen_core_interval(tmp_path: Path) -> None:
    parent = tmp_path / "backtest.json"
    _write_parent(parent)

    payload = compile_market_holdout(parent)

    assert payload["holdout_id"] == "VT08_R3_10_FRESH_HOLDOUT_2022_2024"
    assert payload["no_consumed_baseline_overlap"] is True
    assert payload["c3_included"] is False
    metrics = payload["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["sample_size"] == 1
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 0
    assert metrics["flat_trades"] == 0
