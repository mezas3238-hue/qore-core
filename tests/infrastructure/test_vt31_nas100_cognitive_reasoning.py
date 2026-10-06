from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    dossier_payload,
    dossier_runtime_view,
    market_memory_manifest,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
    memory_payload,
    validate_memory,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
    reason,
    reason_position,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)
from qore.infrastructure.traders.vt31_nas100_strategy_identity_memory import (
    strategy_identity_fingerprint,
    strategy_identity_payload,
    strategy_identity_runtime_view,
)
from qore.infrastructure.traders.vt31_nas100_trader_experience_memory import (
    trader_experience_fingerprint,
    trader_experience_payload,
    trader_experience_runtime_view,
)


def _situation(
    *,
    minute: int = 10 * 60 + 12,
    last_event: str = "reference-liquidity-sweep",
    reclaim_age: int = 3,
    path_ratio: str = "0.62",
    ref_ratio: str = "0.68",
    side: str = "short",
    h1_state: str = "bearish",
    m15_state: str = "UNWIRED",
) -> Nas100SituationModel:
    return Nas100SituationModel(
        as_of="2020-01-02T15:12:00+00:00",
        weekday="Thursday",
        session="NY_AM_SILVER_BULLET",
        decision_minute_ny=minute,
        side=side,
        setup_family="VT31_AM_SILVER_BULLET_R2_2",
        confirmation_state="confirmed",
        prior_day_state="bullish",
        h4_state="mixed",
        h1_state=h1_state,
        premarket_state="rotation",
        cash_open_state="bearish",
        position_in_prior_day_range="upper-third",
        range_state="compressed",
        volatility_state=(
            "compressed"
            if Decimal(ref_ratio) < Decimal("0.75")
            else (
                "normal"
                if Decimal(ref_ratio) <= Decimal("1.25")
                else "expanded"
            )
        ),
        current_path_vs_previous=Decimal(path_ratio),
        reference_width_vs_prior5=Decimal(ref_ratio),
        raid_depth_ref=Decimal("0.14"),
        recent_path_efficiency=Decimal("0.55"),
        recent_overlap_rate=Decimal("0.71"),
        first_breach_side="high",
        double_sided_before_decision=False,
        reference_reclaimed=True,
        reference_reclaim_age_minutes=reclaim_age,
        last_structure_event_family=last_event,
        last_structure_event_age_minutes=2,
        recent_liquidity_event_count_10m=None,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        entry_evidence_family="fair-value-gap",
        confirmation_latency_minutes=4,
        entry_evidence_freshness="fresh-0-5m",
        stop_plan="SOURCE_SWING_EXTREME",
        risk_ref=Decimal("0.21"),
        planned_target_r=None,
        structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
        destination_distance_ref=Decimal("0.71"),
        journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
        dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
        dol2_state="RESEARCH_ONLY_UNCALIBRATED",
        dol3_state="RESEARCH_ONLY_UNCALIBRATED",
        extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
        exhaustion_state="UNKNOWN",
        cross_index_state="OPTIONAL_CONTEXT_NOT_REQUIRED",
        m15_state=m15_state,
    )


def test_handoff_three_persistent_memories_are_distinct() -> None:
    validate_memory()
    payload = memory_payload()
    assert payload["mind_model"] == (
        "THREE_PERSISTENT_MEMORIES_PLUS_SITUATION"
    )

    strategy = strategy_identity_payload()
    assert strategy["memory_class"] == "STRATEGY_IDENTITY"

    dossier = dossier_payload()
    assert dossier["identity"] == "CIBO_NAS100_MARKET_INTELLIGENCE_DOSSIER_V1"
    assert dossier["market_overall"]["days"] == 1591
    assert dossier["structure_memory"]["rows"] == 59810
    assert dossier["journey_memory"]["completed_reversal_episodes"] == 547

    experience = trader_experience_payload()
    assert experience["memory_class"] == "TRADER_EXPERIENCE_LAB"

    manifest = market_memory_manifest()
    assert manifest["governed_cibo_memory_store"] is True
    assert manifest["external_cibo_runtime_dependency"] is False
    assert manifest["evidence_tier"] == "E1_ASSOCIATION_ONLY"
    assert manifest["fresh_holdout_opened"] is False

    fingerprints = {
        strategy_identity_fingerprint(),
        str(manifest["memory_fingerprint"]),
        trader_experience_fingerprint(),
        memory_fingerprint(),
    }
    assert len(fingerprints) == 4
    assert all(len(value) == 64 for value in fingerprints)


