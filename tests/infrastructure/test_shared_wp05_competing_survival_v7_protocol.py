from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_harness(monkeypatch: pytest.MonkeyPatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    module = importlib.import_module("shared_wp05_competing_survival_v7")
    return importlib.reload(module)


def _range() -> dict[str, int | str]:
    return {
        "episode_count": 6_000,
        "complete_evidence_count": 6_000,
        "incomplete_evidence_count": 0,
        "source_min": "2016-01-01T00:00:00+00:00",
        "source_max": "2017-01-01T00:00:00+00:00",
        "target_max": "2017-01-01T00:30:00+00:00",
        "v2_terminal_count": 1_000,
        "changed_target_count": 1,
        "target_unidentifiable_anchor_count": 0,
        "v7_unidentifiable_anchor_count": 0,
        "target_contract": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "fresh_holdout_opened": 0,
    }


def test_v7_does_not_read_r6_r5_when_r8_sample_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _load_harness(monkeypatch)
    calls: list[str] = []

    def prepare(*, partition: str, evidence_paths):
        del evidence_paths
        calls.append(partition)
        if partition != "r8":
            raise AssertionError("consumed partition was opened before legal R8 freeze")
        return tuple(), {
            **_range(),
            "episode_count": 0,
            "complete_evidence_count": 0,
        }

    monkeypatch.setattr(harness, "_prepare_partition", prepare)
    payload = harness.run(evidence={"r8": {}, "r6": {}, "r5": {}})

    assert calls == ["r8"]
    assert payload["status"] == "WP05_V7_PROTOCOL_FAILED"
    assert payload["fresh_holdout_opened"] is False


def test_v7_does_not_read_r6_r5_when_r8_has_no_legal_calibration_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _load_harness(monkeypatch)
    calls: list[str] = []
    base = datetime(2017, 1, 1, tzinfo=UTC)
    source = SimpleNamespace(evidence_complete=True)
    episode = SimpleNamespace(source=source, observed_at=base)
    rows = (episode,) * harness.MINIMUM_EPISODES

    def prepare(*, partition: str, evidence_paths):
        del evidence_paths
        calls.append(partition)
        if partition != "r8":
            raise AssertionError("consumed partition was opened before legal R8 freeze")
        return rows, _range()

    model = SimpleNamespace(
        fit_partition="r8",
        fit_count=4_199,
        fit_terminal_count=1_000,
        calibration_count=1_800,
        calibration_terminal_count=450,
        purged_discovery_count=1,
        discovery_observed_max=base - timedelta(minutes=30),
        calibration_source_min=base,
        terminal_feature_names=("T",),
        recovery_feature_names=("R",),
        terminal_centers_micros=(0,),
        terminal_scales_micros=(1_000_000,),
        terminal_coefficients_micros=(0,),
        terminal_intercept_micros=0,
        recovery_centers_micros=(0,),
        recovery_scales_micros=(1_000_000,),
        recovery_coefficients_micros=(0,),
        recovery_intercept_micros=0,
        terminal_threshold_micros=500_000,
        recovery_threshold_micros=500_000,
        calibration_terminal_preservation_bps=9_700,
        calibration_false_reduction_bps=500,
        calibration_gate_pass=False,
    )

    monkeypatch.setattr(harness, "_prepare_partition", prepare)
    monkeypatch.setattr(
        harness,
        "fit_competing_survival_model",
        lambda **kwargs: model,
    )
    monkeypatch.setattr(
        harness,
        "evaluate_competing_survival",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        harness,
        "_evaluation_payload",
        lambda evaluation: {"partition": "r8"},
    )
    monkeypatch.setattr(
        harness,
        "competing_survival_model_fingerprint",
        lambda frozen: "a" * 64,
    )

    payload = harness.run(evidence={"r8": {}, "r6": {}, "r5": {}})

    assert calls == ["r8"]
    assert payload["status"] == "WP05_V7_COMPETING_SURVIVAL_FALSIFIED"
    assert payload["protocol_pass"] is True
    assert payload["development_gate_pass"] is False
    assert payload["fresh_holdout_opened"] is False
    assert payload["reason"] == "NO_LEGAL_R8_CALIBRATION_THRESHOLD_PAIR"
