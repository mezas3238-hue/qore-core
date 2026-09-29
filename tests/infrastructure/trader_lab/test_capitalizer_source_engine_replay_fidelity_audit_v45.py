from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_source_engine_replay_fidelity_audit_v45 as v45,
)


def test_v45_is_static_governance_only() -> None:
    report = v45.build_report()
    assert report["economics_opened"] is False
    assert report["admission_changed"] is False
    assert report["target_changed"] is False
    assert report["stop_changed"] is False
    assert report["sizing_changed"] is False
    assert report["protection_changed"] is False
    assert report["fresh_holdout_opened"] is False
    assert report["runtime_policy_candidate"] is False
    assert report["candidate_count"] == 0
    assert report["trader_certified"] is False


def test_v45_canonical_contract_requires_dual_gate_and_structural_target() -> None:
    report = v45.build_report()
    assert report["canonical_dual_gate_bound"] is True
    assert report["canonical_structural_target"] is True
    assert report["canonical_fixed_r_forbidden"] is True


def test_v45_current_replay_target_contract_is_fixed_2r() -> None:
    report = v45.build_report()
    assert report["replay_target_r"] == "2.00"
    assert "FIXED_2R" in report["replay_target_identity"]


def test_v45_detects_at_least_one_hard_fidelity_gap() -> None:
    report = v45.build_report()
    assert report["hard_mismatch_count"] > 0
    assert report["next_phase"] == (
        "SOURCE_FIDELITY_GAP_CONFIRMED_BUILD_NATIVE_SOURCE_FAITHFUL_REPLAY_V46"
    )


def test_v45_check_keys_are_unique() -> None:
    report = v45.build_report()
    keys = [row["key"] for row in report["checks"]]
    assert len(keys) == len(set(keys))