def test_situation_is_ephemeral_and_contains_no_outcome_oracle() -> None:
    situation = _situation()
    payload = situation.payload()
    assert payload["memory_class"] == "EPHEMERAL_CAUSAL_SITUATION"
    assert payload["persistent_memory"] is False
    assert payload["causal_as_of_only"] is True
    assert payload["terminal_pnl_present"] is False
    assert payload["historical_date_outcome_present"] is False
    assert "r_multiple" not in payload
    assert "terminal_status" not in payload


def test_reasoning_executes_supported_current_state() -> None:
    situation = _situation()
    decision = reason(situation)
    assert decision.action == "EXECUTE"
    assert decision.target_plan == "PRIMARY_STRUCTURAL_BOUNDARY"
    assert decision.contradictions == ()
    assert "source_identity" in decision.strategy_memory_used
    assert "journey_memory" in decision.cibo_market_memory_used
    assert (
        "reference_liquidity_context"
        in decision.trader_experience_memory_used
    )
    assert decision.situation_fingerprint == situation.fingerprint()


def test_reasoning_waits_instead_of_forcing_trade() -> None:
    decision = reason(
        _situation(last_event="fair-value-gap", reclaim_age=10)
    )
    assert decision.action == "WAIT"
    assert (
        "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT"
        in decision.uncertainty
    )
    assert (
        "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION"
        in decision.uncertainty
    )


def test_reasoning_abstains_when_journey_context_is_structurally_wrong() -> None:
    decision = reason(_situation(path_ratio="0.92"))
    assert decision.action == "ABSTAIN"
    assert "SITUATION:CURRENT_PATH_NOT_COMPRESSED" in decision.contradictions


def test_weekday_memory_is_context_not_prohibition() -> None:
    decision = reason(_situation())
    assert "CIBO:WEEKDAY_CONTEXT_AVAILABLE_ASSOCIATION_ONLY" in (
        decision.supporting_evidence
    )
    assert decision.action == "EXECUTE"


def test_public_memory_payloads_are_defensive_copies() -> None:
    strategy_before = strategy_identity_fingerprint()
    cibo_before = dossier_runtime_view()["identity"]
    experience_before = trader_experience_fingerprint()

    strategy_copy = strategy_identity_payload()
    strategy_copy["market"] = "MUTATED"
    dossier_copy = dossier_payload()
    dossier_copy["market"] = "MUTATED"
    experience_copy = trader_experience_payload()
    experience_copy["market"] = "MUTATED"

    assert strategy_identity_runtime_view()["market"] == "NAS100"
    assert dossier_runtime_view()["market"] == "NAS100"
    assert trader_experience_runtime_view()["market"] == "NAS100"
    assert strategy_identity_fingerprint() == strategy_before
    assert dossier_runtime_view()["identity"] == cibo_before
    assert trader_experience_fingerprint() == experience_before


def test_cached_runtime_views_are_stable_identity_objects() -> None:
    assert strategy_identity_runtime_view() is strategy_identity_runtime_view()
    assert dossier_runtime_view() is dossier_runtime_view()
    assert (
        trader_experience_runtime_view()
        is trader_experience_runtime_view()
    )


def test_noncompressed_short_h1_mixed_is_low_dd_fallback() -> None:
    decision = reason(
        _situation(
            ref_ratio="1.05",
            side="short",
            h1_state="mixed",
        )
    )
    assert decision.action == "EXECUTE"
    assert decision.target_plan == "PRIMARY_STRUCTURAL_BOUNDARY"
    assert "EXPERIENCE:LOW_DD_NONCOMPRESSED_SHORT_H1_MIXED" in (
        decision.supporting_evidence
    )


def test_noncompressed_state_outside_low_dd_gate_abstains() -> None:
    decision = reason(
        _situation(
            ref_ratio="1.05",
            side="short",
            h1_state="bearish",
        )
    )
    assert decision.action == "ABSTAIN"
    assert "EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE" in (
        decision.contradictions
    )


def test_reasoning_target_plan_contains_no_r_runtime_threshold() -> None:
    decision = reason(_situation(ref_ratio="1.05", side="short", h1_state="mixed"))
    assert decision.target_plan == "PRIMARY_STRUCTURAL_BOUNDARY"
    assert "1R" not in decision.target_plan
    assert "1.25R" not in decision.target_plan
    assert "3R" not in decision.target_plan
    assert "_R_" not in decision.target_plan
    assert "PARTIAL" not in decision.target_plan


