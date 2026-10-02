from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_harness(monkeypatch: pytest.MonkeyPatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    module = importlib.import_module("shared_wp05_sequential_changepoint_v10")
    return importlib.reload(module)


def _range() -> dict[str, int | str]:
    return {
        "episode_count": 6_000,
        "eligible_source_count": 6_100,
        "complete_evidence_count": 6_000,
        "incomplete_evidence_count": 100,
        "checkpoint_incomplete_count": 100,
        "checkpoint_complete_coverage_bps": 9_836,
        "terminal_event_count": 1_000,
        "nonterminal_event_count": 5_000,
        "source_min": "2016-01-01T00:00:00+00:00",
        "source_max": "2017-01-01T00:00:00+00:00",
        "target_max": "2017-01-01T00:30:00+00:00",
        "changed_target_count": 1,
        "target_unidentifiable_anchor_count": 0,
        "v10_unidentifiable_anchor_count": 0,
        "target_contract": "HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2",
        "fresh_holdout_opened": 0,
    }


def test_v10_asof_index_is_causal_and_handles_missing_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _load_harness(monkeypatch)
    keys = (
        "2020-01-01T10:00:00",
        "2020-01-01T10:01:00",
        "2020-01-01T10:03:00",
        "2020-01-01T10:05:00",
    )

    assert harness._asof_index(
        closed_keys=keys,
        target_key="2020-01-01T10:02:00",
        source_index=0,
        require_new_observation=True,
    ) == 1
    assert harness._asof_index(
        closed_keys=keys,
        target_key="2020-01-01T10:04:00",
        source_index=0,
        require_new_observation=True,
    ) == 2
    assert harness._asof_index(
        closed_keys=keys,
        target_key="2020-01-01T10:00:00",
        source_index=0,
        require_new_observation=True,
    ) is None
    assert harness._asof_index(
        closed_keys=keys,
        target_key="2020-01-01T10:00:00",
        source_index=0,
        require_new_observation=False,
    ) == 0


def test_v10_does_not_read_r6_r5_when_r8_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _load_harness(monkeypatch)
    calls: list[str] = []

    def prepare(*, partition: str, evidence_paths):
        del evidence_paths
        calls.append(partition)
        if partition != "r8":
            raise AssertionError("V10 opened consumed partition before legal R8 freeze")
        return tuple(), {
            **_range(),
            "episode_count": 0,
            "complete_evidence_count": 0,
            "terminal_event_count": 0,
        }

    monkeypatch.setattr(harness, "_prepare_partition", prepare)
    payload = harness.run(evidence={"r8": {}, "r6": {}, "r5": {}})

    assert calls == ["r8"]
    assert payload["status"] == "WP05_V10_PROTOCOL_FAILED"
    assert payload["fresh_holdout_opened"] is False


def test_v10_does_not_read_r6_r5_without_legal_r8_calibration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _load_harness(monkeypatch)
    calls: list[str] = []
    base = datetime(2017, 1, 1, tzinfo=UTC)
    point = SimpleNamespace(as_of=base, evidence_complete=True)
    episode = SimpleNamespace(
        checkpoints=(point,),
        observed_at=base + timedelta(minutes=30),
    )
    rows = (episode,) * harness.MINIMUM_EPISODES

    def prepare(*, partition: str, evidence_paths):
        del evidence_paths
        calls.append(partition)
        if partition != "r8":
            raise AssertionError("V10 opened consumed partition before legal R8 freeze")
        return rows, _range()

    model = SimpleNamespace(
        fit_partition="r8",
        feature_names=("F",),
        checkpoints_minutes=(0, 3, 5, 10, 15),
        source_only_threshold_micros=0,
        sequential_threshold_micros=0,
        calibration_source_terminal_preservation_bps=9_800,
        calibration_source_false_reduction_bps=0,
        calibration_sequential_terminal_preservation_bps=9_700,
        calibration_sequential_false_reduction_bps=1_000,
        calibration_gate_pass=False,
        fit_count=4_000,
        fit_terminal_count=1_000,
        fit_nonterminal_count=3_000,
        calibration_count=2_000,
        calibration_terminal_count=500,
        calibration_nonterminal_count=1_500,
        purged_discovery_count=0,
        discovery_observed_max=base - timedelta(minutes=30),
        calibration_source_min=base,
        densities=tuple(),
        target_used_for_training_only=True,
        runtime_future_market_used=False,
        outcome_used_at_runtime=False,
        trader_identity_used=False,
        symbol_identity_used=False,
        setup_identity_used=False,
        pnl_used_at_runtime=False,
        methodology_authority=False,
        knowledge_promotion_authority=False,
        sizing_authority=False,
        risk_authority=False,
        order_authority=False,
        execution_authority=False,
    )

    monkeypatch.setattr(harness, "_prepare_partition", prepare)
    monkeypatch.setattr(
        harness,
        "fit_sequential_changepoint_model",
        lambda **kwargs: model,
    )
    monkeypatch.setattr(
        harness,
        "evaluate_sequential_changepoint",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        harness,
        "_evaluation_payload",
        lambda evaluation: {"partition": "r8"},
    )
    monkeypatch.setattr(
        harness,
        "sequential_changepoint_model_fingerprint",
        lambda frozen: "a" * 64,
    )
    monkeypatch.setattr(
        harness,
        "sequential_changepoint_representation_fingerprint",
        lambda: "b" * 64,
    )

    payload = harness.run(evidence={"r8": {}, "r6": {}, "r5": {}})

    assert calls == ["r8"]
    assert payload["status"] == "WP05_V10_CAUSAL_SEQUENTIAL_FALSIFIED"
    assert payload["protocol_pass"] is True
    assert payload["development_gate_pass"] is False
    assert payload["fresh_holdout_opened"] is False
    assert payload["reason"] == "NO_LEGAL_R8_SEQUENTIAL_CALIBRATION"
