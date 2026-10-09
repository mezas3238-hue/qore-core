"""Trader Lab P0 universal receipt gate: diagnostic tests, NOT financial certification."""
from __future__ import annotations

from copy import deepcopy

from scripts.cibo_p0_universal_3368_evidence_gate import (
    EXPECTED_SIGNALS, MOTORS, audit_universal_3368,
)

DIGEST = "sha256:" + "a" * 64
NOW = "2020-06-01T12:00:00+00:00"


def _fixture():
    manifest = {"opportunities": []}
    report = {"signal_decisions": []}
    for i in range(EXPECTED_SIGNALS):
        sid = f"signal-{i:04d}"
        manifest["opportunities"].append({"signal_fingerprint": sid})
        report["signal_decisions"].append({
            "signal_fingerprint": sid,
            "qdle_at": NOW,
            "cibo_native_episode": {
                "episode_digest": DIGEST, "observed_up_to": NOW,
            },
            "cibo_management_decision": {
                "decision_digest": DIGEST, "decided_at": NOW,
                "desired_risk_fraction": "0.05",
                "management_intent": "evaluate entry and manage stop",
            },
            "four_motor_receipts": {
                producer: {
                    "producer": producer, "request_id": sid,
                    "source_event_sha256": DIGEST,
                    "observed_at": NOW, "account_sequence": i + 1,
                } for producer in MOTORS
            },
            "qdle_physical_assessment": {
                "request_id": sid, "state": "UNFUNDABLE",
                "lots": "0", "account_sequence": i + 1,
                "binding_limits": ["BROKER_MIN_GRID"],
            },
            "execution_outcome": {
                "request_id": sid, "paper_status": "PAPER_UNFUNDABLE",
            },
        })
    return manifest, report


def test_complete_receipt_envelopes_pass_shape_only_not_certification():
    manifest, report = _fixture()
    status = audit_universal_3368(manifest, report)
    assert status["status"] == "PASS_EVIDENCE_SHAPE_ONLY"
    assert status["source_signals"] == EXPECTED_SIGNALS
    assert status["defect_counts"] == {}
    assert status["certifies_native_cognition"] is False
    assert status["certifies_broker_physics_or_profitability"] is False


def test_current_replay_rows_do_not_masquerade_as_fresh_cognition():
    manifest, report = _fixture()
    report["signal_decisions"] = [{
        "signal_fingerprint": s["signal_fingerprint"],
        "qdle_at": NOW,
        "mode": "BANK",
        "qdle_lots": "0",
        "status": "QDLE_NO_FINANCEABLE_LOT",
    } for s in manifest["opportunities"]]
    status = audit_universal_3368(manifest, report)
    assert status["status"] == "FAIL"
    for stage in ("cibo_episode", "cibo_management_decision",
                  "four_fresh_motor_votes", "qdle_physical_assessment",
                  "execution_outcome"):
        assert status["defect_counts"][stage] == EXPECTED_SIGNALS


def test_20_pre_qdle_geometry_drops_are_visible_as_missing_evidence():
    manifest, report = _fixture()
    for row in report["signal_decisions"][:20]:
        row["status"] = "INVALID_GEOMETRY"
        row.pop("qdle_physical_assessment")
    status = audit_universal_3368(manifest, report)
    assert status["status"] == "FAIL"
    assert status["defect_counts"]["qdle_physical_assessment"] == 20


def test_duplicate_and_missing_signal_ids_rejected():
    manifest, report = _fixture()
    report["signal_decisions"][-1]["signal_fingerprint"] = "signal-0000"
    status = audit_universal_3368(manifest, report)
    assert status["status"] == "FAIL"
    assert "replay_cardinality" in status["defect_counts"]
    assert "source_identity" in status["defect_counts"]


def test_zero_qdle_lot_cannot_claim_paper_fill():
    manifest, report = _fixture()
    row = report["signal_decisions"][0]
    row["execution_outcome"]["paper_status"] = "PAPER_FILLED"
    status = audit_universal_3368(manifest, report)
    assert status["status"] == "FAIL"
    assert status["defect_counts"]["paper_fill_without_qdle_lot"] == 1


def test_cognitive_or_motor_evidence_from_future_is_rejected():
    manifest, report = _fixture()
    report["signal_decisions"][0]["cibo_native_episode"]["observed_up_to"] = (
        "2020-06-01T12:05:00+00:00")
    report["signal_decisions"][1]["four_motor_receipts"]["SIZING"]["observed_at"] = (
        "2020-06-01T12:05:00+00:00")
    status = audit_universal_3368(manifest, report)
    assert status["status"] == "FAIL"
    assert status["defect_counts"]["cibo_episode"] == 1
    assert status["defect_counts"]["four_fresh_motor_votes"] == 1


def test_no_fake_valid_report_with_fraction_over_five_pct():
    manifest, report = _fixture()
    report["signal_decisions"][0]["cibo_management_decision"][
        "desired_risk_fraction"] = "0.05001"
    status = audit_universal_3368(manifest, report)
    assert status["status"] == "FAIL"
    assert status["defect_counts"]["cibo_management_decision"] == 1
