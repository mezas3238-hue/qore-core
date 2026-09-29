from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_continuation_positive_tail_intelligence import (
    SharedPositionCausalObservation,
)
from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatPolicy,
    SharedPositionThreatScope,
    assess_position_threat,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedPositionThreatLevel,
    SharedTraderIntelligenceValidationError,
)

T0 = datetime(2026, 9, 29, 23, 0, tzinfo=UTC)


def _observation(**overrides: object) -> SharedPositionCausalObservation:
    values: dict[str, object] = {
        "observation_id": "threat-observation-001",
        "position_id": "vt31-position-001",
        "asset": "NAS100",
        "as_of": T0,
        "evidence_cutoff_at": T0,
        "minutes_since_fill": 8,
        "progress_bps": 1_000,
        "signed_close_r_bps": -7_000,
        "efficiency_bps": -7_000,
        "overlap_bps": 8_000,
        "signed_body_r_bps": -5_000,
        "peer_confirmation_bps": 2_000,
        "breadth_bps": 2_000,
        "peer_transition_adverse_bps": 8_000,
        "world_support_bps": 2_000,
        "world_fragility_bps": 8_000,
        "data_integrity_bps": 10_000,
        "provenance_refs": ("immutable-source-bars",),
    }
    values.update(overrides)
    return SharedPositionCausalObservation(**values)  # type: ignore[arg-type]


def _policy() -> SharedPositionThreatPolicy:
    return SharedPositionThreatPolicy(
        policy_id="sti8-source-only-v1",
        moderate_threshold_bps=4_000,
        elevated_threshold_bps=5_500,
        high_threshold_bps=7_000,
        critical_threshold_bps=8_500,
        minimum_integrity_bps=9_500,
        source_only_calibration=True,
        evidence_refs=("r8-source-only-threat-distribution",),
    )


def test_threat_engine_detects_source_only_threat_without_exit_authority() -> None:
    assessment = assess_position_threat(_observation(), policy=_policy())

    assert assessment.threat_level in {
        SharedPositionThreatLevel.ELEVATED,
        SharedPositionThreatLevel.HIGH,
        SharedPositionThreatLevel.CRITICAL,
    }
    assert assessment.mandatory_exit is False
    assert assessment.mandatory_protection is False
    assert assessment.position_management_authority is False
    assert assessment.risk_authority is False
    assert assessment.execution_authority is False


def test_cross_asset_break_can_dominate_threat_scope() -> None:
    assessment = assess_position_threat(
        _observation(
            signed_close_r_bps=-1_000,
            efficiency_bps=-500,
            overlap_bps=4_000,
            signed_body_r_bps=-500,
            peer_confirmation_bps=500,
            peer_transition_adverse_bps=9_500,
            world_support_bps=7_000,
            world_fragility_bps=2_500,
        ),
        policy=_policy(),
    )

    assert assessment.threat_scope is SharedPositionThreatScope.CROSS_ASSET_THREAT


def test_bad_data_returns_insufficient_threat() -> None:
    assessment = assess_position_threat(
        _observation(data_integrity_bps=8_000),
        policy=_policy(),
    )

    assert assessment.threat_level is SharedPositionThreatLevel.INSUFFICIENT


def test_healthy_position_has_lower_threat_than_adverse_position() -> None:
    adverse = assess_position_threat(_observation(), policy=_policy())
    healthy = assess_position_threat(
        _observation(
            progress_bps=8_000,
            signed_close_r_bps=8_000,
            efficiency_bps=8_000,
            overlap_bps=2_000,
            signed_body_r_bps=3_000,
            peer_confirmation_bps=9_000,
            breadth_bps=9_000,
            peer_transition_adverse_bps=1_000,
            world_support_bps=9_000,
            world_fragility_bps=1_000,
        ),
        policy=_policy(),
    )

    assert healthy.threat_score_bps < adverse.threat_score_bps


def test_threat_policy_rejects_non_source_only_calibration() -> None:
    with pytest.raises(
        SharedTraderIntelligenceValidationError,
        match="calibration must be source-only",
    ):
        replace(_policy(), source_only_calibration=False)
