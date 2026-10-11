"""Sensor → cognitive entry authority → PAPER outcome; no fake full brain."""

from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_sensor_paper_decision_ab_v1 import (
    IDENTITY,
    CognitiveEntryVerdict,
    _score,
)


def _verdict() -> CognitiveEntryVerdict:
    return CognitiveEntryVerdict(
        source_opportunity_id="deadbeef",
        symbol="EURUSD", observed_at="2026-07-02T15:09:00+00:00",
        disposition="ACCEPT", why="Confirmed as-of Master Frame with H1/M15/M1",
        cognitive_engine_identity="A1_REAL_COGNITIVE_ENGINE",
        master_frame_artifact_sha256="a" * 64,
        master_frame_evaluated=True, sensor_evidence_evaluated=True,
    )


def test_cognitive_port_requires_real_complete_frame_attestation() -> None:
    assert IDENTITY.endswith("AB_V1")
    v = _verdict()
    assert v.disposition == "ACCEPT"
    for changes in (
        {"master_frame_evaluated": False},
        {"sensor_evidence_evaluated": False},
        {"master_frame_artifact_sha256": ""},
        {"cognitive_engine_identity": ""},
        {"why": ""},
        {"outcome_visible": True},
        {"used_future_h1_expiry": True},
        {"authorization_is_live": True},
    ):
        with pytest.raises(ValueError, match="causal A1 Master Frame"):
            replace(v, **changes)


def test_verdict_must_match_a_timezone_aware_original_decision() -> None:
    with pytest.raises(ValueError, match="timezone"):
        replace(_verdict(), observed_at="2026-07-02T15:09:00")


def test_wait_and_abstain_are_valid_nonexecuted_paper_choices() -> None:
    assert replace(_verdict(), disposition="WAIT").disposition == "WAIT"
    assert replace(_verdict(), disposition="ABSTAIN").disposition == "ABSTAIN"


def test_zero_trades_cannot_fake_a_positive_profit_factor() -> None:
    r = _score(())
    assert r["trades"] == 0
    assert r["profit_factor"] is None
    assert r["max_drawdown_r"] is None
