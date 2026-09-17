"""CIBO Journey Intelligence contract for Turtle Soup XAUUSD.

Research-only, provider-neutral knowledge layer. It turns consumed forensic
evidence into explicit structural knowledge without converting CIBO into a
return-maximising score or granting execution authority.

The contract separates:
1. pre-entry structural observation;
2. historical memory known before the observation time; and
3. an epistemic assessment (known invalid / conflicted / unknown).

Historical outcomes may inform hypotheses and uncertainty, but never become an
order, a risk bypass, a date rule, or a fresh-holdout claim.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from collections.abc import Sequence
from typing import Any

IDENTITY = "TURTLE_SOUP_XAUUSD_R10_CIBO_JOURNEY_INTELLIGENCE_CONTRACT_V1"
EVIDENCE_STATUS = (
    "CONSUMED_CIBO_10Y_JOURNEY_INTELLIGENCE_FOUNDATION_NOT_FRESH_HOLDOUT"
)

EVIDENCE_REFS = (
    {
        "code": "R9_CAUSAL_BREAK_DISCRIMINATOR",
        "run_id": 35274286150,
        "artifact_id": 10518674739,
        "digest": "sha256:a445b550a09e75050bc7bc11764c7f72db51d74485df14427e87022d1c765254",
    },
    {
        "code": "R9_JOURNEY_DIVERGENCE_FORENSICS",
        "run_id": 35275016846,
        "artifact_id": 10520147121,
        "digest": "sha256:813d0a6ee79aa16d45ef0d872b3905773e1800a5fcf32b207473a7b8751a9054",
    },
    {
        "code": "R9_LIQUIDITY_SIGNIFICANCE_FORENSICS",
        "run_id": 35275461733,
        "artifact_id": 10520471534,
        "digest": "sha256:aba7a747488487c7bee744ba04783d64f14dce65b167b6b7cd97af15dfdd61a2",
    },
    {
        "code": "R9_CISD_SEQUENCE_FORENSICS",
        "run_id": 35275903599,
        "artifact_id": 10520337279,
        "digest": "sha256:b623b7cd9a895c631d0a63633f94c64760d2400c6e58e1fc89a83097bc2e448f",
    },
)


class JourneyEpistemicState(StrEnum):
    KNOWN_INVALID = "KNOWN_INVALID"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


class JourneyDirective(StrEnum):
    ABSTAIN_STRUCTURAL = "ABSTAIN_STRUCTURAL"
    ABSTAIN_CONFLICTED = "ABSTAIN_CONFLICTED"
    NO_DECISION = "NO_DECISION"


class JourneyOutcome(StrEnum):
    ACTIVE_DOL_REACHED = "ACTIVE_DOL_REACHED"
    INVALIDATED_BEFORE_ACTIVE_DOL = "INVALIDATED_BEFORE_ACTIVE_DOL"
    OTHER = "OTHER"


class JourneyHypothesis(StrEnum):
    INVALIDATION_RISK_ELEVATED = "INVALIDATION_RISK_ELEVATED"
    MULTIPLE_CONTINUATIONS_PLAUSIBLE = "MULTIPLE_CONTINUATIONS_PLAUSIBLE"
    INSUFFICIENT_STRUCTURAL_KNOWLEDGE = "INSUFFICIENT_STRUCTURAL_KNOWLEDGE"


@dataclass(frozen=True)
class JourneyObservation:
    observed_at: datetime
    side: str
    source_timeframe: str
    raid_depth_source_fraction: Decimal
    reclaim_latency_minutes: Decimal
    cisd_progress_exact: Decimal
    protected_risk_source_fraction: Decimal
    h4_range_state: str | None = None


@dataclass(frozen=True)
class HistoricalJourneyCase:
    observed_at: datetime
    mechanism_code: str
    outcome: JourneyOutcome


@dataclass(frozen=True)
class HistoricalMemorySummary:
    mechanism_code: str
    prior_cases: int
    active_dol_reached: int
    invalidated_before_active_dol: int
    other: int
    leading_observed_outcome: JourneyOutcome | None
    operating_signal: bool = False


@dataclass(frozen=True)
class JourneyIntelligenceAssessment:
    identity: str
    mechanism_code: str
    epistemic_state: JourneyEpistemicState
    directive: JourneyDirective
    hypothesis: JourneyHypothesis
    reasons: tuple[str, ...]
    memory: HistoricalMemorySummary
    operating_rule: bool = False
    candidate_promoted: bool = False
    fresh_holdout_consumed: bool = False
    demo_eligible: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False


def _in_open_closed(value: Decimal, low: str, high: str) -> bool:
    return Decimal(low) < value <= Decimal(high)


def identify_structural_mechanism(observation: JourneyObservation) -> str:
    """Attach a pre-entry observation to an already-documented causal family.

    These boundaries are not searched here. They are previously documented
    R6/R8 forensic families and are used only to attach known evidence.
    """
    raid = observation.raid_depth_source_fraction
    reclaim = observation.reclaim_latency_minutes
    cisd = observation.cisd_progress_exact
    risk = observation.protected_risk_source_fraction

    deep_raid = _in_open_closed(raid, "0.25", "0.50")
    medium_raid = _in_open_closed(raid, "0.10", "0.25")
    protected_risk = _in_open_closed(risk, "0.50", "1.00")
    fast_reclaim = reclaim <= Decimal("5")

    if deep_raid and fast_reclaim and cisd > Decimal("0.75") and protected_risk:
        return "ROBUST_INVALID_DEEP_RAID_LATE_CISD"
    if (
        deep_raid
        and fast_reclaim
        and _in_open_closed(cisd, "0.50", "0.75")
        and protected_risk
    ):
        return "BREAK_A_DEEP_RAID_MID_LATE_CISD"
    if (
        medium_raid
        and fast_reclaim
        and _in_open_closed(cisd, "0.25", "0.50")
        and protected_risk
        and observation.h4_range_state == "normal_0.75_1.25"
    ):
        return "BREAK_B_MEDIUM_RAID_EARLY_MID_CISD_NORMAL_H4"
    return "UNRESOLVED_JOURNEY"


def summarize_prior_memory(
    *,
    current_at: datetime,
    mechanism_code: str,
    history: Sequence[HistoricalJourneyCase],
) -> HistoricalMemorySummary:
    """Summarize only causally available prior cases of the same mechanism."""
    prior = [
        item
        for item in history
        if item.observed_at < current_at and item.mechanism_code == mechanism_code
    ]
    counts = {item: 0 for item in JourneyOutcome}
    for item in prior:
        counts[item.outcome] += 1

    leading: JourneyOutcome | None = None
    if prior:
        ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        if len(ordered) == 1 or ordered[0][1] > ordered[1][1]:
            leading = ordered[0][0]

    return HistoricalMemorySummary(
        mechanism_code=mechanism_code,
        prior_cases=len(prior),
        active_dol_reached=counts[JourneyOutcome.ACTIVE_DOL_REACHED],
        invalidated_before_active_dol=counts[
            JourneyOutcome.INVALIDATED_BEFORE_ACTIVE_DOL
        ],
        other=counts[JourneyOutcome.OTHER],
        leading_observed_outcome=leading,
    )


def assess_journey(
    observation: JourneyObservation,
    history: Sequence[HistoricalJourneyCase] = (),
) -> JourneyIntelligenceAssessment:
    mechanism = identify_structural_mechanism(observation)
    memory = summarize_prior_memory(
        current_at=observation.observed_at,
        mechanism_code=mechanism,
        history=history,
    )

    if mechanism == "ROBUST_INVALID_DEEP_RAID_LATE_CISD":
        return JourneyIntelligenceAssessment(
            identity=IDENTITY,
            mechanism_code=mechanism,
            epistemic_state=JourneyEpistemicState.KNOWN_INVALID,
            directive=JourneyDirective.ABSTAIN_STRUCTURAL,
            hypothesis=JourneyHypothesis.INVALIDATION_RISK_ELEVATED,
            reasons=(
                "same causal anatomy was negative across early, transition, and recent consumed partitions",
                "abstention is attached to the structural mechanism, not year/date",
            ),
            memory=memory,
        )

    if mechanism.startswith("BREAK_A_") or mechanism.startswith("BREAK_B_"):
        return JourneyIntelligenceAssessment(
            identity=IDENTITY,
            mechanism_code=mechanism,
            epistemic_state=JourneyEpistemicState.CONFLICTED,
            directive=JourneyDirective.ABSTAIN_CONFLICTED,
            hypothesis=JourneyHypothesis.MULTIPLE_CONTINUATIONS_PLAUSIBLE,
            reasons=(
                "family was historically viable but degraded in the recent consumed regime",
                "R9 shows most recent failures die before touching any active DOL",
                "liquidity and CISD evidence does not support a universal scalar repair",
            ),
            memory=memory,
        )

    return JourneyIntelligenceAssessment(
        identity=IDENTITY,
        mechanism_code=mechanism,
        epistemic_state=JourneyEpistemicState.UNKNOWN,
        directive=JourneyDirective.NO_DECISION,
        hypothesis=JourneyHypothesis.INSUFFICIENT_STRUCTURAL_KNOWLEDGE,
        reasons=(
            "no frozen causal validity rule exists for this journey anatomy",
            "unknown must remain unknown until a structural explanation is validated",
        ),
        memory=memory,
    )


def contract_manifest() -> dict[str, Any]:
    return {
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "purpose": (
            "Give the XAUUSD Turtle Soup specialist explicit causal memory, "
            "epistemic states, and abstention reasons before any promotion test."
        ),
        "intelligence_model": {
            "kind": "case-informed causal structural reasoning",
            "return_maximising_score": False,
            "automatic_threshold_search": False,
            "date_or_year_operating_feature": False,
            "post_entry_feature_allowed_for_operating_decision": False,
            "historical_memory_must_precede_observation_time": True,
            "unknown_state_is_first_class": True,
            "conflicted_state_is_first_class": True,
        },
        "known_states": {
            "ROBUST_INVALID_DEEP_RAID_LATE_CISD": "KNOWN_INVALID",
            "BREAK_A_DEEP_RAID_MID_LATE_CISD": "CONFLICTED",
            "BREAK_B_MEDIUM_RAID_EARLY_MID_CISD_NORMAL_H4": "CONFLICTED",
            "UNRESOLVED_JOURNEY": "UNKNOWN",
        },
        "evidence_refs": list(EVIDENCE_REFS),
        "governance": {
            "candidate_promoted": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "next_research_question": (
            "Can liquidity significance, CISD sequence, Protected Swing causality, "
            "and DOL topology explain journey validity consistently enough to "
            "upgrade UNKNOWN/CONFLICTED states without retrospective PnL mining?"
        ),
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    payload = contract_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n")
    print(json.dumps(_jsonable(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