def test_maximum_intelligence_gate_exposes_current_unwired_m15() -> None:
    decision = reason(_situation())

    assert decision.max_intelligence_ready is False
    assert "m15_context" in decision.cognitive_domains_consulted
    assert "M15_CONTEXT_UNWIRED" in decision.max_intelligence_blockers
    assert "SITUATION:M15_CONTEXT_UNWIRED" in decision.uncertainty


def test_wiring_m15_removes_only_the_m15_blocker() -> None:
    decision = reason(_situation(m15_state="bearish-displacement"))

    assert "M15_CONTEXT_UNWIRED" not in decision.max_intelligence_blockers
    assert "DEEPER_JOURNEY_CAPACITY_UNCALIBRATED" in (
        decision.max_intelligence_blockers
    )
    assert "CONTEXTUAL_POSITION_MANAGEMENT_UNRESOLVED" in (
        decision.max_intelligence_blockers
    )
    assert "DOL2_TARGET_INTELLIGENCE_UNCALIBRATED" in (
        decision.max_intelligence_blockers
    )
    assert "DOL3_TARGET_INTELLIGENCE_UNCALIBRATED" in (
        decision.max_intelligence_blockers
    )
    assert decision.max_intelligence_ready is False


def test_maximum_intelligence_manifest_covers_full_cognitive_stack() -> None:
    decision = reason(_situation())
    domains = set(decision.cognitive_domains_consulted)

    required = {
        "strategy_identity",
        "prior_day_context",
        "h4_context",
        "h1_context",
        "m15_context",
        "m1_microstructure",
        "structure",
        "liquidity",
        "regime",
        "volatility",
        "timing_freshness",
        "entry_intelligence",
        "risk_geometry",
        "journey_intelligence",
        "target_exit_intelligence",
        "cibo_market_memory",
        "trader_experience_memory",
        "cross_index_context",
        "post_entry_reassessment_capability",
        "strategy_native_r_capability",
    }
    assert required.issubset(domains)
    assert decision.strategy_memory_used
    assert decision.cibo_market_memory_used
    assert decision.trader_experience_memory_used


def test_late_market_is_invalid_new_entry_but_not_invalid_live_position() -> None:
    entry_state = _situation(
        minute=10 * 60 + 12,
        m15_state="bearish",
    )
    entry_reasoning = reason(entry_state)
    assert entry_reasoning.action == "EXECUTE"

    current = _situation(
        minute=10 * 60 + 45,
        m15_state="bearish",
    )
    admission = reason(current)
    position = reason_position(
        current,
        frozen_entry_reasoning=entry_reasoning,
    )

    assert admission.action == "ABSTAIN"
    assert "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE" in (
        admission.contradictions
    )
    assert position.action == "EXECUTE"
    assert "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE" not in (
        position.contradictions
    )
    assert any(
        item.startswith(
            "POSITION:ADMISSION_ONLY_CONTRADICTION="
            "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE"
        )
        for item in position.context_observations
    )


def test_calibrated_journey_depletion_remains_position_authority() -> None:
    entry_state = _situation(m15_state="bearish")
    entry_reasoning = reason(entry_state)

    current = _situation(
        minute=10 * 60 + 45,
        m15_state="bearish",
    )
    current = replace(
        current,
        journey_stage="POST_1R_H5_ENTRY_OR_WORSE",
        extension_capacity_state=(
            "CALIBRATED_POST1R_CONTINUATION_DEPLETED"
        ),
        exhaustion_state="FAILED_CONTINUATION_CONFIRMED",
    )
    position = reason_position(
        current,
        frozen_entry_reasoning=entry_reasoning,
    )

    assert position.action == "ABSTAIN"
    assert "JOURNEY:POST1R_CONTINUATION_DEPLETED" in (
        position.contradictions
    )
    assert position.max_intelligence_ready is False
    assert "DOL2_TARGET_INTELLIGENCE_UNCALIBRATED" in (
        position.max_intelligence_blockers
    )
    assert "DOL3_TARGET_INTELLIGENCE_UNCALIBRATED" in (
        position.max_intelligence_blockers
    )


def test_h4_unavailable_blocks_maximum_intelligence() -> None:
    situation = replace(
        _situation(m15_state="bearish"),
        h4_state="unavailable",
    )
    decision = reason(situation)

    assert decision.max_intelligence_ready is False
    assert "H4_CONTEXT_UNAVAILABLE" in decision.max_intelligence_blockers
    assert "SITUATION:H4_CONTEXT_UNAVAILABLE" in decision.uncertainty
