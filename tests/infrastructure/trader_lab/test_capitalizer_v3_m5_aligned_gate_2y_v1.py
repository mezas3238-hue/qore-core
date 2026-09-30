import json
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_v3_m5_aligned_gate_2y_v1 import (
    BASELINE_DD_R,
    BASELINE_LOSING_STREAK,
    BASELINE_MAX3_TRADES,
    BASELINE_PF,
    BASELINE_TOTAL_R,
    IDENTITY,
    MATRIX_IDENTITY,
    _load_state_lookup,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    CapitalizerM5DirectionalState,
)


def test_information_experiment_contract_is_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_M5_ALIGNED_GATE_2Y_V1"
    assert MATRIX_IDENTITY == "QORE_CAPITALIZER_NINE_MARKET_V3_M5_ALIGNED_GATE_2Y_V1"
    assert BASELINE_MAX3_TRADES == 474
    assert str(BASELINE_PF) == "1.283270342004661566350801358"
    assert str(BASELINE_TOTAL_R) == "50.34686423146549474995387094"
    assert str(BASELINE_DD_R) == "13.43559872546085473546771142"
    assert BASELINE_LOSING_STREAK == 8


def test_state_lookup_uses_frozen_directional_mapping(tmp_path: Path) -> None:
    path = tmp_path / (
        "capitalizer-eurusd-v3-m3-microstructure-context-2y-v1-rows.jsonl"
    )
    rows = (
        {
            "closeback_at": "2026-09-22T10:05:00+00:00",
            "side": "LONG",
            "microstructure_signature": "LOW_BREAK_ATTEMPT+LOW_RAID_REJECTION",
        },
        {
            "closeback_at": "2026-09-22T10:10:00+00:00",
            "side": "SHORT",
            "microstructure_signature": "HIGH_ACCEPTANCE+HIGH_BREAK_ATTEMPT",
        },
    )
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    lookup = _load_state_lookup(tmp_path)

    assert lookup[
        ("2026-09-22T10:05:00+00:00", "LONG")
    ] is CapitalizerM5DirectionalState.ALIGNED
    assert lookup[
        ("2026-09-22T10:10:00+00:00", "SHORT")
    ] is CapitalizerM5DirectionalState.OPPOSED
