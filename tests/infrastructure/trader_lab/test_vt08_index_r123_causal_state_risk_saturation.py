from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r123_causal_state_risk_saturation as r123,
)


def test_r123_source_and_floor_are_pinned() -> None:
    assert r123.SOURCE_R122_RUN_ID == 36055703336
    assert r123.SOURCE_R122_ARTIFACT_ID == 10833130590
    assert r123.SOURCE_R122_ARTIFACT_DIGEST == (
        "sha256:6c8a35c137e791504dc921e8ed76920a"
        "0989a2c627448f820c7c845a052e4c08"
    )
    assert r123.FLOOR == Decimal("0.005")
    assert r123.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }


def test_r123_risk_bundle_reports_floor_saturation() -> None:
    rows = [
        {
            "weight": "0.005",
            "primary_r": "0.010",
            "secondary_r": "0.009",
            "exit_timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "NAS100",
            "trade_id": 1,
        },
        {
            "weight": "0.10",
            "primary_r": "-0.10",
            "secondary_r": "-0.11",
            "exit_timestamp": "2026-01-02T00:00:00+00:00",
            "symbol": "NAS100",
            "trade_id": 2,
        },
    ]
    bundle = r123._risk_bundle(rows)
    assert bundle["sample"] == 2
    assert bundle["floor_count"] == 1
    assert bundle["above_floor_count"] == 1
    assert bundle["floor_fraction"] == "0.5"
    assert bundle["total_effective_risk_r"] == "0.105"
