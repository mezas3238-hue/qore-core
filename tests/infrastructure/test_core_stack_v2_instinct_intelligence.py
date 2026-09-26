from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter_ns

from qore.infrastructure.core_stack_v2 import (
    InstinctSituation,
    MarketEnvironmentAssessment,
    MarketEnvironmentState,
    MarketTrajectoryAssessment,
    MarketTrajectoryState,
    PositionPathAssessment,
    PositionPathState,
    ResidentConvergenceAssessment,
    ResidentConvergenceState,
    SupportMethodology,
    assess_instinct,
    superintelligence_freeze_contract,
)

NOW = datetime(2026, 9, 24, 19, 30, tzinfo=UTC)


def _environment(
    *,
    state: MarketEnvironmentState,
    support: int,
    adverse: int,
    velocity: int,
    persistence: int,
    recovery: int = 1000,
) -> MarketEnvironmentAssessment:
    return MarketEnvironmentAssessment(
        as_of=NOW,
        state=state,
        evidence_count=8,
        market_support_bps=support,
        adverse_environment_bps=adverse,
        adverse_velocity_bps=velocity,
        recovery_velocity_bps=recovery,
        adverse_persistence_bps=persistence,
        recovery_persistence_bps=2000,
        cross_market_fragility_bps=adverse,
        structural_fragility_bps=adverse,
        reasons=("TEST",),
    )


def _trajectory(
    *,
    state: MarketTrajectoryState,
    support: int,
    adverse: int,
    pressure: int,
    velocity: int,
    persistence: int,
    recovery: int = 1000,
) -> MarketTrajectoryAssessment:
    return MarketTrajectoryAssessment(
        as_of=NOW,
        state=state,
        evidence_count=8,
        support_bps=support,
        adversity_bps=adverse,
        deterioration_pressure_bps=pressure,
        deterioration_velocity_bps=velocity,
        recovery_velocity_bps=recovery,
        deterioration_persistence_bps=persistence,
        recovery_persistence_bps=2000,
        reasons=("TEST",),
    )


def _path(
    *,
    state: PositionPathState,
    winner: int,
    failure: int,
) -> PositionPathAssessment:
    return PositionPathAssessment(
        as_of=NOW,
        state=state,
        evidence_count=6,
        path_support_bps=7000 if winner >= failure else 3000,
        adverse_dominance_bps=failure,
        adverse_persistence_bps=7000 if failure >= 7000 else 2500,
        recovery_persistence_bps=2500,
        winner_protection_bps=winner,
        terminal_failure_risk_bps=failure,
        reasons=("TEST",),
    )


def test_instinct_selects_immediate_defense_on_converged_terminal_failure() -> None:
    result = assess_instinct(
        _environment(
            state=MarketEnvironmentState.DEFENSIVE,
            support=1800,
            adverse=8600,
            velocity=8200,
            persistence=8500,
        ),
        _trajectory(
            state=MarketTrajectoryState.FAILURE,
            support=1600,
            adverse=8800,
            pressure=8700,
            velocity=8400,
            persistence=9000,
        ),
        path=_path(
            state=PositionPathState.FAILURE_RISK,
            winner=1800,
            failure=9000,
        ),
        opportunity_quality_bps=2500,
        expansion_capacity_bps=1500,
    )

    assert result.situation is InstinctSituation.TERMINAL_FAILURE_RISK
    assert result.support_methodology is SupportMethodology.IMMEDIATE_DEFENSE
    assert result.threat_bps >= 8000
    assert result.urgency_bps >= 8000
    assert result.complexity == "O(1)"
    assert result.history_scan_used is False
    assert result.io_used is False
    assert result.pnl_used is False
    assert result.order_authority is False
    assert result.risk_authority is False
    assert result.execution_authority is False



