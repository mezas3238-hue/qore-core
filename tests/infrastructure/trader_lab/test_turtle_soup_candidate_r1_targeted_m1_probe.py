from __future__ import annotations

import json
from pathlib import Path

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1_targeted_m1_probe import (
    _canonical_manifest_digest,
    load_target_sessions,
)

_MARKETS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "GBPJPY", "AUDJPY")


def _manifest(path: Path, *, target: str = "2025-01-02T22:00:00+00:00") -> Path:
    payload: dict[str, object] = {
        "schema": "qore.trader_lab.turtle_soup_candidate_r1.targeted_m1_manifest.v1",
        "research_identity": "turtle-soup-candidate-r1",
        "fresh_oos_embargo_start": "2026-03-01T00:00:00+00:00",
        "source_d1_run_id": 34947549114,
        "source_m15_run_id": 34947548876,
        "source_acquisition_sha": "5a228511d39dabd9686c2d9c14c1a6a4f52ad2b2",
        "selection_reason": "resolve-only-INTRABAR_PATH_AMBIGUOUS; no pnl-based session selection",
        "counts": {"classic": 1, "plus_one": 0},
        "sessions": {
            market: {
                "classic": [target] if market == "EURUSD" else [],
                "plus-one": [],
            }
            for market in _MARKETS
        },
    }
    payload["manifest_digest_sha256"] = _canonical_manifest_digest(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_target_manifest_returns_only_frozen_symbol_sessions(tmp_path: Path) -> None:
    path = _manifest(tmp_path / "manifest.json")
    sessions = load_target_sessions(path, symbol="EURUSD")
    assert len(sessions) == 1
    assert sessions[0].isoformat() == "2025-01-02T22:00:00+00:00"


def test_target_manifest_digest_tampering_fails_closed(tmp_path: Path) -> None:
    path = _manifest(tmp_path / "manifest.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["selection_reason"] = "pnl-selected"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CTraderDemoLabProbeError, match="digest mismatch"):
        load_target_sessions(path, symbol="EURUSD")


def test_target_manifest_cannot_cross_fresh_oos_embargo(tmp_path: Path) -> None:
    path = _manifest(tmp_path / "manifest.json", target="2026-03-01T00:00:00+00:00")
    with pytest.raises(CTraderDemoLabProbeError, match="fresh-OOS embargo"):
        load_target_sessions(path, symbol="EURUSD")


def test_target_manifest_rejects_market_outside_frozen_universe(tmp_path: Path) -> None:
    path = _manifest(tmp_path / "manifest.json")
    with pytest.raises(CTraderDemoLabProbeError, match="frozen R1 universe"):
        load_target_sessions(path, symbol="XAUUSD")
