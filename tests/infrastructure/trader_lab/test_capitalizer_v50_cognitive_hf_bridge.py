from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerEvidenceCalibration,
    CapitalizerEvidenceSource,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CAPITALIZER_IDENTITY,
    CapitalizerSession,
    EvidenceStrength,
)
from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
    CapitalizerExperienceMemory,
    CapitalizerExperienceProfile,
)
from qore.infrastructure.trader_lab.capitalizer_metacognition_v2 import (
    CapitalizerEpistemicReadiness,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50CognitiveCandidateFacts,
    V50CognitiveDisposition,
    assess_v50_cognitive_candidate,
    build_v50_cognitive_state,
)


def _facts(**overrides: object) -> V50CognitiveCandidateFacts:
    values: dict[str, object] = {
        "symbol": "EURUSD",
        "session": CapitalizerSession.LONDON,
        "h1_state_age_minutes": 45,
        "m15_to_m1_delay_minutes": 7,
        "session_minutes_remaining": 90,
        "stop_distance_ticks": Decimal("50"),
        "recent_m1_range_ticks": Decimal("10"),
        "destination_room_r": Decimal("1.25"),
        "trigger_family": "FVG_RETRACE_CISD",
        "h1_basis": "CANDLE2_REVERSAL:BULLISH_FVG",
        "session_slot_ordinal": 1,
        "metacognitive_readiness": CapitalizerEpistemicReadiness.WELL_SUPPORTED,
        "genuinely_new_causal_event": True,
        "repeated_failure_state": False,
    }
    values.update(overrides)
    return V50CognitiveCandidateFacts(**values)  # type: ignore[arg-type]


def test_coherent_fresh_geometry_passes_to_competition() -> None:
    result = assess_v50_cognitive_candidate(
        _facts(),
        experience_memory=CapitalizerExperienceMemory(),
    )
    assert result.disposition is V50CognitiveDisposition.PASS_TO_COMPETITION
    assert result.strategy_may_evaluate is True
    assert result.grants_entry_authority is False


def test_stale_h1_waits_for_refresh_instead_of_consuming_slot() -> None:
    result = assess_v50_cognitive_candidate(
        _facts(h1_state_age_minutes=240),
        experience_memory=CapitalizerExperienceMemory(),
    )
    assert result.disposition is V50CognitiveDisposition.WAIT_REFRESH_H1
    assert result.strategy_may_evaluate is False


def test_late_m1_confirmation_waits_for_fresh_m15_setup() -> None:
    result = assess_v50_cognitive_candidate(
        _facts(m15_to_m1_delay_minutes=60),
        experience_memory=CapitalizerExperienceMemory(),
    )
    assert result.disposition is V50CognitiveDisposition.WAIT_REFRESH_M15


def test_extreme_stop_noise_requests_stop_specialist_not_blind_rejection() -> None:
    result = assess_v50_cognitive_candidate(
        _facts(stop_distance_ticks=Decimal("15")),
        experience_memory=CapitalizerExperienceMemory(),
    )
    assert result.disposition is V50CognitiveDisposition.REFINE_STOP_GEOMETRY
    assert result.requests_stop_refinement is True


def test_tiny_destination_requests_target_ladder() -> None:
    result = assess_v50_cognitive_candidate(
        _facts(destination_room_r=Decimal("0.25")),
        experience_memory=CapitalizerExperienceMemory(),
    )
    assert result.disposition is V50CognitiveDisposition.REFINE_TARGET_LADDER
    assert result.requests_target_refinement is True


def test_exact_negative_experience_can_abstain_without_current_outcome() -> None:
    facts = _facts()
    state = build_v50_cognitive_state(facts)
    calibration = CapitalizerEvidenceCalibration(
        state_family_id=state.state_family_id,
        source=CapitalizerEvidenceSource.DEVELOPMENT_REPLAY,
        source_fingerprint="a" * 64,
        observations=40,
        mean_r=Decimal("-0.20"),
        strength=EvidenceStrength.HIGH,
    )
    profile = CapitalizerExperienceProfile(
        strategy_identity=CAPITALIZER_IDENTITY,
        symbol=facts.symbol,
        session=facts.session,
        state_family_id=state.state_family_id,
        calibration=calibration,
        failure_tags=("NEGATIVE_EXPECTANCY_STATE",),
    )
    result = assess_v50_cognitive_candidate(
        facts,
        experience_memory=CapitalizerExperienceMemory(profiles=(profile,)),
    )
    assert result.disposition is V50CognitiveDisposition.ABSTAIN_KNOWN_NEGATIVE_STATE
    assert result.experience_observations == 40
    assert result.experience_mean_r == Decimal("-0.20")
    assert result.rule_promotion_allowed is False
