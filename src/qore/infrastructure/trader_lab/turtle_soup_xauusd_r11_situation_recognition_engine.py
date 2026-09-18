"""Situation Recognition / Structural Journey Intelligence Engine for XAUUSD.

Research-only reasoning engine. It recognizes the structural situation present
at the entry decision using evidence-bound, pre-entry observations.

It is deliberately NOT:
- a probability-of-profit model;
- a PnL score;
- an execution authorization;
- a date/year regime switch;
- a fresh-holdout consumer.

The engine can recognize a STRUCTURALLY_VALID_CANDIDATE research state when a
pre-registered multi-channel BREAK A morphology transferred without
recalibration across all consumed temporal partitions. That state remains
non-operating until a separate positive-validity contract and fresh validation
are completed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, cast

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r10_cibo_structural_knowledge_base import (
    claim_by_code,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R11_SITUATION_RECOGNITION_ENGINE_V1"
EVIDENCE_STATUS = (
    "CONSUMED_CIBO_10Y_EVIDENCE_BOUND_SITUATION_RECOGNITION_NOT_FRESH_HOLDOUT"
)

# Evidence-family membership MUST reproduce the exact categorical populations
# used by R7/R8. Continuous R9/R10 values are context inside a family and
# cannot broaden family membership.
ROBUST_INVALID_SIGNATURE = {
    "raid_depth_range_bucket": "q4:<=0.50",
    "cisd_progress_bucket": "q4:>0.75",
    "reclaim_latency_bucket": "<=5m",
    "protected_risk_range_bucket": "q3:<=1.0",
}
BREAK_A_SIGNATURE = {
    "raid_depth_range_bucket": "q4:<=0.50",
    "cisd_progress_bucket": "q3:<=0.75",
    "reclaim_latency_bucket": "<=5m",
    "protected_risk_range_bucket": "q3:<=1.0",
}
BREAK_B_SIGNATURE = {
    "raid_depth_range_bucket": "q3:<=0.25",
    "cisd_progress_bucket": "q2:<=0.50",
    "reclaim_latency_bucket": "<=5m",
    "protected_risk_range_bucket": "q3:<=1.0",
    "h4_range_3v20": "normal_0.75_1.25",
}

# Frozen from R10 causal-memory-transfer artifact 10522826606.
# These are not searched or recalibrated here.
A_WICK_MIN = Decimal("0.2041168495008011832860840626")
A_REVIOLATION_MAX = Decimal("0.3897675775115538206129133576")
A_PS_SERIES_MIN = Decimal("2.5")
A_H4_PROXIMITY_MAX = Decimal("0.1326477635782747603833865814")

B_RAID_C1_MIN = Decimal("0.1355108552740873643090739080")
B_PS_RANGE_MIN = Decimal("0.4062280174547331592552635153")
B_CISD_CONFIRM_RANGE_MAX = Decimal("0.9868987820394540371064470545")
B_REVIOLATION_MIN = Decimal("0.1856847314838959585981093021")


class SituationState(StrEnum):
    KNOWN_INVALID = "KNOWN_INVALID"
    STRUCTURALLY_VALID_CANDIDATE = "STRUCTURALLY_VALID_CANDIDATE"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


class SituationDirective(StrEnum):
    ABSTAIN_STRUCTURAL = "ABSTAIN_STRUCTURAL"
    RESEARCH_CANDIDATE_NO_ENTRY = "RESEARCH_CANDIDATE_NO_ENTRY"
    ABSTAIN_CONFLICTED = "ABSTAIN_CONFLICTED"
    NO_DECISION = "NO_DECISION"


class EvidenceGrade(StrEnum):
    ESTABLISHED_NEGATIVE = "ESTABLISHED_NEGATIVE"
    MULTICHANNEL_TRANSFERRED_CLUE = "MULTICHANNEL_TRANSFERRED_CLUE"
    CONFLICTED_WITH_CONTEXT = "CONFLICTED_WITH_CONTEXT"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class SituationObservation:
    observed_at: datetime
    side: str
    source_timeframe: str

    raid_depth_source_fraction: Decimal
    reclaim_latency_minutes: Decimal
    cisd_progress_exact: Decimal
    protected_risk_source_fraction: Decimal
    h4_range_state: str | None

    raid_depth_range_bucket: str
    reclaim_latency_bucket: str
    cisd_progress_bucket: str
    protected_risk_range_bucket: str
    h4_range_3v20: str | None

    c1_directional_wick_fraction: Decimal | None = None
    c1_nearest_prior_h4_boundary_source_fraction: Decimal | None = None
    opposing_series_length: Decimal | None = None
    post_reclaim_max_reviolation_source_fraction: Decimal | None = None

    raid_depth_c1_range_fraction: Decimal | None = None
    ps_candle_range_source_fraction: Decimal | None = None
    confirm_bar_range_vs_prior6_m5: Decimal | None = None

    active_dol_count: int | None = None
    selected_dol_family: str | None = None
    selected_dol_distance_source_fraction: Decimal | None = None


@dataclass(frozen=True)
class EvidenceSignal:
    code: str
    channel: str
    matched: bool | None
    explanation: str
    threshold_source: str


@dataclass(frozen=True)
class SituationAssessment:
    identity: str
    observed_at: datetime
    mechanism_code: str
    state: SituationState
    directive: SituationDirective
    evidence_grade: EvidenceGrade
    evidence_signals: tuple[EvidenceSignal, ...]
    knowledge_claim_codes: tuple[str, ...]
    explanation: tuple[str, ...]
    dol_context: dict[str, Any]
    operating_permission: bool = False
    candidate_promoted: bool = False
    fresh_holdout_consumed: bool = False
    demo_eligible: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False


def _signal(
    *,
    code: str,
    channel: str,
    value: Decimal | None,
    op: str,
    threshold: Decimal,
    explanation: str,
) -> EvidenceSignal:
    if value is None:
        matched: bool | None = None
    elif op == ">=":
        matched = value >= threshold
    elif op == "<=":
        matched = value <= threshold
    else:
        raise ValueError(f"unsupported operator: {op}")
    return EvidenceSignal(
        code=code,
        channel=channel,
        matched=matched,
        explanation=explanation,
        threshold_source="R10_CAUSAL_MEMORY_TRANSFER_ATLAS_CONSUMED_EVIDENCE",
    )


def _break_a_signals(observation: SituationObservation) -> tuple[EvidenceSignal, ...]:
    return (
        _signal(
            code="A_LIQUIDITY_DIRECTIONAL_WICK",
            channel="liquidity_significance",
            value=observation.c1_directional_wick_fraction,
            op=">=",
            threshold=A_WICK_MIN,
            explanation="C1 directional wick matches the frozen BREAK A transferred-liquidity anchor.",
        ),
        _signal(
            code="A_CISD_POST_RECLAIM_REVIOLATION",
            channel="cisd_defense",
            value=observation.post_reclaim_max_reviolation_source_fraction,
            op="<=",
            threshold=A_REVIOLATION_MAX,
            explanation="Post-reclaim re-violation remains within the frozen BREAK A defended-reclaim anchor.",
        ),
        _signal(
            code="A_PS_OPPOSING_SERIES",
            channel="protected_swing_causality",
            value=observation.opposing_series_length,
            op=">=",
            threshold=A_PS_SERIES_MIN,
            explanation="Protected Swing opposing-series length matches a stable BREAK A clue.",
        ),
        _signal(
            code="A_LIQUIDITY_H4_PROXIMITY",
            channel="liquidity_topology",
            value=observation.c1_nearest_prior_h4_boundary_source_fraction,
            op="<=",
            threshold=A_H4_PROXIMITY_MAX,
            explanation="Raided C1 liquidity is near the frozen prior-H4 proximity anchor.",
        ),
    )


def _break_b_signals(observation: SituationObservation) -> tuple[EvidenceSignal, ...]:
    return (
        _signal(
            code="B_RAID_DEPTH_RELATIVE_C1",
            channel="liquidity_raid_anatomy",
            value=observation.raid_depth_c1_range_fraction,
            op=">=",
            threshold=B_RAID_C1_MIN,
            explanation="Raid magnitude relative to C1 matches the transferred BREAK B anchor.",
        ),
        _signal(
            code="B_PS_CANDLE_RANGE",
            channel="protected_swing_causality",
            value=observation.ps_candle_range_source_fraction,
            op=">=",
            threshold=B_PS_RANGE_MIN,
            explanation="Protected Swing candle range matches the transferred BREAK B anchor.",
        ),
        _signal(
            code="B_CISD_CONFIRM_RANGE",
            channel="cisd_sequence",
            value=observation.confirm_bar_range_vs_prior6_m5,
            op="<=",
            threshold=B_CISD_CONFIRM_RANGE_MAX,
            explanation="CISD confirm-range anchor is present, but this clue did not transfer consistently.",
        ),
        _signal(
            code="B_CISD_POST_RECLAIM_REVIOLATION",
            channel="cisd_defense",
            value=observation.post_reclaim_max_reviolation_source_fraction,
            op=">=",
            threshold=B_REVIOLATION_MIN,
            explanation="BREAK B post-reclaim re-violation anchor is present; it remains context only.",
        ),
    )


def _matched(signals: tuple[EvidenceSignal, ...], *codes: str) -> bool:
    selected = {signal.code: signal.matched for signal in signals}
    return all(selected.get(code) is True for code in codes)


def _signature_matches(
    observation: SituationObservation,
    signature: dict[str, str],
) -> bool:
    values = {
        "raid_depth_range_bucket": observation.raid_depth_range_bucket,
        "reclaim_latency_bucket": observation.reclaim_latency_bucket,
        "cisd_progress_bucket": observation.cisd_progress_bucket,
        "protected_risk_range_bucket": observation.protected_risk_range_bucket,
        "h4_range_3v20": observation.h4_range_3v20,
    }
    return all(str(values.get(key)) == expected for key, expected in signature.items())


def _mechanism(observation: SituationObservation) -> str:
    if _signature_matches(observation, ROBUST_INVALID_SIGNATURE):
        return "ROBUST_INVALID_DEEP_RAID_LATE_CISD"
    if _signature_matches(observation, BREAK_A_SIGNATURE):
        return "BREAK_A_DEEP_RAID_MID_LATE_CISD"
    if _signature_matches(observation, BREAK_B_SIGNATURE):
        return "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"
    return "UNRESOLVED_JOURNEY"

def _dol_context(observation: SituationObservation) -> dict[str, Any]:
    return {
        "active_dol_count": observation.active_dol_count,
        "selected_dol_family": observation.selected_dol_family,
        "selected_dol_distance_source_fraction": (
            None
            if observation.selected_dol_distance_source_fraction is None
            else str(observation.selected_dol_distance_source_fraction)
        ),
        "role": (
            "destination_context_only_until_upstream_journey_validity_is_established"
        ),
    }


def assess_situation(observation: SituationObservation) -> SituationAssessment:
    mechanism = _mechanism(observation)

    if mechanism == "ROBUST_INVALID_DEEP_RAID_LATE_CISD":
        claim = claim_by_code("K01_ROBUST_INVALID_DEEP_RAID_LATE_CISD")
        return SituationAssessment(
            identity=IDENTITY,
            observed_at=observation.observed_at,
            mechanism_code=mechanism,
            state=SituationState.KNOWN_INVALID,
            directive=SituationDirective.ABSTAIN_STRUCTURAL,
            evidence_grade=EvidenceGrade.ESTABLISHED_NEGATIVE,
            evidence_signals=(),
            knowledge_claim_codes=(claim.code,),
            explanation=(
                "Exact structural conjunction is repeatedly negative across consumed temporal partitions.",
                "Abstention is attached to anatomy, not calendar date or market side.",
            ),
            dol_context=_dol_context(observation),
        )

    if mechanism == "BREAK_A_DEEP_RAID_MID_LATE_CISD":
        signals = _break_a_signals(observation)
        strongest_pair = _matched(
            signals,
            "A_LIQUIDITY_DIRECTIONAL_WICK",
            "A_CISD_POST_RECLAIM_REVIOLATION",
        )
        if strongest_pair:
            return SituationAssessment(
                identity=IDENTITY,
                observed_at=observation.observed_at,
                mechanism_code=mechanism,
                state=SituationState.STRUCTURALLY_VALID_CANDIDATE,
                directive=SituationDirective.RESEARCH_CANDIDATE_NO_ENTRY,
                evidence_grade=EvidenceGrade.MULTICHANNEL_TRANSFERRED_CLUE,
                evidence_signals=signals,
                knowledge_claim_codes=(
                    claim_by_code("K09_BREAK_A_MULTICHANNEL_TRANSFER_CLUE").code,
                    claim_by_code("K07_BREAK_A_B_REMAIN_CONFLICTED").code,
                    claim_by_code("K08_POSITIVE_VALIDITY_NOT_YET_PROVEN").code,
                ),
                explanation=(
                    "Two independent pre-entry channels match the strongest frozen BREAK A transfer clue.",
                    "The conjunction preserved its structural-capacity direction without recalibration in early, transition, and recent consumed partitions.",
                    "Sample support remains small, so this is a research validity candidate rather than operating permission.",
                ),
                dol_context=_dol_context(observation),
            )

        return SituationAssessment(
            identity=IDENTITY,
            observed_at=observation.observed_at,
            mechanism_code=mechanism,
            state=SituationState.CONFLICTED,
            directive=SituationDirective.ABSTAIN_CONFLICTED,
            evidence_grade=EvidenceGrade.CONFLICTED_WITH_CONTEXT,
            evidence_signals=signals,
            knowledge_claim_codes=(
                claim_by_code("K07_BREAK_A_B_REMAIN_CONFLICTED").code,
                claim_by_code("K05_BREAK_A_OPPOSING_SERIES_LENGTH_CLUE").code,
            ),
            explanation=(
                "BREAK A is historically viable but degraded recently.",
                "The strongest transferred multi-channel clue is not simultaneously present.",
            ),
            dol_context=_dol_context(observation),
        )

    if mechanism == "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4":
        signals = _break_b_signals(observation)
        modest_pair = _matched(
            signals,
            "B_RAID_DEPTH_RELATIVE_C1",
            "B_PS_CANDLE_RANGE",
        )
        explanation = [
            "BREAK B remains conflicted because recent degradation is not yet causally resolved.",
        ]
        if modest_pair:
            explanation.append(
                "Raid-relative-C1 and Protected Swing range match the modest transferred BREAK B clue."
            )
        else:
            explanation.append(
                "The modest transferred BREAK B raid/Protected-Swing conjunction is not present."
            )
        explanation.append(
            "CISD expansion magnitude is explicitly prevented from becoming a universal permission rule."
        )
        return SituationAssessment(
            identity=IDENTITY,
            observed_at=observation.observed_at,
            mechanism_code=mechanism,
            state=SituationState.CONFLICTED,
            directive=SituationDirective.ABSTAIN_CONFLICTED,
            evidence_grade=EvidenceGrade.CONFLICTED_WITH_CONTEXT,
            evidence_signals=signals,
            knowledge_claim_codes=(
                claim_by_code("K07_BREAK_A_B_REMAIN_CONFLICTED").code,
                claim_by_code("K10_BREAK_B_RAID_PS_TRANSFER_CLUE").code,
                claim_by_code("K11_BREAK_B_CISD_EXPANSION_NOT_STABLE").code,
            ),
            explanation=tuple(explanation),
            dol_context=_dol_context(observation),
        )

    claim = claim_by_code("K08_POSITIVE_VALIDITY_NOT_YET_PROVEN")
    return SituationAssessment(
        identity=IDENTITY,
        observed_at=observation.observed_at,
        mechanism_code=mechanism,
        state=SituationState.UNKNOWN,
        directive=SituationDirective.NO_DECISION,
        evidence_grade=EvidenceGrade.INSUFFICIENT,
        evidence_signals=(),
        knowledge_claim_codes=(claim.code,),
        explanation=(
            "No frozen causal situation contract covers this anatomy.",
            "Unknown remains unknown; absence of a known negative is not permission to trade.",
        ),
        dol_context=_dol_context(observation),
    )


def engine_manifest() -> dict[str, Any]:
    return {
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "states": [item.value for item in SituationState],
        "directives": [item.value for item in SituationDirective],
        "evidence_family_signatures": {
            "robust_invalid": dict(ROBUST_INVALID_SIGNATURE),
            "break_a": dict(BREAK_A_SIGNATURE),
            "break_b": dict(BREAK_B_SIGNATURE),
        },
        "frozen_anchors": {
            "break_a": {
                "c1_directional_wick_min": str(A_WICK_MIN),
                "post_reclaim_reviolation_max": str(A_REVIOLATION_MAX),
                "opposing_series_min_context_only": str(A_PS_SERIES_MIN),
                "prior_h4_proximity_max_context_only": str(A_H4_PROXIMITY_MAX),
            },
            "break_b": {
                "raid_depth_c1_min": str(B_RAID_C1_MIN),
                "ps_candle_range_min": str(B_PS_RANGE_MIN),
                "cisd_confirm_range_max_unstable_context_only": str(
                    B_CISD_CONFIRM_RANGE_MAX
                ),
                "post_reclaim_reviolation_min_context_only": str(B_REVIOLATION_MIN),
            },
        },
        "reasoning_contract": {
            "pnl_score": False,
            "probability_of_profit": False,
            "automatic_threshold_search": False,
            "later_period_recalibration": False,
            "continuous_values_can_define_evidence_family_membership": False,
            "evidence_family_membership_uses_exact_r7_r8_buckets": True,
            "year_or_date_operating_input": False,
            "post_entry_input": False,
            "dol_is_destination_context_not_upstream_validity": True,
            "structurally_valid_candidate_is_operating_permission": False,
            "unknown_is_permission": False,
        },
        "governance": {
            "candidate_promoted": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def assessment_to_dict(assessment: SituationAssessment) -> dict[str, Any]:
    raw = asdict(assessment)

    def convert(value: Any) -> Any:
        if isinstance(value, StrEnum):
            return value.value
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): convert(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [convert(item) for item in value]
        return value

    return cast(dict[str, Any], convert(raw))
