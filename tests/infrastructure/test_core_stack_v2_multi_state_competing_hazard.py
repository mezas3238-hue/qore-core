from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.multi_state_competing_hazard import (
    CompetingHazardDecision,
    CompetingHazardEvidence,
    assess_competing_hazards,
)


NOW = datetime(2026, 9, 25, 14, 30, tzinfo=UTC)


def _e(**overrides: int) -> CompetingHazardEvidence:
    values = {
        "data_integrity_bps": 10_000,
        "stop_hazard_bps": 1_000,
        "terminal_hazard_bps": 1_000,
        "target_hazard_bps": 1_500,
        "recovery_hazard_bps": 1_500,
        "no_event_bps": 5_000,
        "adverse_persistence_bps": 7_000,
        "target_persistence_bps": 7_000,
        "recovery_persistence_bps": 7_000,
        "winner_veto_bps": 1_000,
        "uncertainty_bps": 2_000,
    }
    values.update(overrides)
    return CompetingHazardEvidence(as_of=NOW, **values)


def test_stop_requires_dominance_persistence_and_no_winner_veto() -> None:
    result = assess_competing_hazards(
        _e(
            stop_hazard_bps=3_800,
            terminal_hazard_bps=3_200,
            target_hazard_bps=900,
            recovery_hazard_bps=800,
        )
    )
    assert result.decision is CompetingHazardDecision.STOP_LIKELY


def test_winner_veto_blocks_false_stop_without_creating_target() -> None:
    result = assess_competing_hazards(
        _e(
            stop_hazard_bps=3_800,
            terminal_hazard_bps=3_200,
            target_hazard_bps=900,
            recovery_hazard_bps=800,
            winner_veto_bps=8_500,
        )
    )
    assert result.decision is CompetingHazardDecision.CONTESTED
    assert result.winner_veto_active is True


def test_recovery_is_first_class_state() -> None:
    result = assess_competing_hazards(
        _e(
            stop_hazard_bps=500,
            terminal_hazard_bps=500,
            target_hazard_bps=900,
            recovery_hazard_bps=6_500,
        )
    )
    assert result.decision is CompetingHazardDecision.RECOVERABLE


def test_target_requires_own_evidence_not_veto() -> None:
    result = assess_competing_hazards(
        _e(
            stop_hazard_bps=500,
            terminal_hazard_bps=500,
            target_hazard_bps=6_500,
            recovery_hazard_bps=500,
            winner_veto_bps=9_000,
        )
    )
    assert result.decision is CompetingHazardDecision.TARGET_LIKELY


def test_uncertainty_forces_contested() -> None:
    result = assess_competing_hazards(
        _e(
            stop_hazard_bps=4_000,
            terminal_hazard_bps=3_500,
            target_hazard_bps=500,
            recovery_hazard_bps=500,
            uncertainty_bps=8_500,
        )
    )
    assert result.decision is CompetingHazardDecision.CONTESTED
