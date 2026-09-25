from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.core_stack_v2.competing_risk_decision_gate import (
    CompetingRiskDecision,
    assess_competing_risk_decision,
)
from qore.infrastructure.core_stack_v2.competing_risk_path_core import (
    CompetingRiskBeliefState,
)


def _belief(
    minute: int,
    *,
    stop: int,
    target: int,
    recovery: int,
    uncertainty: int,
    formation: int | None = None,
    path: bool = True,
) -> CompetingRiskBeliefState:
    return CompetingRiskBeliefState(
        as_of=datetime(2026, 9, 25, 12, 0, tzinfo=UTC) + timedelta(minutes=minute),
        stop_pressure_bps=stop,
        stop_formation_bps=stop if formation is None else formation,
        target_capacity_bps=target,
        recovery_strength_bps=recovery,
        uncertainty_bps=uncertainty,
        stop_hazard_proxy_bps=stop,
        target_hazard_proxy_bps=target,
        separation_margin_bps=abs(stop - target),
        path_evidence_available=path,
    )


def test_single_stop_observation_is_only_forming() -> None:
    result = assess_competing_risk_decision(
        (_belief(1, stop=8000, target=2500, recovery=2000, uncertainty=3000),)
    )

    assert result.decision is CompetingRiskDecision.STOP_FORMING
    assert result.stop_persistence_bps == 10000
    assert result.evidence_count == 1


def test_persistent_stop_separation_confirms_stop_likely() -> None:
    result = assess_competing_risk_decision(
        (
            _belief(1, stop=7600, target=2800, recovery=2200, uncertainty=3200),
            _belief(2, stop=7900, target=2400, recovery=1800, uncertainty=3000),
            _belief(3, stop=8300, target=2100, recovery=1600, uncertainty=2600),
        )
    )

    assert result.decision is CompetingRiskDecision.STOP_LIKELY
    assert result.stop_persistence_bps == 10000
    assert "STOP_HAZARD_PERSISTENT" in result.reasons



def test_early_formation_can_prearm_before_confirmed_stop_hazard() -> None:
    result = assess_competing_risk_decision(
        (
            _belief(
                1,
                stop=4600,
                target=2600,
                recovery=1800,
                uncertainty=6000,
                formation=6200,
            ),
        )
    )

    assert result.decision is CompetingRiskDecision.STOP_FORMING
    assert result.latest_stop_hazard_bps < 6500
    assert result.latest_stop_formation_bps >= 5000
    assert "CONFIRMED_STOP_HAZARD_NOT_YET_ESTABLISHED" in result.reasons


def test_persistent_formation_alone_never_becomes_confirmed_stop() -> None:
    result = assess_competing_risk_decision(
        (
            _belief(1, stop=4600, target=2500, recovery=1600, uncertainty=6000, formation=6200),
            _belief(2, stop=4700, target=2400, recovery=1500, uncertainty=5900, formation=6400),
            _belief(3, stop=4800, target=2300, recovery=1400, uncertainty=5800, formation=6600),
        )
    )

    assert result.decision is CompetingRiskDecision.STOP_FORMING
    assert result.stop_formation_persistence_bps == 10000
    assert result.stop_persistence_bps == 0

def test_recovery_veto_blocks_terminal_confirmation() -> None:
    result = assess_competing_risk_decision(
        (
            _belief(1, stop=7600, target=2500, recovery=1800, uncertainty=3000),
            _belief(2, stop=7800, target=2300, recovery=1900, uncertainty=3000),
            _belief(3, stop=4200, target=4300, recovery=8200, uncertainty=7000),
        )
    )

    assert result.decision is CompetingRiskDecision.RECOVERABLE
    assert "STOP_HAZARD_CAPPED_DURING_RECOVERY" in result.reasons


def test_target_requires_persistent_path_supported_separation() -> None:
    result = assess_competing_risk_decision(
        (
            _belief(1, stop=1800, target=7600, recovery=2200, uncertainty=3200),
            _belief(2, stop=1600, target=7900, recovery=1800, uncertainty=2800),
            _belief(3, stop=1500, target=8200, recovery=1700, uncertainty=2500),
        )
    )

    assert result.decision is CompetingRiskDecision.TARGET_LIKELY
    assert result.target_persistence_bps == 10000


def test_high_uncertainty_keeps_destination_contested() -> None:
    result = assess_competing_risk_decision(
        (
            _belief(1, stop=7000, target=3000, recovery=2000, uncertainty=8000),
            _belief(2, stop=7200, target=2800, recovery=2000, uncertainty=7800),
            _belief(3, stop=7400, target=2600, recovery=2000, uncertainty=7600),
        )
    )

    assert result.decision is CompetingRiskDecision.CONTESTED
    assert "UNCERTAINTY_TOO_HIGH_FOR_DECISION" in result.reasons


def test_missing_trade_path_is_insufficient() -> None:
    result = assess_competing_risk_decision(
        (_belief(1, stop=8000, target=1800, recovery=1000, uncertainty=2500, path=False),)
    )

    assert result.decision is CompetingRiskDecision.INSUFFICIENT


def test_decision_gate_is_shadow_only() -> None:
    result = assess_competing_risk_decision(
        (
            _belief(1, stop=7600, target=2800, recovery=1800, uncertainty=3000),
            _belief(2, stop=7800, target=2600, recovery=1800, uncertainty=3000),
            _belief(3, stop=8000, target=2400, recovery=1800, uncertainty=3000),
        )
    )

    assert result.outcome_used is False
    assert result.future_market_used is False
    assert result.management_authority is False
    assert result.sizing_authority is False
    assert result.execution_authority is False
