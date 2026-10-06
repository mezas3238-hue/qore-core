"""Frozen pure-edge policy primitives for VT31 NAS100 Comparator 008.

This module contains only causal trader-policy decisions. It has no sizing,
leverage, compounding, portfolio, broker-volume or capital-allocation authority.

The policy is promoted from consumed-evidence research only so the exact same
semantics can be invoked by replay and runtime before the fresh holdout is
opened.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Mapping

from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)

POLICY_ID = "VT31_AB_COMP008_BULLISH_H1_MID_CONFIRMATION_SURVIVOR"
MATERIAL_ADVERSE_R = Decimal("-0.50")


class ConfirmationLatencyState(StrEnum):
    NONE = "NONE"
    FAST_LE5M = "FAST_LE5M"
    MID_6_10M = "MID_6_10M"
    SLOW_GE11M = "SLOW_GE11M"


class ReclaimSequenceState(StrEnum):
    NONE = "NONE"
    FRESH_LT8M = "FRESH_LT8M"
    STALE_8_14M = "STALE_8_14M"
    MATURE_GE15M = "MATURE_GE15M"


@dataclass(frozen=True, slots=True)
class Comparator008AdmissionFacts:
    entry_family: str
    side: str
    prior_day_state: str
    reference_volatility_state: str
    h4_state: str
    h1_state: str
    m15_state: str
    premarket_state: str
    cash_open_state: str
    reference_reclaim_age_minutes: int | None
    confirmation_latency_minutes: int | None


@dataclass(frozen=True, slots=True)
class Comparator008AdmissionDecision:
    policy_id: str
    admitted: bool
    abstention_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Comparator003PretargetExitFacts:
    maximum_cognition_verified: bool
    current_open_r: Decimal
    management_context: str
    reference_reclaim_age_minutes: int | None
    destination_state: str
    entry_family: str
    reference_volatility_state: str


def confirmation_latency_state(
    value: object,
) -> ConfirmationLatencyState:
    if value is None:
        return ConfirmationLatencyState.NONE
    minute = int(value)
    if minute <= 5:
        return ConfirmationLatencyState.FAST_LE5M
    if minute >= 11:
        return ConfirmationLatencyState.SLOW_GE11M
    return ConfirmationLatencyState.MID_6_10M


def reclaim_sequence_state(value: object) -> ReclaimSequenceState:
    if value is None:
        return ReclaimSequenceState.NONE
    age = int(value)
    if age < 8:
        return ReclaimSequenceState.FRESH_LT8M
    if age < 15:
        return ReclaimSequenceState.STALE_8_14M
    return ReclaimSequenceState.MATURE_GE15M


def _order_block_positive_evidence(
    facts: Comparator008AdmissionFacts,
) -> bool:
    if facts.entry_family != "order-block":
        return True
    return (
        facts.side == "short"
        and facts.reference_reclaim_age_minutes is not None
        and facts.reference_reclaim_age_minutes >= 15
    )


def _bullish_rotation_recovery(
    facts: Comparator008AdmissionFacts,
) -> bool:
    return (
        facts.h1_state == "bullish"
        and facts.m15_state == "mixed"
        and facts.premarket_state == "bullish"
        and facts.cash_open_state == "rotation"
        and facts.reference_reclaim_age_minutes is not None
        and facts.reference_reclaim_age_minutes < 8
    )


def comparator008_admission_decision(
    facts: Comparator008AdmissionFacts,
) -> Comparator008AdmissionDecision:
    """Apply the complete frozen Comparator-008 admission stack."""

    reasons: list[str] = []

    if facts.reference_volatility_state == "expanded":
        reasons.append("COMP008:EXPANDED_REFERENCE")

    if not _order_block_positive_evidence(facts):
        reasons.append("COMP008:ORDER_BLOCK_POSITIVE_EVIDENCE_MISSING")

    rotation_compressed = (
        facts.entry_family == "breaker"
        and facts.side == "short"
        and facts.prior_day_state == "rotation"
        and facts.reference_volatility_state == "compressed"
    )
    if rotation_compressed and not _bullish_rotation_recovery(facts):
        reasons.append(
            "COMP008:BREAKER_ROTATION_COMPRESSED_WITHOUT_BULLISH_RECOVERY"
        )

    fvg_fresh_fast = (
        facts.entry_family == "fair-value-gap"
        and facts.side == "short"
        and facts.reference_volatility_state == "compressed"
        and reclaim_sequence_state(facts.reference_reclaim_age_minutes)
        is ReclaimSequenceState.FRESH_LT8M
        and confirmation_latency_state(facts.confirmation_latency_minutes)
        is ConfirmationLatencyState.FAST_LE5M
    )
    if fvg_fresh_fast:
        reasons.append("COMP008:FVG_SHORT_COMPRESSED_FRESH_FAST")

    bearish_compressed_bullish_h1 = (
        facts.entry_family == "breaker"
        and facts.side == "short"
        and facts.prior_day_state == "bearish"
        and facts.reference_volatility_state == "compressed"
        and facts.h1_state == "bullish"
    )
    if bearish_compressed_bullish_h1:
        reasons.append("COMP008:BREAKER_BEARISH_COMPRESSED_H1_BULLISH")

    rapid_conflict_a = (
        facts.entry_family == "breaker"
        and facts.side == "short"
        and facts.prior_day_state == "bullish"
        and facts.reference_volatility_state == "normal"
        and facts.h4_state == "bullish"
        and facts.h1_state == "mixed"
        and facts.m15_state == "mixed"
        and facts.premarket_state == "bearish"
        and facts.cash_open_state == "bullish"
    )
    if rapid_conflict_a:
        reasons.append("COMP008:RAPID_BREAKER_CONFLICT_A")

    rapid_conflict_b = (
        facts.entry_family == "breaker"
        and facts.side == "short"
        and facts.reference_volatility_state == "normal"
        and reclaim_sequence_state(facts.reference_reclaim_age_minutes)
        is ReclaimSequenceState.FRESH_LT8M
        and confirmation_latency_state(facts.confirmation_latency_minutes)
        is ConfirmationLatencyState.MID_6_10M
    )
    if rapid_conflict_b:
        reasons.append("COMP008:RAPID_BREAKER_CONFLICT_B")

    bullish_h1_mid_confirmation = (
        facts.entry_family == "breaker"
        and facts.side == "short"
        and facts.prior_day_state == "bullish"
        and facts.cash_open_state == "bullish"
        and facts.h1_state == "bullish"
        and confirmation_latency_state(facts.confirmation_latency_minutes)
        is ConfirmationLatencyState.MID_6_10M
    )
    if bullish_h1_mid_confirmation:
        reasons.append("COMP008:BULLISH_H1_MID_CONFIRMATION_CONFLICT")

    return Comparator008AdmissionDecision(
        policy_id=POLICY_ID,
        admitted=not reasons,
        abstention_reasons=tuple(reasons),
    )


def comparator008_facts_from_situation(
    state: Nas100SituationModel,
) -> Comparator008AdmissionFacts:
    return Comparator008AdmissionFacts(
        entry_family=state.entry_evidence_family,
        side=state.side,
        prior_day_state=state.prior_day_state,
        reference_volatility_state=state.volatility_state,
        h4_state=state.h4_state,
        h1_state=state.h1_state,
        m15_state=state.m15_state,
        premarket_state=state.premarket_state,
        cash_open_state=state.cash_open_state,
        reference_reclaim_age_minutes=state.reference_reclaim_age_minutes,
        confirmation_latency_minutes=state.confirmation_latency_minutes,
    )


def comparator008_decision_from_situation(
    state: Nas100SituationModel,
) -> Comparator008AdmissionDecision:
    return comparator008_admission_decision(
        comparator008_facts_from_situation(state)
    )


def comparator008_facts_from_replay_row(
    row: Mapping[str, object],
) -> Comparator008AdmissionFacts:
    context_raw = row.get("entry_context")
    if not isinstance(context_raw, Mapping):
        raise ValueError("Comparator-008 replay row requires entry_context")
    context = context_raw
    reclaim = context.get("reference_reclaim_age_minutes")
    confirmation = context.get("confirmation_latency_minutes")
    return Comparator008AdmissionFacts(
        entry_family=str(row["entry_family"]),
        side=str(row["side"]),
        prior_day_state=str(context.get("prior_day_state")),
        reference_volatility_state=str(
            context.get("reference_volatility_state")
        ),
        h4_state=str(context.get("h4_state")),
        h1_state=str(context.get("h1_state")),
        m15_state=str(context.get("m15_state")),
        premarket_state=str(context.get("premarket_state")),
        cash_open_state=str(context.get("cash_open_state")),
        reference_reclaim_age_minutes=(
            None if reclaim is None else int(reclaim)
        ),
        confirmation_latency_minutes=(
            None if confirmation is None else int(confirmation)
        ),
    )


def comparator008_should_abstain_replay_row(
    row: Mapping[str, object],
) -> bool:
    return not comparator008_admission_decision(
        comparator008_facts_from_replay_row(row)
    ).admitted


def comparator003_pretarget_exit_allowed(
    facts: Comparator003PretargetExitFacts,
) -> bool:
    """Frozen Comparator-003 causal pre-DOL1 cognitive-exit authority."""

    if not facts.maximum_cognition_verified:
        return False
    if facts.current_open_r > MATERIAL_ADVERSE_R:
        return False

    stale_sequence = (
        facts.reference_reclaim_age_minutes is not None
        and 8 <= facts.reference_reclaim_age_minutes < 15
    )
    base_safe = facts.management_context == "CAUTIOUS" or (
        facts.management_context == "MIXED" and stale_sequence
    )
    fvg_nonshallow = (
        facts.entry_family == "fair-value-gap"
        and facts.destination_state != "SHALLOW"
    )
    nonob_normal = (
        facts.reference_volatility_state == "normal"
        and facts.entry_family != "order-block"
    )
    return base_safe or fvg_nonshallow or nonob_normal


def comparator003_pretarget_exit_from_diagnostic(
    diagnostic: Mapping[str, object],
    *,
    entry_family: str,
    reference_volatility_state: str,
) -> bool:
    reclaim = diagnostic.get("reference_reclaim_age_minutes")
    return comparator003_pretarget_exit_allowed(
        Comparator003PretargetExitFacts(
            maximum_cognition_verified=(
                diagnostic.get("maximum_cognition_verified") is True
            ),
            current_open_r=Decimal(str(diagnostic["current_open_r"])),
            management_context=str(diagnostic["management_context"]),
            reference_reclaim_age_minutes=(
                None if reclaim is None else int(reclaim)
            ),
            destination_state=str(diagnostic["destination_state"]),
            entry_family=entry_family,
            reference_volatility_state=reference_volatility_state,
        )
    )


COMP008_ADMISSION_CONTRADICTIONS = frozenset(
    {
        "COMP008:EXPANDED_REFERENCE",
        "COMP008:ORDER_BLOCK_POSITIVE_EVIDENCE_MISSING",
        "COMP008:BREAKER_ROTATION_COMPRESSED_WITHOUT_BULLISH_RECOVERY",
        "COMP008:FVG_SHORT_COMPRESSED_FRESH_FAST",
        "COMP008:BREAKER_BEARISH_COMPRESSED_H1_BULLISH",
        "COMP008:RAPID_BREAKER_CONFLICT_A",
        "COMP008:RAPID_BREAKER_CONFLICT_B",
        "COMP008:BULLISH_H1_MID_CONFIRMATION_CONFLICT",
    }
)