def test_instinct_severe_preentry_deterioration_is_never_passive() -> None:
    result = assess_instinct(
        _environment(
            state=MarketEnvironmentState.FRAGILE,
            support=4700,
            adverse=5600,
            velocity=5200,
            persistence=6500,
        ),
        _trajectory(
            state=MarketTrajectoryState.DETERIORATING,
            support=4300,
            adverse=6600,
            pressure=6500,
            velocity=6100,
            persistence=7000,
        ),
        opportunity_quality_bps=4800,
        expansion_capacity_bps=4200,
    )

    assert result.situation in {
        InstinctSituation.RAPID_DETERIORATION,
        InstinctSituation.TERMINAL_FAILURE_RISK,
    }
    assert result.support_methodology in {
        SupportMethodology.PROGRESSIVE_DEFENSE,
        SupportMethodology.IMMEDIATE_DEFENSE,
    }
    assert result.structural_risk_bps > 0
    assert result.threat_convergence_bps > 0


def test_instinct_preentry_terminal_failure_does_not_require_position_path() -> None:
    result = assess_instinct(
        _environment(
            state=MarketEnvironmentState.DEFENSIVE,
            support=1600,
            adverse=8800,
            velocity=8500,
            persistence=9000,
        ),
        _trajectory(
            state=MarketTrajectoryState.FAILURE,
            support=1400,
            adverse=9000,
            pressure=9000,
            velocity=8800,
            persistence=9000,
        ),
        opportunity_quality_bps=2000,
        expansion_capacity_bps=1200,
    )

    assert result.situation is InstinctSituation.TERMINAL_FAILURE_RISK
    assert result.support_methodology is SupportMethodology.IMMEDIATE_DEFENSE
    assert result.threat_bps >= 8500


def test_instinct_protects_established_winner_before_defense_logic() -> None:
    result = assess_instinct(
        _environment(
            state=MarketEnvironmentState.DEGRADING,
            support=5200,
            adverse=6100,
            velocity=5900,
            persistence=6500,
        ),
        _trajectory(
            state=MarketTrajectoryState.DETERIORATING,
            support=4800,
            adverse=6200,
            pressure=6100,
            velocity=6000,
            persistence=6500,
        ),
        path=_path(
            state=PositionPathState.HEALTHY_PULLBACK,
            winner=8200,
            failure=4300,
        ),
        opportunity_quality_bps=7000,
        expansion_capacity_bps=6500,
    )

    assert result.situation is InstinctSituation.HEALTHY_CONTINUATION
    assert result.support_methodology is SupportMethodology.WINNER_PROTECTION
    assert "FALSE_DEFENSE_MUST_BE_AVOIDED" in result.reasons


def test_instinct_selects_extension_only_with_strong_support_and_capacity() -> None:
    result = assess_instinct(
        _environment(
            state=MarketEnvironmentState.SUPPORTIVE,
            support=8500,
            adverse=1800,
            velocity=800,
            persistence=1000,
        ),
        _trajectory(
            state=MarketTrajectoryState.HEALTHY,
            support=8400,
            adverse=1800,
            pressure=1900,
            velocity=500,
            persistence=1000,
        ),
        opportunity_quality_bps=8500,
        expansion_capacity_bps=8800,
    )

    assert result.situation is InstinctSituation.SUPPORTIVE_EXPANSION
    assert result.support_methodology is SupportMethodology.EXTENSION_SUPPORT


def test_instinct_freeze_requires_resident_constant_time_hot_path() -> None:
    contract = superintelligence_freeze_contract()
    essential = contract["shared_essential_intelligence"]
    instinct = essential["ultrafast_instinct_hot_path"]

    assert instinct["resident_state_inputs_only"] is True
    assert instinct["constant_time_fusion_required"] is True
    assert instinct["complexity_contract"] == "O(1)"
    assert instinct["history_scan_in_hot_path_forbidden"] is True
    assert instinct["network_io_in_hot_path_forbidden"] is True
    assert instinct["runtime_pnl_input_forbidden"] is True
    assert instinct["performance_engineering"]["full_rebuild_per_trade_forbidden"] is True


