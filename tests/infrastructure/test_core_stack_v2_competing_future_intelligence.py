from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.competing_future_intelligence import (
    CausalHorizonSnapshot,
    CompetingFutureState,
    assess_competing_futures,
)


def _snap(
    minutes: int,
    *,
    support: int,
    adversity: int,
    det_v: int,
    rec_v: int,
    det_p: int,
    rec_p: int,
    confirm: int,
    fragility: int,
    structural: int,
    trend: int,
    uncertainty: int = 2500,
) -> CausalHorizonSnapshot:
    return CausalHorizonSnapshot(
        horizon_minutes=minutes,
        as_of=datetime(2026, 9, 24, 14, 0, tzinfo=UTC),
        evidence_count=max(5, minutes),
        data_integrity_bps=10_000,
        support_bps=support,
        adversity_bps=adversity,
        deterioration_velocity_bps=det_v,
        recovery_velocity_bps=rec_v,
        deterioration_persistence_bps=det_p,
        recovery_persistence_bps=rec_p,
        cross_market_confirmation_bps=confirm,
        cross_market_fragility_bps=fragility,
        structural_fragility_bps=structural,
        trend_support_bps=trend,
        uncertainty_bps=uncertainty,
    )


def test_competing_futures_identifies_terminal_adversity() -> None:
    snapshots = tuple(
        _snap(
            minutes,
            support=3000,
            adversity=7000,
            det_v=7000,
            rec_v=2000,
            det_p=8000,
            rec_p=2000,
            confirm=2500,
            fragility=7500,
            structural=8000,
            trend=2500,
        )
        for minutes in (5, 15, 30, 60)
    )

    result = assess_competing_futures(snapshots)

    assert result.state is CompetingFutureState.TERMINAL_ADVERSE
    assert result.terminal_horizon_count == 4
    assert result.recovery_horizon_count == 0
    assert result.terminal_evidence_bps > result.recovery_evidence_bps
    assert result.outcome_used is False
    assert result.pnl_used is False
    assert result.sizing_authority is False


def test_competing_futures_separates_fast_adversity_from_broad_recovery() -> None:
    fast = _snap(
        5,
        support=3000,
        adversity=7000,
        det_v=7000,
        rec_v=2000,
        det_p=7000,
        rec_p=2000,
        confirm=3000,
        fragility=7000,
        structural=7500,
        trend=2500,
    )
    broader = tuple(
        _snap(
            minutes,
            support=7000,
            adversity=3000,
            det_v=2000,
            rec_v=7000,
            det_p=2500,
            rec_p=7500,
            confirm=7500,
            fragility=2500,
            structural=3000,
            trend=7500,
        )
        for minutes in (15, 30, 60)
    )

    result = assess_competing_futures((fast, *broader))

    assert result.state is CompetingFutureState.RECOVERABLE_ADVERSE
    assert result.terminal_horizon_count == 1
    assert result.recovery_horizon_count == 3
    assert "FAST_ADVERSITY_PRESENT" in result.reasons
    assert "BROAD_HORIZON_RECOVERY_DOMINANT" in result.reasons


def test_competing_futures_supportive_requires_no_terminal_horizon() -> None:
    snapshots = tuple(
        _snap(
            minutes,
            support=7500,
            adversity=2500,
            det_v=2000,
            rec_v=7500,
            det_p=2000,
            rec_p=8000,
            confirm=8000,
            fragility=2000,
            structural=2500,
            trend=8000,
        )
        for minutes in (5, 15, 30, 60)
    )

    result = assess_competing_futures(snapshots)

    assert result.state is CompetingFutureState.SUPPORTIVE
    assert result.terminal_horizon_count == 0
    assert result.recovery_horizon_count == 4


def test_competing_futures_does_not_force_a_guess_when_paths_conflict() -> None:
    snapshots = (
        _snap(
            5,
            support=3000,
            adversity=7000,
            det_v=7000,
            rec_v=2000,
            det_p=7000,
            rec_p=2000,
            confirm=3000,
            fragility=7000,
            structural=7500,
            trend=2500,
        ),
        _snap(
            15,
            support=7000,
            adversity=3000,
            det_v=2000,
            rec_v=7000,
            det_p=2000,
            rec_p=7000,
            confirm=7500,
            fragility=2500,
            structural=2500,
            trend=7500,
        ),
    )

    result = assess_competing_futures(snapshots)

    assert result.state is CompetingFutureState.CONFLICTED


def test_competing_futures_requires_multi_horizon_evidence() -> None:
    result = assess_competing_futures(
        (
            _snap(
                5,
                support=5000,
                adversity=5000,
                det_v=5000,
                rec_v=5000,
                det_p=5000,
                rec_p=5000,
                confirm=5000,
                fragility=5000,
                structural=5000,
                trend=5000,
            ),
        )
    )
    assert result.state is CompetingFutureState.INSUFFICIENT
