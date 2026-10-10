"""Fail-closed historical native-M1 source→sensor full-cognition readiness gate."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.capitalizer_a1_historical_full_frame_preflight_v1 import (
    CRITICAL_SENSORS,
    audit_pinned_historical_inputs,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)


def _fixture(tmp_path):
    original = tmp_path / "v49"
    sensor = tmp_path / "sensor"
    at = datetime(2026, 1, 7, 10, 0, tzinfo=UTC)
    for session in CapitalizerSession:
        for symbol in sorted(allowed_markets(session)):
            candidate = V49Opportunity(
                symbol=symbol, session=session.value,
                operating_date="2026-01-07", h1_state_direction="BULLISH",
                h1_state_from=(at - timedelta(hours=1)).isoformat(),
                h1_state_until=(at + timedelta(hours=1)).isoformat(),
                h1_state_basis="V49_SOURCE_H1",
                m15_setup_confirmed_at=(at - timedelta(minutes=15)).isoformat(),
                m15_protected_swing_price="90",
                m1_trigger_confirmed_at=at.isoformat(),
                m1_trigger_family="FVG_RETRACE_CISD",
                decision_reference_price="100",
                structural_target_witness_price="110",
            )
            original_book = original / symbol
            sensor_book = sensor / symbol
            original_book.mkdir(parents=True)
            sensor_book.mkdir(parents=True)
            (original_book / f"capitalizer-{symbol.lower()}-v49-hf-capacity-opportunities.jsonl").write_text(
                json.dumps(asdict(candidate)) + "\n"
            )
            row = {
                "source_opportunity_id": source_opportunity_id(candidate),
                "symbol": symbol,
                "original_entry_at": at.isoformat(),
                "original_trigger_family": "FVG_RETRACE_CISD",
                "original_source_signal_preserved": True,
                "execution_authorized": False,
                "hard_entry_gate_added": False,
                "full_master_frame_attested": False,
                "sensor_source_identity_match": True,
                "sensors": [
                    {
                        "sensor": key,
                        "status": "NOT_AVAILABLE",
                        "observed_at": at.isoformat(),
                    }
                    for key in (*CRITICAL_SENSORS, "H1_BIAS_DECLARED")
                ],
            }
            (sensor_book / "scalper-entry-sensors-rows.jsonl").write_text(
                json.dumps(row) + "\n"
            )
    return original, sensor


def test_pinned_full_frame_prerequisite_audit_preserves_nine_sources(tmp_path) -> None:
    original, sensor = _fixture(tmp_path)
    report = audit_pinned_historical_inputs(
        original_root=original, sensor_root=sensor
    )
    assert report.historical_markets == 9
    assert report.source_opportunities == report.source_sensors_reconciled == 9
    assert report.sensor_source_disagreements == 0
    assert report.nine_market_world_barriers_attested == 0
    assert report.current_status == "BLOCKED_MISSING_NINE_MARKET_CAUSAL_WORLD"
    assert report.measured_cognitive_pf is None
    assert report.measured_cognitive_drawdown_r is None
    assert not report.full_historical_master_frame_replayed
    assert not report.trader_certified


def test_preflight_rejects_missing_ninth_market_and_future_sensor(tmp_path) -> None:
    original, sensor = _fixture(tmp_path)
    (sensor / "XAUUSD" / "scalper-entry-sensors-rows.jsonl").unlink()
    with pytest.raises(ValueError, match="nine source books and nine native"):
        audit_pinned_historical_inputs(original_root=original, sensor_root=sensor)
    original, sensor = _fixture(tmp_path)
    target = sensor / "AUDJPY" / "scalper-entry-sensors-rows.jsonl"
    row = json.loads(target.read_text())
    row["sensors"][0]["observed_at"] = datetime(
        2026, 1, 7, 10, 1, tzinfo=UTC
    ).isoformat()
    target.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="future sensor"):
        audit_pinned_historical_inputs(original_root=original, sensor_root=sensor)


def test_preflight_rejects_foreign_sensor_and_missing_original(tmp_path) -> None:
    original, sensor = _fixture(tmp_path)
    target = sensor / "AUDJPY" / "scalper-entry-sensors-rows.jsonl"
    row = json.loads(target.read_text())
    row["source_opportunity_id"] = "UNRECOGNIZED"
    target.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="no original parent"):
        audit_pinned_historical_inputs(original_root=original, sensor_root=sensor)
