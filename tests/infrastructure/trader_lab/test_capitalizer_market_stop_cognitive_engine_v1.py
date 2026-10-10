from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_market_stop_cognitive_engine_v1 import (
    CapitalizerBreathingState,
    CapitalizerBufferEvidenceKind,
    CapitalizerMarketStopMemory,
    CapitalizerMarketStopSpecialist,
    CapitalizerPostEntryStopAction,
    CapitalizerStopDecision,
    CapitalizerStopStateFamilyProfile,
    CapitalizerStopStructuralFacts,
    assess_post_entry_stop_transition,
    build_market_memory,
    evaluate_market_stop,
)


def _memory() -> CapitalizerMarketStopMemory:
    return CapitalizerMarketStopMemory(
        identity="QORE_CAPITALIZER_MARKET_STOP_MEMORY_V1",
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        source_forensic_identity="QORE_CAPITALIZER_M1_LOSS_CAUSAL_FORENSICS_V1",
        source_trade_count=1362,
        stop_count=763,
        same_session_target_recovery_rate=Decimal("0.2097"),
        median_extra_stop_r_recovered=Decimal("1.11"),
        p75_extra_stop_r_recovered=Decimal("3.01"),
        p90_extra_stop_r_recovered=Decimal("6.66"),
        cross_feature_loss_higher=("planned_reward_r", "setup_age_minutes"),
        evidence_status="CONSUMED_FORENSIC_EVIDENCE",
    )


def _facts() -> CapitalizerStopStructuralFacts:
    return CapitalizerStopStructuralFacts(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        side=CapitalizerSide.LONG,
        state_family_id="NAS100:NY:LONG:FRESH:RECLAIM_NO:DISP_STRONG",
        entry_price=Decimal("20150"),
        target_price=Decimal("20190"),
        m1_protected_swing_price=Decimal("20142.6"),
        m1_mss_origin_price=Decimal("20141.8"),
        m1_order_block_low=Decimal("20142.1"),
        m1_order_block_high=Decimal("20149.5"),
        m1_fvg_low=Decimal("20148.0"),
        m1_fvg_high=Decimal("20150.5"),
        liquidity_raid_level=Decimal("20143.0"),
        tick_size=Decimal("0.1"),
        spread_ticks=Decimal("8"),
        volatility_ticks=Decimal("120"),
        session_elapsed_minutes=95,
        fresh_repeat_state="FRESH",
        reclaim_state="NO_RECLAIM",
        displacement_state="STRONG",
        expansion_speed_state="FAST",
    )


def test_structural_stop_without_exact_memory_does_not_invent_buffer() -> None:
    specialist = CapitalizerMarketStopSpecialist(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        memory=_memory(),
    )
    proposal = evaluate_market_stop(facts=_facts(), specialist=specialist)
    assert proposal.decision is CapitalizerStopDecision.STRUCTURAL_STOP
    assert proposal.invalidation_anchor == "M1_PROTECTED_SWING"
    assert proposal.structural_stop_price == Decimal("20142.6")
    assert proposal.execution_buffer_ticks == 0
    assert proposal.final_stop_price == Decimal("20142.6")
    assert proposal.expected_breathing is CapitalizerBreathingState.NORMAL
    assert proposal.qore_risk_approval_required is True
    assert proposal.grants_capital_authority is False
    assert proposal.rule_promotion_allowed is False


def test_exact_market_state_can_propose_research_buffer() -> None:
    profile = CapitalizerStopStateFamilyProfile(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        state_family_id=_facts().state_family_id,
        observations=120,
        candidate_buffer_ticks=Decimal("18"),
        evidence_kind=CapitalizerBufferEvidenceKind.STRUCTURAL_EQUIVALENT_EXCURSION,
        replay_frozen=True,
        fresh_holdout_consumed=True,
    )
    specialist = CapitalizerMarketStopSpecialist(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        memory=_memory(),
        state_profiles=(profile,),
    )
    proposal = evaluate_market_stop(facts=_facts(), specialist=specialist)
    assert (
        proposal.decision
        is CapitalizerStopDecision.STRUCTURAL_STOP_WITH_CANDIDATE_BREATHING
    )
    assert proposal.execution_buffer_ticks == Decimal("18")
    assert proposal.final_stop_price == Decimal("20140.8")
    assert proposal.live_authorized is False
    assert proposal.real_capital_authorized is False


