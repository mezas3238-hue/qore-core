from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter_ns

from qore.infrastructure.core_stack_v2 import (
    InstinctAssessment,
    InstinctSituation,
    JourneyAssessment,
    JourneyDisposition,
    PositionPathAssessment,
    PositionPathState,
    RealtimeTradeAction,
    StopManagementMode,
    SupportMethodology,
    TargetManagementMode,
    assess_realtime_trade_management,
    superintelligence_freeze_contract,
)

NOW = datetime(2026, 9, 24, 20, 30, tzinfo=UTC)


def _instinct(
    *,
    situation: InstinctSituation,
    methodology: SupportMethodology,
    support: int = 5000,
    threat: int = 5000,
    urgency: int = 5000,
    winner: int = 5000,
    extension: int = 5000,
) -> InstinctAssessment:
    return InstinctAssessment(
        as_of=NOW,
        situation=situation,
        support_methodology=methodology,
        market_support_bps=support,
        threat_bps=threat,
        urgency_bps=urgency,
        shock_risk_bps=threat,
        structural_risk_bps=threat,
        resilience_bps=support,
        threat_convergence_bps=(threat + urgency + threat) // 3,
        confidence_bps=8500,
        winner_protection_bps=winner,
        expansion_capacity_bps=extension,
        reasons=("TEST",),
    )


def _journey(
    *,
    disposition: JourneyDisposition,
    continuation: int = 5000,
    deterioration: int = 5000,
    extension: int = 5000,
) -> JourneyAssessment:
    return JourneyAssessment(
        trader_id="GENERIC_TRADER",
        market="GENERIC_MARKET",
        as_of=NOW,
        disposition=disposition,
        continuation_support_bps=continuation,
        deterioration_bps=deterioration,
        extension_capacity_bps=extension,
        reasons=("TEST",),
    )


def _path(
    *,
    state: PositionPathState,
    winner: int = 5000,
    failure: int = 5000,
) -> PositionPathAssessment:
    return PositionPathAssessment(
        as_of=NOW,
        state=state,
        evidence_count=6,
        path_support_bps=8000 if winner >= failure else 2500,
        adverse_dominance_bps=failure,
        adverse_persistence_bps=7500 if failure >= 7000 else 2500,
        recovery_persistence_bps=2500,
        winner_protection_bps=winner,
        terminal_failure_risk_bps=failure,
        reasons=("TEST",),
    )


def test_realtime_management_compresses_terminal_loss_without_sizing() -> None:
    result = assess_realtime_trade_management(
        _instinct(
            situation=InstinctSituation.TERMINAL_FAILURE_RISK,
            methodology=SupportMethodology.IMMEDIATE_DEFENSE,
            support=1800,
            threat=9000,
            urgency=8800,
            winner=1200,
            extension=1200,
        ),
        _journey(
            disposition=JourneyDisposition.EXIT_RISK_WARNING,
            continuation=1500,
            deterioration=9000,
            extension=1000,
        ),
        _path(
            state=PositionPathState.FAILURE_RISK,
            winner=1200,
            failure=9200,
        ),
        progress_bps=800,
    )

    assert result.action is RealtimeTradeAction.EXIT_RISK
    assert result.stop_mode is StopManagementMode.CAP_QUARTER_RISK
    assert result.maximum_remaining_loss_r is not None
    assert str(result.maximum_remaining_loss_r) == "0.25"
    assert result.sizing_change_allowed is False
    assert result.risk_budget_authority is False
    assert result.order_quantity_authority is False
    assert result.broker_execution_authority is False
    assert result.stop_widening_allowed is False


def test_realtime_management_trails_and_extends_strong_winner() -> None:
    result = assess_realtime_trade_management(
        _instinct(
            situation=InstinctSituation.SUPPORTIVE_EXPANSION,
            methodology=SupportMethodology.EXTENSION_SUPPORT,
            support=9000,
            threat=1200,
            urgency=1000,
            winner=9000,
            extension=9000,
        ),
        _journey(
            disposition=JourneyDisposition.EXTEND,
            continuation=9000,
            deterioration=1000,
            extension=9000,
        ),
        _path(
            state=PositionPathState.FAVORABLE_EXPANSION,
            winner=9000,
            failure=1200,
        ),
        progress_bps=7500,
    )

    assert result.action is RealtimeTradeAction.TRAIL_AND_EXTEND
    assert result.stop_mode is StopManagementMode.TRAIL_WIDE
    assert result.target_mode is TargetManagementMode.EXTEND_200
    assert str(result.target_multiplier) == "2.00"
    assert str(result.trail_distance_r) == "0.75"
    assert result.sizing_change_allowed is False


def test_realtime_management_defends_early_rapid_deterioration() -> None:
    result = assess_realtime_trade_management(
        _instinct(
            situation=InstinctSituation.RAPID_DETERIORATION,
            methodology=SupportMethodology.PROGRESSIVE_DEFENSE,
            support=3200,
            threat=6800,
            urgency=7000,
            winner=1800,
            extension=2200,
        ),
        _journey(
            disposition=JourneyDisposition.DEFEND,
            continuation=3000,
            deterioration=7200,
            extension=2500,
        ),
        _path(
            state=PositionPathState.ADVERSE_DOMINANCE,
            winner=1600,
            failure=6900,
        ),
        progress_bps=1200,
    )

    assert result.action is RealtimeTradeAction.DEFEND
    assert result.stop_mode is StopManagementMode.CAP_HALF_RISK
    assert str(result.maximum_remaining_loss_r) == "0.50"


def test_realtime_management_freeze_forbids_sizing_and_allows_dynamic_path() -> None:
    contract = superintelligence_freeze_contract()
    management = contract["shared_essential_intelligence"]["realtime_trade_management"]
    position = contract["position_law"]
    north_star = contract["shared_essential_intelligence"]["owner_economic_north_star"]

    assert management["trailing_stop_required"] is True
    assert management["target_extension_allowed"] is True
    assert management["sizing_change_forbidden"] is True
    assert management["same_trade_count_required"] is True
    assert management["same_initial_position_size_required"] is True
    assert management["economic_attribution_must_isolate_shared_trade_management"] is True
    assert management["shared_management_directive_authority"] is True
    assert management["shared_broker_execution_authority"] is False
    assert position["same_position_size_throughout_trade"] is True
    assert position["sizing_changes_for_shared_economic_claims_forbidden"] is True
    assert north_star["shared_behavior_must_be_measured_with_sizing_unchanged"] is True


def test_realtime_management_hot_path_is_submillisecond_p95() -> None:
    instinct = _instinct(
        situation=InstinctSituation.RAPID_DETERIORATION,
        methodology=SupportMethodology.PROGRESSIVE_DEFENSE,
        threat=6700,
        urgency=6900,
    )
    journey = _journey(disposition=JourneyDisposition.DEFEND, deterioration=7000)
    path = _path(state=PositionPathState.ADVERSE_DOMINANCE, failure=6800)

    timings: list[int] = []
    for _ in range(5_000):
        start = perf_counter_ns()
        assess_realtime_trade_management(
            instinct,
            journey,
            path,
            progress_bps=1800,
        )
        timings.append(perf_counter_ns() - start)

    timings.sort()
    p95_ns = timings[int(len(timings) * 0.95)]
    assert p95_ns < 1_000_000
