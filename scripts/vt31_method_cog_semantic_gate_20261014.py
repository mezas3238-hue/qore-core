#!/usr/bin/env python3
"""VT31 M0-M6 *semantic* witness assessment; never grants a certificate.

Only tests doctrine/profiles, native cognition and correct WAIT/REJECT behavior.
Cannot replace manual primary-source review, independent authentication,
or a real-Cog replay. No financial, sizing or performance gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

PROFILE_ICT = "ICT_GENERAL_2023"
PROFILE_TTRADES = "TTRADES_NY_AM_2025"
PROFILE_QORE = "QORE_G3_PROPUESTA"
PROFILES = frozenset({PROFILE_ICT, PROFILE_TTRADES, PROFILE_QORE})
GATES = tuple(f"M{i}" for i in range(7))
DECISIONS = frozenset({"TRADE_INTENT", "WAIT", "REJECT", "UNKNOWN"})
SOURCE_AUTHOR = "AUTHOR_PRIMARY"
SOURCE_QORE = "QORE_POLICY"
SOURCE_AMBIGUOUS = "AUTHOR_AMBIGUITY"
COG_NATIVE = "AUTHENTIC_COG"
NO_TRADE = frozenset({"WAIT", "REJECT", "UNKNOWN"})


class SemanticState(StrEnum):
    CONFIRMED_IN_SCOPE = "CONFIRMED_IN_SCOPE"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN_SOURCE = "UNKNOWN_SOURCE"
    PROFILE_CONTAMINATION = "PROFILE_CONTAMINATION"
    NOT_AUTHENTIC_COG = "NOT_AUTHENTIC_COG"
    PENDING_CAUSAL_WITNESS = "PENDING_CAUSAL_WITNESS"
    PENDING_INDEPENDENT_REVIEW = "PENDING_INDEPENDENT_REVIEW"


@dataclass(frozen=True, slots=True)
class SemanticCase:
    gate: str
    profile: str
    case_id: str
    doctrine_ref: str
    source_class: str
    expected: str
    actual_cog_decision: str
    cog_provenance: str
    cognized_asof_verified: bool
    independent_witness: bool
    negative_no_trade_case: bool
    source_conflict_noted: bool = False


@dataclass(frozen=True, slots=True)
class SemanticAssessment:
    gate: str
    profile: str
    case_id: str
    state: SemanticState
    reason: str
    method_certified: bool = False
    cognition_certified: bool = False
    trader_certified: bool = False
    execution_authorized: bool = False


def inspect_semantic_case(case: SemanticCase) -> SemanticAssessment:
    """Fail closed on profile leakage, absent doctrine, unknown clock or fake COG."""
    if case.profile not in PROFILES or case.gate not in GATES:
        raise ValueError("UNKNOWN_PROFILE_OR_GATE")
    if not case.case_id or not case.doctrine_ref:
        raise ValueError("NO_VERSIONED_CASE_OR_DOCTRINE_PROVENANCE")
    if case.expected not in DECISIONS or case.actual_cog_decision not in DECISIONS:
        raise ValueError("UNKNOWN_DECISION_TOKEN")
    if case.source_class not in {SOURCE_AUTHOR, SOURCE_QORE, SOURCE_AMBIGUOUS}:
        raise ValueError("UNKNOWN_SOURCE_CLASS")

    def result(state: SemanticState, why: str) -> SemanticAssessment:
        return SemanticAssessment(case.gate, case.profile, case.case_id, state, why)

    if case.source_class == SOURCE_QORE and case.profile != PROFILE_QORE:
        return result(
            SemanticState.PROFILE_CONTAMINATION,
            "QORE_PROXY_CANNOT_BE_AUTHORIAL_ICT_OR_TTRADES_PROOF",
        )
    if case.source_class == SOURCE_AUTHOR and case.profile == PROFILE_QORE:
        return result(
            SemanticState.PROFILE_CONTAMINATION,
            "QORE_G3_IS_NOT_THE_ORIGINAL_AUTHORS_METHOD",
        )
    if case.source_class == SOURCE_AMBIGUOUS or case.source_conflict_noted:
        return result(SemanticState.UNKNOWN_SOURCE, "DOCTRINE_NOT_DETERMINED")
    if case.cog_provenance != COG_NATIVE:
        return result(SemanticState.NOT_AUTHENTIC_COG, "SYNTHETIC_DTO_IS_NOT_COG")
    if not case.cognized_asof_verified or not case.independent_witness:
        return result(
            SemanticState.PENDING_CAUSAL_WITNESS,
            "NATIVE_COG_OR_SOURCE_ASOF_INSUFFICIENTLY_ATTESTED",
        )
    if case.negative_no_trade_case and case.expected not in NO_TRADE:
        raise ValueError("NEGATIVE_CASE_EXPECTED_MUST_BE_NONTRADE")
    if case.expected != case.actual_cog_decision:
        return result(
            SemanticState.CONTRADICTED,
            "REAL_COG_DISAGREED_WITH_SOURCE_EXPECTATION",
        )
    if case.gate == "M6":
        # A DTO/case cannot authenticate independent COG/OPS signers.
        return result(
            SemanticState.PENDING_INDEPENDENT_REVIEW,
            "REAL_COG_OPS_SIGNERS_REQUIRE_EXTERNAL_AUTHENTICATION",
        )
    return result(
        SemanticState.CONFIRMED_IN_SCOPE,
        "ONE_CAUSAL_PROFILE_MATCH_NOT_A_FULL_METHOD_CERTIFICATE",
    )


def dossier_verdict(
    cases: tuple[SemanticCase, ...],
) -> tuple[SemanticAssessment, ...]:
    """Report per-case truth, never synthesize a global certificate from a count.

    Original author teaching and negative no-trade boundaries require real
    independent review beyond programmatic checks.
    """
    return tuple(inspect_semantic_case(case) for case in cases)


# Deliberately no PnL, sizing, win-rate, PF/Sharpe/Sortino/DD or frequency input.
# Deliberately no method_certify() or promote_to_live() function.
