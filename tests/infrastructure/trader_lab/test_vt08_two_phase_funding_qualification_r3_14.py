from __future__ import annotations

from dataclasses import replace

from qore.infrastructure.trader_lab.vt08_official_adaptive_monte_carlo_r3_12 import (
    PRIMARY_POLICY,
)
from qore.infrastructure.trader_lab.vt08_two_phase_funding_qualification_r3_14 import (
    PHASE1_POLICIES,
    PHASE2_POLICIES,
    RiskPairScore,
    phase_completion_day,
    select_risk_pair,
)


def _score(
    *,
    p60: float,
    breach: float = 0.0,
    dd99: float = 0.05,
    safe: bool = True,
    median_days: float = 40.0,
) -> RiskPairScore:
    return RiskPairScore(
        phase1_policy_name=PHASE1_POLICIES[0].name,
        phase2_policy_name=PHASE2_POLICIES[0].name,
        probability_phase1_pass_within_60d=0.50,
        probability_phase2_pass_given_phase1=0.50,
        probability_two_phase_complete_within_30d=0.01,
        probability_two_phase_complete_within_45d=0.05,
        probability_two_phase_complete_within_60d=p60,
        phase1_breach_probability=breach,
        phase2_breach_probability_given_phase1=breach,
        combined_breach_probability=breach,
        challenge_drawdown_p95=0.04,
        challenge_drawdown_p99=dd99,
        ruin_probability=0.0,
        median_phase1_completion_days=25.0,
        median_phase2_completion_days=12.0,
        median_total_completion_days=median_days,
        p95_total_completion_days=58.0,
        expected_attempts_per_two_phase_completion=(None if p60 == 0 else 1.0 / p60),
        safe_candidate=safe,
    )


def test_phase_completion_enforces_minimum_trading_days() -> None:
    assert (
        phase_completion_day(
            target_day=2,
            first_breach_day=None,
            minimum_trading_days=4,
            available_days=60,
        )
        == 4
    )


def test_phase_completion_fails_if_breach_occurs_before_minimum_day_completion() -> None:
    assert (
        phase_completion_day(
            target_day=2,
            first_breach_day=3,
            minimum_trading_days=4,
            available_days=60,
        )
        is None
    )


def test_phase_completion_fails_closed_when_deadline_is_exhausted() -> None:
    assert (
        phase_completion_day(
            target_day=58,
            first_breach_day=None,
            minimum_trading_days=5,
            available_days=57,
        )
        is None
    )


def test_pre_registered_surface_is_16_pairs_and_phase2_never_exceeds_phase1() -> None:
    assert len(PHASE1_POLICIES) == 4
    assert len(PHASE2_POLICIES) == 4
    assert len(PHASE1_POLICIES) * len(PHASE2_POLICIES) == 16
    for phase1 in PHASE1_POLICIES:
        for phase2 in PHASE2_POLICIES:
            assert phase2.a_base_bps <= phase1.a_base_bps
            assert phase1.upshift_step_bps < phase1.downshift_step_bps
            assert phase2.upshift_step_bps < phase2.downshift_step_bps


def test_funded_mode_is_materially_lower_risk_than_challenge_surface() -> None:
    assert PRIMARY_POLICY.a_base_bps < min(policy.a_base_bps for policy in PHASE2_POLICIES)
    assert PRIMARY_POLICY.gbpjpy_base_bps < min(
        policy.gbpjpy_base_bps for policy in PHASE2_POLICIES
    )


def test_selection_maximizes_two_phase_completion_among_safe_pairs() -> None:
    first = _score(p60=0.20)
    second = replace(
        _score(p60=0.30),
        phase1_policy_name=PHASE1_POLICIES[1].name,
        phase2_policy_name=PHASE2_POLICIES[1].name,
    )
    p1, p2, score = select_risk_pair(
        (
            (PHASE1_POLICIES[0], PHASE2_POLICIES[0], first),
            (PHASE1_POLICIES[1], PHASE2_POLICIES[1], second),
        )
    )
    assert p1 == PHASE1_POLICIES[1]
    assert p2 == PHASE2_POLICIES[1]
    assert score == second


def test_selection_never_uses_unsafe_pair_even_when_faster() -> None:
    safe = _score(p60=0.20)
    unsafe = replace(
        _score(p60=0.90, safe=False, breach=0.02, dd99=0.08),
        phase1_policy_name=PHASE1_POLICIES[1].name,
        phase2_policy_name=PHASE2_POLICIES[1].name,
    )
    p1, p2, score = select_risk_pair(
        (
            (PHASE1_POLICIES[0], PHASE2_POLICIES[0], safe),
            (PHASE1_POLICIES[1], PHASE2_POLICIES[1], unsafe),
        )
    )
    assert p1 == PHASE1_POLICIES[0]
    assert p2 == PHASE2_POLICIES[0]
    assert score == safe
