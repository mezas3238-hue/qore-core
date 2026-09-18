from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    dossier_payload,
    market_memory_manifest,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
    memory_payload,
    validate_memory,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)
from qore.infrastructure.traders.vt31_nas100_strategy_identity_memory import (
    strategy_identity_fingerprint,
    strategy_identity_payload,
)
from qore.infrastructure.traders.vt31_nas100_trader_experience_memory import (
    trader_experience_fingerprint,
    trader_experience_payload,
)


def _situation(
    *,
    minute: int = 10 * 60 + 12,
    last_event: str = "reference-liquidity-sweep",
    reclaim_age: int = 3,
    path_ratio: str = "0.62",
    ref_ratio: str = "0.68",
) -> Nas100SituationModel:
    return Nas100SituationModel(
        as_of="2020-01-02T15:12:00+00:00",
        weekday="Thursday",
        session="NY_AM_SILVER_BULLET",
        decision_minute_ny=minute,
        side="short",
        setup_family="VT31_AM_SILVER_BULLET_R2_2",
        confirmation_state="confirmed",
        prior_day_state="bullish",
        h4_state="mixed",
        h1_state="bearish",
        premarket_state="rotation",
        cash_open_state="bearish",
        position_in_prior_day_range="upper-third",
        range_state="compressed",
        volatility_state="compressed",
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
        planned_target_r=Decimal("3.4"),
        structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
        destination_distance_ref=Decimal("0.71"),
        journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
        dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
        dol2_state="RESEARCH_ONLY_UNCALIBRATED",
        dol3_state="RESEARCH_ONLY_UNCALIBRATED",
        extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
        exhaustion_state="UNKNOWN",
        cross_index_state="OPTIONAL_CONTEXT_NOT_REQUIRED",
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
    assert decision.target_plan == "FULL_STRUCTURAL_BOUNDARY"
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
