from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.causal_action_readiness import (
    ActionReadinessDisposition,
    CausalActionReadinessEvidence,
    CausalActionReadinessPolicy,
    assess_causal_action_readiness,
)


def _evidence(
    *,
    adverse_h1: int,
    adverse_h3: int,
    favorable_h1: int,
    favorable_h3: int,
    margin: int,
    velocity: int,
) -> CausalActionReadinessEvidence:
    return CausalActionReadinessEvidence(
        as_of=datetime(2026, 9, 26, 2, 15, tzinfo=UTC),
        adverse_h1_bps=adverse_h1,
        adverse_h3_bps=adverse_h3,
        favorable_h1_bps=favorable_h1,
        favorable_h3_bps=favorable_h3,
        near_directional_margin_bps=margin,
        adverse_velocity_bps=velocity,
    )


def test_adverse_evidence_can_remain_watch_without_action_readiness() -> None:
    result = assess_causal_action_readiness(
        _evidence(
            adverse_h1=1_100,
            adverse_h3=3_000,
            favorable_h1=200,
            favorable_h3=500,
            margin=900,
            velocity=-300,
        )
    )

    assert result.disposition is ActionReadinessDisposition.WATCH
    assert result.execution_authority is False
    assert result.risk_authority is False
    assert result.stop_authority is False


def test_near_term_front_loaded_adversity_emits_exit_risk_warning() -> None:
    result = assess_causal_action_readiness(
        _evidence(
            adverse_h1=3_000,
            adverse_h3=4_000,
            favorable_h1=300,
            favorable_h3=600,
            margin=2_700,
            velocity=250,
        )
    )

    assert result.disposition is ActionReadinessDisposition.EXIT_RISK_WARNING
    assert result.imminence_ratio_bps == 7_500
    assert "ADVERSE_TIMING_CONFIRMED" in result.reasons


def test_favorable_near_term_direction_emits_recovery() -> None:
    result = assess_causal_action_readiness(
        _evidence(
            adverse_h1=500,
            adverse_h3=1_000,
            favorable_h1=2_500,
            favorable_h3=3_000,
            margin=-2_000,
            velocity=-200,
        )
    )

    assert result.disposition is ActionReadinessDisposition.RECOVERY


def test_policy_thresholds_are_ordered() -> None:
    try:
        CausalActionReadinessPolicy(
            watch_adverse_h1_bps=2_000,
            defend_adverse_h1_bps=1_000,
            exit_adverse_h1_bps=3_000,
        )
    except ValueError:
        return
    raise AssertionError("unordered readiness thresholds must fail closed")