def test_recovery_only_memory_cannot_widen_stop() -> None:
    profile = CapitalizerStopStateFamilyProfile(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        state_family_id=_facts().state_family_id,
        observations=120,
        candidate_buffer_ticks=Decimal("18"),
        evidence_kind=CapitalizerBufferEvidenceKind.RECOVERY_ONLY,
        replay_frozen=True,
        fresh_holdout_consumed=True,
    )
    specialist = CapitalizerMarketStopSpecialist(
        symbol="NAS100",
        session=CapitalizerSession.NEW_YORK,
        memory=_memory(),
        state_profiles=(profile,),
    )
    proposal = evaluate_market_stop(facts=_facts(), specialist=specialist)
    assert proposal.decision is CapitalizerStopDecision.STRUCTURAL_STOP
    assert proposal.execution_buffer_ticks == 0
    assert proposal.final_stop_price == Decimal("20142.6")
    assert "REJECT_STOP_WIDENING_RECOVERY_ONLY_EVIDENCE" in (
        proposal.adversarial_findings
    )


def test_post_entry_stop_can_hold_or_improve_but_never_widen() -> None:
    widen = assess_post_entry_stop_transition(
        side=CapitalizerSide.LONG,
        current_stop_price=Decimal("20142.6"),
        requested_stop_price=Decimal("20140.8"),
    )
    improve = assess_post_entry_stop_transition(
        side=CapitalizerSide.LONG,
        current_stop_price=Decimal("20142.6"),
        requested_stop_price=Decimal("20145.0"),
    )
    hold = assess_post_entry_stop_transition(
        side=CapitalizerSide.LONG,
        current_stop_price=Decimal("20142.6"),
        requested_stop_price=Decimal("20142.6"),
    )
    assert widen.action is CapitalizerPostEntryStopAction.REJECT_WIDENING
    assert improve.action is CapitalizerPostEntryStopAction.IMPROVE
    assert hold.action is CapitalizerPostEntryStopAction.HOLD


def test_consumed_forensics_build_broad_memory_only(tmp_path: Path) -> None:
    raw = {
        "identity": "QORE_CAPITALIZER_M1_LOSS_CAUSAL_FORENSICS_V1",
        "symbol": "NAS100",
        "session": "NEW_YORK",
        "source_trade_count": 1362,
        "evidence_status": "CONSUMED_FORENSIC_EVIDENCE",
        "stop_intelligence": {
            "stops": 763,
            "target_recovery_rate": "0.2097",
            "median_extra_stop_r_needed_for_recovered": "1.11",
            "p75_extra_stop_r_needed_for_recovered": "3.01",
            "p90_extra_stop_r_needed_for_recovered": "6.66",
        },
        "winner_loser_feature_medians": {
            "setup_age_minutes": {"direction": "LOSS_HIGHER"},
            "planned_reward_r": {"direction": "LOSS_HIGHER"},
            "displacement_body_ratio": {"direction": "LOSS_LOWER"},
        },
    }
    memory = build_market_memory(raw)
    assert memory.symbol == "NAS100"
    assert memory.exact_state_family_profiles_present is False
    assert memory.executable_buffer_frozen is False
    assert memory.holdout_fresh_after_memory_build is False
    assert memory.runtime_mutation_allowed is False
    assert memory.cross_feature_loss_higher == (
        "planned_reward_r",
        "setup_age_minutes",
    )
