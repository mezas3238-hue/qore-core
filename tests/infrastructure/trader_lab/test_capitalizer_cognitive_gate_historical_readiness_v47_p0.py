from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_gate_historical_readiness_v47_p0 as p0,
)


def test_p0_never_forces_historical_cognitive_pass() -> None:
    report = p0.build_report()
    assert report["constant_pass_to_strategy_used"] is False
    assert report["quote_fresh_invented"] is False
    assert report["regime_family_invented"] is False
    assert report["knowledge_known_forced"] is False
    assert report["hypothesis_stage_forced"] is False
    assert report["metacognition_forced"] is False


def test_p0_has_no_economic_or_fresh_holdout_authority() -> None:
    report = p0.build_report()
    assert report["strategy_economics_calculated"] is False
    assert report["outcomes_read"] is False
    assert report["fresh_holdout_opened"] is False
    assert report["runtime_policy_candidate"] is False
    assert report["candidate_count"] == 0
    assert report["trader_certified"] is False


def test_p0_v46_can_supply_provenance_and_destination_only() -> None:
    report = p0.build_report()
    by_key = {row["key"]: row for row in report["dependencies"]}
    assert by_key["EVIDENCE_PROVENANCE_COMPLETE"]["blocker"] is False
    assert by_key["DESTINATION_CONTEXT_KNOWN_AVAILABLE"]["blocker"] is False
    assert by_key["PERCEPTION_QUOTE_FRESH"]["blocker"] is True
    assert by_key["REGIME_RESOLUTION_SUPPORTED"]["blocker"] is True


def test_p0_historical_cognitive_replay_remains_fail_closed() -> None:
    report = p0.build_report()
    assert report["historical_cognitive_gate_replay_ready"] is False
    assert report["blocking_dependency_count"] > 0
    assert report["next_phase"] == (
        "COGNITIVE_GATE_HISTORICAL_REPLAY_BLOCKED_DO_NOT_FORCE_PASS"
    )


def test_p0_dependency_keys_are_unique() -> None:
    report = p0.build_report()
    keys = [row["key"] for row in report["dependencies"]]
    assert len(keys) == len(set(keys))
