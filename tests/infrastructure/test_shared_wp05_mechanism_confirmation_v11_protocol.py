from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_harness(monkeypatch: pytest.MonkeyPatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    module = importlib.import_module("shared_wp05_mechanism_confirmation_v11")
    return importlib.reload(module)


def _range() -> dict[str, int | str]:
    return {
        "episode_count": 6_100,
        "eligible_source_count": 6_150,
        "complete_evidence_count": 6_100,
        "incomplete_evidence_count": 50,
        "checkpoint_incomplete_count": 50,
        "checkpoint_complete_coverage_bps": 9_918,
        "terminal_event_count": 1_500,
        "nonterminal_event_count": 4_600,
        "source_min": "2016-01-01T00:00:00+00:00",
        "source_max": "2017-01-01T00:00:00+00:00",
        "target_max": "2017-01-01T00:30:00+00:00",
        "changed_target_count": 1,
        "target_unidentifiable_anchor_count": 0,
        "v10_unidentifiable_anchor_count": 0,
        "target_contract": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "fresh_holdout_opened": 0,
    }


def test_v11_does_not_read_r6_r5_when_r8_sample_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _load_harness(monkeypatch)
    calls: list[str] = []

    def prepare(*, partition: str, evidence_paths):
        del evidence_paths
        calls.append(partition)
        if partition != "r8":
            raise AssertionError("V11 opened consumed holdout before R8 gate")
        return tuple(), {
            **_range(),
            "episode_count": 0,
            "complete_evidence_count": 0,
            "terminal_event_count": 0,
        }

    monkeypatch.setattr(harness, "_prepare_partition", prepare)
    payload = harness.run(evidence={"r8": {}, "r6": {}, "r5": {}})

    assert calls == ["r8"]
    assert payload["status"] == "WP05_V11_PROTOCOL_FAILED"
    assert payload["fresh_holdout_opened"] is False


def test_v11_does_not_read_r6_r5_without_legal_r8_calibration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _load_harness(monkeypatch)
    calls: list[str] = []
    base = datetime(2017, 1, 1, tzinfo=UTC)
    episode = SimpleNamespace(observed_at=base + timedelta(minutes=30))
    rows = (episode,) * harness.MINIMUM_EPISODES

    def prepare(*, partition: str, evidence_paths):
        del evidence_paths
        calls.append(partition)
        if partition != "r8":
            raise AssertionError("V11 opened consumed holdout before R8 freeze")
        return rows, _range()

    model = SimpleNamespace(calibration_gate_pass=False)

    monkeypatch.setattr(harness, "_prepare_partition", prepare)
    monkeypatch.setattr(
        harness,
        "fit_v11_mechanism_confirmation_model",
        lambda **kwargs: model,
    )
    monkeypatch.setattr(
        harness,
        "_model_payload",
        lambda frozen: {"fingerprint_sha256": "a" * 64},
    )
    monkeypatch.setattr(
        harness,
        "evaluate_v11_mechanism_confirmation",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        harness,
        "_evaluation_payload",
        lambda evaluation: {"partition": "r8"},
    )

    payload = harness.run(evidence={"r8": {}, "r6": {}, "r5": {}})

    assert calls == ["r8"]
    assert payload["status"] == "WP05_V11_MECHANISM_CONFIRMATION_FALSIFIED"
    assert payload["protocol_pass"] is True
    assert payload["development_gate_pass"] is False
    assert payload["reason"] == "NO_LEGAL_R8_CONFIRMATION_CALIBRATION"
    assert payload["fresh_holdout_opened"] is False
