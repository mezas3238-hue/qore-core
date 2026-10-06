"""Frozen runtime policy for VT31 NAS100 Comparator 009.

Comparator 009 keeps the Comparator-008 admission stack and adds the validated
maximum-cognition Breaker MIXED weak-efficiency pre-DOL1 exit.

This module contains causal pure-edge policy only. It has no sizing, leverage,
compounding, portfolio, broker-volume, equity or capital-allocation authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from qore.infrastructure.traders.vt31_nas100_comp008_policy import (
    MATERIAL_ADVERSE_R,
    Comparator003PretargetExitFacts,
    Comparator008AdmissionDecision,
    Comparator008AdmissionFacts,
    comparator003_pretarget_exit_allowed,
    comparator008_admission_decision,
    comparator008_facts_from_replay_row,
    comparator008_facts_from_situation,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)

POLICY_ID = "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
WEAK_EFFICIENCY_MAX = Decimal("0.30")


@dataclass(frozen=True, slots=True)
class Comparator009AdmissionDecision:
    policy_id: str
    admitted: bool
    abstention_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Comparator009PretargetExitFacts:
    pre_dol1: bool
    maximum_cognition_verified: bool
    current_open_r: Decimal
    management_context: str
    reference_reclaim_age_minutes: int | None
    destination_state: str
    entry_family: str
    reference_volatility_state: str
    recent_path_efficiency: Decimal | None


@dataclass(frozen=True, slots=True)
class Comparator009PretargetExitDecision:
    policy_id: str
    exit_authorized: bool
    comp003_base_exit_authorized: bool
    weak_efficiency_exit_authorized: bool


def _wrap_admission(
    decision: Comparator008AdmissionDecision,
) -> Comparator009AdmissionDecision:
    return Comparator009AdmissionDecision(
        policy_id=POLICY_ID,
        admitted=decision.admitted,
        abstention_reasons=decision.abstention_reasons,
    )


def comparator009_admission_decision(
    facts: Comparator008AdmissionFacts,
) -> Comparator009AdmissionDecision:
    """Apply the unchanged Comparator-008 admission stack under COMP009."""

    return _wrap_admission(comparator008_admission_decision(facts))


def comparator009_admission_from_situation(
    state: Nas100SituationModel,
) -> Comparator009AdmissionDecision:
    return comparator009_admission_decision(
        comparator008_facts_from_situation(state)
    )


def comparator009_admission_from_replay_row(
    row: Mapping[str, object],
) -> Comparator009AdmissionDecision:
    return comparator009_admission_decision(
        comparator008_facts_from_replay_row(row)
    )


def _weak_efficiency_exit_allowed(
    facts: Comparator009PretargetExitFacts,
) -> bool:
    if not facts.pre_dol1:
        return False
    if facts.entry_family != "breaker":
        return False
    if not facts.maximum_cognition_verified:
        return False
    if facts.current_open_r > MATERIAL_ADVERSE_R:
        return False
    if facts.management_context != "MIXED":
        return False
    if facts.recent_path_efficiency is None:
        return False
    return facts.recent_path_efficiency <= WEAK_EFFICIENCY_MAX


def comparator009_pretarget_exit_decision(
    facts: Comparator009PretargetExitFacts,
) -> Comparator009PretargetExitDecision:
    """Apply the frozen COMP003 base exits plus the validated COMP009 delta."""

    if not facts.pre_dol1:
        return Comparator009PretargetExitDecision(
            policy_id=POLICY_ID,
            exit_authorized=False,
            comp003_base_exit_authorized=False,
            weak_efficiency_exit_authorized=False,
        )

    base = comparator003_pretarget_exit_allowed(
        Comparator003PretargetExitFacts(
            maximum_cognition_verified=facts.maximum_cognition_verified,
            current_open_r=facts.current_open_r,
            management_context=facts.management_context,
            reference_reclaim_age_minutes=(
                facts.reference_reclaim_age_minutes
            ),
            destination_state=facts.destination_state,
            entry_family=facts.entry_family,
            reference_volatility_state=facts.reference_volatility_state,
        )
    )
    weak = _weak_efficiency_exit_allowed(facts)
    return Comparator009PretargetExitDecision(
        policy_id=POLICY_ID,
        exit_authorized=base or weak,
        comp003_base_exit_authorized=base,
        weak_efficiency_exit_authorized=weak,
    )


def comparator009_pretarget_exit_from_diagnostic(
    diagnostic: Mapping[str, object],
    *,
    entry_family: str,
    reference_volatility_state: str,
    pre_dol1: bool,
) -> Comparator009PretargetExitDecision:
    reclaim = diagnostic.get("reference_reclaim_age_minutes")
    efficiency = diagnostic.get("recent_path_efficiency")
    return comparator009_pretarget_exit_decision(
        Comparator009PretargetExitFacts(
            pre_dol1=pre_dol1,
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
            recent_path_efficiency=(
                None if efficiency is None else Decimal(str(efficiency))
            ),
        )
    )
