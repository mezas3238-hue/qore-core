from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_index_c2_positional_r1_forensics import (
    EXPECTED_FREEZE_COMMIT,
    EXPECTED_REPLAY_SCHEMA,
    build_report,
)


def _trade(
    symbol: str,
    signal_at: str,
    anchor: int,
    side: str,
    r_multiple: str,
    exit_reason: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "signal_at": signal_at,
        "anchor_hour_new_york": anchor,
        "side": side,
        "exit_reason": exit_reason,
        "r_multiple": r_multiple,
    }


def _replay(path: Path) -> Path:
    markets = [
        {
            "symbol": "NAS100",
            "trades": [
                _trade(
                    "NAS100",
                    "2025-01-02T07:00:00+00:00",
                    2,
                    "long",
                    "2",
                    "target",
                ),
                _trade(
                    "NAS100",
                    "2025-01-03T11:00:00+00:00",
                    6,
                    "short",
                    "-1",
                    "stop",
                ),
                _trade(
                    "NAS100",
                    "2025-01-04T15:00:00+00:00",
                    10,
                    "short",
                    "1",
                    "h4_containment_exit",
                ),
            ],
        },
        {
            "symbol": "SP500",
            "trades": [
                _trade(
                    "SP500",
                    "2025-02-02T07:00:00+00:00",
                    2,
                    "short",
                    "-1",
                    "stop",
                ),
                _trade(
                    "SP500",
                    "2025-02-03T11:00:00+00:00",
                    6,
                    "long",
                    "2",
                    "target",
                ),
                _trade(
                    "SP500",
                    "2025-02-04T15:00:00+00:00",
                    10,
                    "long",
                    "-1",
                    "stop",
                ),
            ],
        },
        {
            "symbol": "US30",
            "trades": [
                _trade(
                    "US30",
                    "2026-01-02T07:00:00+00:00",
                    2,
                    "long",
                    "-1",
                    "stop",
                ),
                _trade(
                    "US30",
                    "2026-01-03T11:00:00+00:00",
                    6,
                    "short",
                    "2",
                    "target",
                ),
                _trade(
                    "US30",
                    "2026-01-04T15:00:00+00:00",
                    10,
                    "short",
                    "0",
                    "h4_containment_exit",
                ),
            ],
        },
    ]
    payload = {
        "schema": EXPECTED_REPLAY_SCHEMA,
        "research_only": True,
        "consumed_evidence": True,
        "fresh_holdout": False,
        "governance": {
            "pre_economic_freeze_commit": EXPECTED_FREEZE_COMMIT,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
        },
        "markets": markets,
        "aggregate_equal_risk_trade_economics": {
            "sample_size": 9,
            "total_r": "3",
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_forensics_reconciles_and_never_authorizes_subset_selection(
    tmp_path: Path,
) -> None:
    report = build_report(_replay(tmp_path / "r1.json"))

    aggregate = report["aggregate"]
    assert isinstance(aggregate, dict)
    assert aggregate["sample_size"] == 9
    assert aggregate["total_r"] == "3"

    by_market = report["by_market"]
    by_anchor = report["by_anchor_new_york"]
    bootstrap = report["block_bootstrap"]
    assert isinstance(by_market, dict)
    assert isinstance(by_anchor, dict)
    assert isinstance(bootstrap, dict)
    assert set(by_market) == {"NAS100", "SP500", "US30"}
    assert set(by_anchor) == {"02:00", "06:00", "10:00"}
    assert len(bootstrap) == 3

    adjudication = report["diagnostic_adjudication"]
    assert isinstance(adjudication, dict)
    assert adjudication["retrospective_subset_selection_authorized"] is False
    assert adjudication["methodology_change_authorized"] is False
    assert adjudication["fresh_unseen_validation_required_before_promotion"] is True
    assert adjudication["demo_eligible"] is False
    assert adjudication["live_authorized"] is False
    assert adjudication["production_authorized"] is False


def test_forensics_is_deterministic(tmp_path: Path) -> None:
    replay = _replay(tmp_path / "r1.json")
    first = build_report(replay)
    second = build_report(replay)
    assert first["block_bootstrap"] == second["block_bootstrap"]
