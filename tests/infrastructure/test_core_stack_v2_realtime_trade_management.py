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

    assert management["research_status"] == "DEFERRED_UNTIL_NATURAL_DD_INTELLIGENCE_PASSES"
    assert management["may_contribute_to_current_primary_dd_claim"] is False
    assert management["trailing_stop_required_after_phase_unlock"] is True
    assert management["target_extension_allowed_after_phase_unlock"] is True
    assert management["sizing_change_forbidden"] is True
    assert management["same_trade_count_required"] is True
    assert management["same_initial_position_size_required"] is True
    assert management["economic_attribution_must_isolate_shared_trade_management"] is True
    assert management["shared_management_directive_authority"] is True
    assert management["shared_broker_execution_authority"] is False
    assert position["same_position_size_throughout_trade"] is True
    assert position["shared_sizing_use_forbidden"] is True
    assert position["shared_sizing_change_forbidden"] is True
    assert position["shared_position_quantity_change_forbidden"] is True
    assert north_star["shared_behavior_must_be_measured_with_sizing_unchanged"] is True


def test_natural_drawdown_intelligence_must_pass_before_actuation() -> None:
    contract = superintelligence_freeze_contract()
    sequence = contract["drawdown_intelligence_sequence"]
    phase_1 = sequence["phase_1_natural_dd_intelligence"]
    phase_2 = sequence["phase_2_realtime_dd_actuation"]

    assert phase_1["status"] == "ACTIVE_PRIMARY_RESEARCH"
    assert phase_1["sizing_forbidden"] is True
    assert phase_1["trailing_stop_forbidden_for_primary_claim"] is True
    assert phase_1["target_extension_forbidden_for_primary_claim"] is True
    assert phase_1["stop_geometry_mutation_forbidden_for_primary_claim"] is True
    assert phase_1["target_geometry_mutation_forbidden_for_primary_claim"] is True
    assert phase_1["same_trade_universe_required"] is True
    assert phase_1["actual_dd_reduction_not_claimed_until_actuation_phase"] is True

    assert phase_2["status"] == "LOCKED"
    assert phase_2["unlock_requires_phase_1_pass"] is True
    assert phase_2["trailing_stop_allowed_after_unlock"] is True
    assert phase_2["target_extension_allowed_after_unlock"] is True
    assert phase_2["sizing_remains_forbidden"] is True


def test_owner_law_absolutely_forbids_shared_sizing_everywhere() -> None:
    contract = superintelligence_freeze_contract()
    sizing = contract["absolute_shared_sizing_prohibition"]
    phase_b = contract["shared_research_sequence"]["phase_b_external_risk_integration"]

    assert sizing["owner_law"] is True
    assert sizing["scope"] == "ALL_SHARED_RUNTIME_RESEARCH_LABS_AND_FUTURE_PHASES"
    assert sizing["shared_may_read_sizing_to_decide_market_state"] is False
    assert sizing["shared_may_compute_sizing"] is False
    assert sizing["shared_may_recommend_sizing"] is False
    assert sizing["shared_may_change_sizing"] is False
    assert sizing["shared_may_weight_capital"] is False
    assert sizing["shared_may_change_risk_budget"] is False
    assert sizing["shared_may_change_order_quantity"] is False
    assert sizing["shared_may_scale_in_or_scale_out_by_quantity"] is False
    assert sizing["shared_may_claim_dd_improvement_from_sizing"] is False
    assert sizing["shared_success_requires_identical_sizing_baseline"] is True

    assert phase_b["shared_sizing_remains_forbidden"] is True
    assert phase_b["shared_capital_weighting_remains_forbidden"] is True
    assert phase_b["qore_risk_keeps_all_sizing_authority"] is True
    assert phase_b["shared_results_must_continue_to_be_reported_at_identical_sizing"] is True


def test_multi_horizon_competing_futures_is_required_before_actuation() -> None:
    contract = superintelligence_freeze_contract()
    engine = contract["shared_essential_intelligence"]["multi_horizon_competing_futures"]
    phase_1 = contract["drawdown_intelligence_sequence"]["phase_1_natural_dd_intelligence"]

    assert engine["required"] is True
    assert engine["terminal_and_recovery_futures_must_be_explicit_and_competing"] is True
    assert engine["multi_horizon_state_required"] is True
    assert engine["minimum_distinct_horizons"] == 2
    assert engine["preferred_horizons_minutes"] == (5, 15, 30, 60)
    assert engine["scalar_average_cannot_be_primary_discriminator"] is True
    assert engine["forced_binary_guess_when_futures_conflict_forbidden"] is True
    assert engine["runtime_outcome_input_forbidden"] is True
    assert engine["sizing_dependency_forbidden"] is True
    assert engine["phase_1_actuation_authority"] is False

    assert phase_1["must_use_competing_terminal_vs_recoverable_futures"] is True
    assert phase_1["must_use_multi_horizon_causal_state"] is True
    assert phase_1["single_short_window_as_primary_discriminator_forbidden"] is True
    assert phase_1["scalar_threat_average_as_primary_discriminator_forbidden"] is True


def test_universal_drawdown_phenotype_memory_retains_ambiguous_forms() -> None:
    contract = superintelligence_freeze_contract()
    memory = contract["shared_essential_intelligence"]["universal_drawdown_phenotype_memory"]
    phase_1 = contract["drawdown_intelligence_sequence"]["phase_1_natural_dd_intelligence"]

    assert memory["required"] is True
    assert memory["knowledge_not_actuation_in_phase_1"] is True
    assert memory["exact_sequence_memory_required"] is True
    assert memory["morphology_memory_required"] is True
    assert memory["temporal_stability_tracking_required"] is True
    assert memory["winner_overlap_tracking_required"] is True
    assert memory["pure_loss_forms_retained"] is True
    assert memory["loss_dominant_forms_retained"] is True
    assert memory["ambiguous_forms_retained"] is True
    assert memory["winner_dominant_forms_retained_for_disambiguation"] is True
    assert memory["ambiguous_forms_must_not_be_silently_discarded"] is True
    assert memory["runtime_must_be_able_to_mark_unknown_or_unseen_form"] is True
    assert memory["sizing_dependency_forbidden"] is True
    assert memory["phase_1_actuation_authority"] is False

    assert phase_1["universal_drawdown_form_capture_required"] is True
    assert phase_1["pure_and_ambiguous_dd_forms_must_both_be_retained"] is True
    assert phase_1["ambiguous_form_may_inform_perception_but_not_actuation"] is True


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
