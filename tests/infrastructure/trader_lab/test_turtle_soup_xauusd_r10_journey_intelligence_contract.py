from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r10_journey_intelligence_contract import (
    HistoricalJourneyCase,
    JourneyDirective,
    JourneyEpistemicState,
    JourneyHypothesis,
    JourneyObservation,
    JourneyOutcome,
    assess_journey,
    contract_manifest,
    identify_structural_mechanism,
    summarize_prior_memory,
)


def _obs(
    *,
    raid: str,
    reclaim: str,
    cisd: str,
    risk: str,
    h4: str | None = None,
) -> JourneyObservation:
    return JourneyObservation(
        observed_at=datetime(2026, 9, 17, 12, tzinfo=UTC),
        side="short",
        source_timeframe="H1",
        raid_depth_source_fraction=Decimal(raid),
        reclaim_latency_minutes=Decimal(reclaim),
        cisd_progress_exact=Decimal(cisd),
        protected_risk_source_fraction=Decimal(risk),
        h4_range_state=h4,
    )


def test_robust_invalid_is_structural_abstention() -> None:
    observation = _obs(raid="0.35", reclaim="5", cisd="0.80", risk="0.75")
    result = assess_journey(observation)
    assert identify_structural_mechanism(observation) == "ROBUST_INVALID_DEEP_RAID_LATE_CISD"
    assert result.epistemic_state is JourneyEpistemicState.KNOWN_INVALID
    assert result.directive is JourneyDirective.ABSTAIN_STRUCTURAL
    assert result.hypothesis is JourneyHypothesis.INVALIDATION_RISK_ELEVATED
    assert result.operating_rule is False
    assert result.live_authorized is False


def test_break_a_and_b_remain_conflicted_not_promoted() -> None:
    break_a = _obs(raid="0.35", reclaim="5", cisd="0.65", risk="0.75")
    break_b = _obs(
        raid="0.20",
        reclaim="4",
        cisd="0.40",
        risk="0.75",
        h4="normal_0.75_1.25",
    )
    for observation in (break_a, break_b):
        result = assess_journey(observation)
        assert result.epistemic_state is JourneyEpistemicState.CONFLICTED
        assert result.directive is JourneyDirective.ABSTAIN_CONFLICTED
        assert result.candidate_promoted is False
        assert result.fresh_holdout_consumed is False


def test_unresolved_journey_stays_unknown() -> None:
    result = assess_journey(
        _obs(raid="0.07", reclaim="3", cisd="0.30", risk="0.40")
    )
    assert result.epistemic_state is JourneyEpistemicState.UNKNOWN
    assert result.directive is JourneyDirective.NO_DECISION
    assert result.hypothesis is JourneyHypothesis.INSUFFICIENT_STRUCTURAL_KNOWLEDGE


def test_memory_is_strictly_causal_and_not_an_operating_signal() -> None:
    current = datetime(2026, 9, 17, 12, tzinfo=UTC)
    mechanism = "BREAK_A_DEEP_RAID_MID_LATE_CISD"
    history = (
        HistoricalJourneyCase(
            observed_at=current - timedelta(days=2),
            mechanism_code=mechanism,
            outcome=JourneyOutcome.INVALIDATED_BEFORE_ACTIVE_DOL,
        ),
        HistoricalJourneyCase(
            observed_at=current - timedelta(days=1),
            mechanism_code=mechanism,
            outcome=JourneyOutcome.ACTIVE_DOL_REACHED,
        ),
        HistoricalJourneyCase(
            observed_at=current + timedelta(days=1),
            mechanism_code=mechanism,
            outcome=JourneyOutcome.INVALIDATED_BEFORE_ACTIVE_DOL,
        ),
    )
    memory = summarize_prior_memory(
        current_at=current,
        mechanism_code=mechanism,
        history=history,
    )
    assert memory.prior_cases == 2
    assert memory.invalidated_before_active_dol == 1
    assert memory.active_dol_reached == 1
    assert memory.leading_observed_outcome is None
    assert memory.operating_signal is False


def test_contract_manifest_is_fail_closed_and_evidence_bound() -> None:
    payload = contract_manifest()
    assert payload["identity"].startswith("TURTLE_SOUP_XAUUSD_R10_")
    assert len(payload["evidence_refs"]) == 4
    assert payload["intelligence_model"]["return_maximising_score"] is False
    assert payload["intelligence_model"]["automatic_threshold_search"] is False
    assert payload["intelligence_model"]["date_or_year_operating_feature"] is False
    assert payload["governance"]["candidate_promoted"] is False
    assert payload["governance"]["fresh_holdout_consumed"] is False
    assert payload["governance"]["demo_eligible"] is False
    assert payload["governance"]["live_authorized"] is False
    assert payload["governance"]["real_capital_authorized"] is False
    assert payload["governance"]["production_authorized"] is False
