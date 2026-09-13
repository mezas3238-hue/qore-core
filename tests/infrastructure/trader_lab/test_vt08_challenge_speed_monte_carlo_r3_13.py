from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_challenge_speed_monte_carlo_r3_13 import (
    BLOCK_DAYS,
    CHALLENGE_HORIZON_DAYS,
    CHALLENGE_POLICIES,
    MAX_SAFE_BREACH_PROBABILITY,
    MAX_SAFE_DRAWDOWN_P99,
    CandidateScore,
    select_policy,
)


def _score(
    name: str,
    *,
    p10: float,
    breach: float,
    drawdown: float,
    safe: bool,
) -> CandidateScore:
    return CandidateScore(
        policy_name=name,
        probability_10pct_within_30d_before_breach=p10,
        probability_8pct_within_30d_before_breach=p10,
        probability_5pct_within_30d_before_breach=p10,
        any_breach_probability=breach,
        drawdown_p99=drawdown,
        ruin_probability=0.0,
        median_terminal_return=0.0,
        median_days_to_10pct_when_achieved=20.0,
        safe_candidate=safe,
    )


def test_challenge_horizon_and_resampling_are_frozen() -> None:
    assert CHALLENGE_HORIZON_DAYS == 30
    assert BLOCK_DAYS == 5
    assert MAX_SAFE_BREACH_PROBABILITY == 0.01
    assert MAX_SAFE_DRAWDOWN_P99 == 0.06


def test_search_surface_is_preregistered_and_increasing() -> None:
    assert len(CHALLENGE_POLICIES) == 8
    bases = [float(policy.a_base_bps) for policy in CHALLENGE_POLICIES]
    assert bases == [25.0, 30.0, 50.0, 75.0, 100.0, 125.0, 150.0, 200.0]
    for policy in CHALLENGE_POLICIES:
        assert policy.upshift_step_bps < policy.downshift_step_bps
        assert policy.a_floor_bps <= policy.a_base_bps <= policy.a_ceiling_bps
        assert policy.gbpjpy_floor_bps <= policy.gbpjpy_base_bps <= policy.gbpjpy_ceiling_bps
        assert policy.internal_daily_guard_bps <= 300
        assert policy.internal_peak_drawdown_guard_bps <= 600


def test_selection_maximizes_p10_only_inside_safe_set() -> None:
    low = CHALLENGE_POLICIES[2]
    winner = CHALLENGE_POLICIES[4]
    unsafe = CHALLENGE_POLICIES[-1]
    selected_policy, selected_score = select_policy(
        [
            (low, _score(low.name, p10=0.10, breach=0.0, drawdown=0.03, safe=True)),
            (winner, _score(winner.name, p10=0.20, breach=0.005, drawdown=0.05, safe=True)),
            (unsafe, _score(unsafe.name, p10=0.90, breach=0.02, drawdown=0.08, safe=False)),
        ]
    )
    assert selected_policy == winner
    assert selected_score is not None
    assert selected_score.probability_10pct_within_30d_before_breach == 0.20


def test_selection_prefers_lower_breach_then_lower_drawdown_on_tie() -> None:
    first = CHALLENGE_POLICIES[3]
    second = CHALLENGE_POLICIES[4]
    selected_policy, _ = select_policy(
        [
            (first, _score(first.name, p10=0.20, breach=0.004, drawdown=0.05, safe=True)),
            (second, _score(second.name, p10=0.20, breach=0.006, drawdown=0.04, safe=True)),
        ]
    )
    assert selected_policy == first


def test_selection_can_fail_closed_when_no_candidate_is_safe() -> None:
    policy = CHALLENGE_POLICIES[-1]
    selected_policy, selected_score = select_policy(
        [(policy, _score(policy.name, p10=0.50, breach=0.02, drawdown=0.08, safe=False))]
    )
    assert selected_policy is None
    assert selected_score is None