def test_instinct_microbenchmark_is_submillisecond_p95_on_ci() -> None:
    environment = _environment(
        state=MarketEnvironmentState.DEGRADING,
        support=4200,
        adverse=6300,
        velocity=6500,
        persistence=7000,
    )
    trajectory = _trajectory(
        state=MarketTrajectoryState.DETERIORATING,
        support=3900,
        adverse=6500,
        pressure=6500,
        velocity=6800,
        persistence=7000,
    )

    timings: list[int] = []
    for _ in range(5_000):
        start = perf_counter_ns()
        assess_instinct(
            environment,
            trajectory,
            opportunity_quality_bps=4500,
            expansion_capacity_bps=3500,
        )
        timings.append(perf_counter_ns() - start)

    timings.sort()
    p95_ns = timings[int(len(timings) * 0.95)]
    assert p95_ns < 1_000_000


def test_instinct_uses_resident_terminal_convergence_before_path_matures() -> None:
    path = PositionPathAssessment(
        as_of=NOW,
        state=PositionPathState.INSUFFICIENT,
        evidence_count=1,
        path_support_bps=3000,
        adverse_dominance_bps=6500,
        adverse_persistence_bps=0,
        recovery_persistence_bps=0,
        winner_protection_bps=1500,
        terminal_failure_risk_bps=7000,
        reasons=("PATH_EVIDENCE_INSUFFICIENT",),
    )
    convergence = ResidentConvergenceAssessment(
        as_of=NOW,
        state=ResidentConvergenceState.TERMINAL_FAILURE,
        active_head_count=6,
        terminal_vote_count=5,
        recovery_vote_count=1,
        support_vote_count=0,
        terminal_risk_bps=7800,
        recovery_strength_bps=2600,
        support_strength_bps=2400,
        head_agreement_bps=8333,
        reasons=("TEST",),
    )

    result = assess_instinct(
        _environment(
            state=MarketEnvironmentState.DEGRADING,
            support=3500,
            adverse=6500,
            velocity=6200,
            persistence=6500,
        ),
        _trajectory(
            state=MarketTrajectoryState.DETERIORATING,
            support=3300,
            adverse=6700,
            pressure=6600,
            velocity=6400,
            persistence=6600,
        ),
        path=path,
        convergence=convergence,
        opportunity_quality_bps=3000,
        expansion_capacity_bps=2500,
    )

    assert result.situation is InstinctSituation.TERMINAL_FAILURE_RISK
    assert result.support_methodology is SupportMethodology.IMMEDIATE_DEFENSE
    assert "FAST_DEFENSE_WITHOUT_WAITING_FOR_SLOW_PATH" in result.reasons


def test_instinct_recovery_convergence_blocks_false_defense() -> None:
    convergence = ResidentConvergenceAssessment(
        as_of=NOW,
        state=ResidentConvergenceState.RECOVERABLE_ADVERSITY,
        active_head_count=6,
        terminal_vote_count=1,
        recovery_vote_count=4,
        support_vote_count=3,
        terminal_risk_bps=4200,
        recovery_strength_bps=7200,
        support_strength_bps=6800,
        head_agreement_bps=6666,
        reasons=("TEST",),
    )

    result = assess_instinct(
        _environment(
            state=MarketEnvironmentState.FRAGILE,
            support=5200,
            adverse=5600,
            velocity=5200,
            persistence=5600,
            recovery=6500,
        ),
        _trajectory(
            state=MarketTrajectoryState.WEAKENING,
            support=5000,
            adverse=5600,
            pressure=5600,
            velocity=5200,
            persistence=5600,
            recovery=6500,
        ),
        convergence=convergence,
        opportunity_quality_bps=6000,
        expansion_capacity_bps=6000,
    )

    assert result.situation is InstinctSituation.RECOVERY_BUILDING
    assert result.support_methodology is SupportMethodology.RECOVERY_SUPPORT
    assert "FALSE_DEFENSE_BLOCKED_BY_RECOVERY_EVIDENCE" in result.reasons
