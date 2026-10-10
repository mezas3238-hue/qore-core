"""V48 source-rule ledger and differential-audit contract for Capitalizer.

This module exists to prevent a repeated category error: QORE operationalization,
interpretation, context, and alternative execution techniques may not be silently
promoted into one universal source-mandatory AND gate.

V48 is pre-economic research. It grants no certification, execution, sizing, merge,
DEMO, LIVE, VPS, production, or real-capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_SOURCE_RULE_LEDGER_AND_DIFFERENTIAL_AUDIT"


class V48EvidenceClass(StrEnum):
    SOURCE_EXPLICIT = "SOURCE_EXPLICIT"
    SOURCE_STRONGLY_IMPLIED = "SOURCE_STRONGLY_IMPLIED"
    INTERPRETATION = "INTERPRETATION"
    QORE_ENGINEERING_RULE = "QORE_ENGINEERING_RULE"
    UNRESOLVED = "UNRESOLVED"


class V48SemanticRole(StrEnum):
    CONTEXT = "CONTEXT"
    REQUIRED_SEQUENCE = "REQUIRED_SEQUENCE"
    SESSION_ROUTE = "SESSION_ROUTE"
    ALTERNATIVE_ROUTE = "ALTERNATIVE_ROUTE"
    EXECUTION_LAYER = "EXECUTION_LAYER"
    EXECUTION_OPTION_FAMILY = "EXECUTION_OPTION_FAMILY"
    TARGET_CONTEXT = "TARGET_CONTEXT"
    UNRESOLVED = "UNRESOLVED"


class V48MismatchStatus(StrEnum):
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SOURCE_SUPPORT_NOT_ESTABLISHED = "SOURCE_SUPPORT_NOT_ESTABLISHED"
    REQUIRES_SOURCE_RESOLUTION = "REQUIRES_SOURCE_RESOLUTION"


@dataclass(frozen=True, slots=True)
class V48SourceRule:
    rule_id: str
    source_family: str
    source_url: str
    claim: str
    evidence_class: V48EvidenceClass
    semantic_role: V48SemanticRole
    universal_hard_gate_supported: bool

    def __post_init__(self) -> None:
        if not self.rule_id or self.rule_id != self.rule_id.upper():
            raise ValueError("V48 rule_id must be non-empty uppercase")
        if not self.source_url.startswith("https://"):
            raise ValueError("V48 source rule requires an https source URL")
        if not self.claim:
            raise ValueError("V48 source rule requires an explicit claim")
        if self.evidence_class in {
            V48EvidenceClass.INTERPRETATION,
            V48EvidenceClass.QORE_ENGINEERING_RULE,
            V48EvidenceClass.UNRESOLVED,
        } and self.universal_hard_gate_supported:
            raise ValueError(
                "interpretation/QORE/unresolved evidence cannot become a universal hard gate"
            )


SOURCE_RULES: tuple[V48SourceRule, ...] = (
    V48SourceRule(
        rule_id="TTRADES_SCALPING_MODEL_TOP_DOWN_CONTEXT",
        source_family="TTRADES",
        source_url="https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",
        claim=(
            "The scalping lesson describes Daily context, Hourly scalping bias, "
            "Fifteen-minute swing structure, and One-minute execution."
        ),
        evidence_class=V48EvidenceClass.SOURCE_EXPLICIT,
        semantic_role=V48SemanticRole.EXECUTION_LAYER,
        universal_hard_gate_supported=False,
    ),
    V48SourceRule(
        rule_id="TTRADES_M1_IS_EXECUTION_NOT_PRIMARY_DECISION_LAYER",
        source_family="TTRADES",
        source_url="https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",
        claim=(
            "The source states that the one-minute chart is where the trade is executed, "
            "not where the decision is made; the narrative should already be clear."
        ),
        evidence_class=V48EvidenceClass.SOURCE_EXPLICIT,
        semantic_role=V48SemanticRole.EXECUTION_LAYER,
        universal_hard_gate_supported=False,
    ),
    V48SourceRule(
        rule_id="TTRADES_M1_CONTINUATION_BEHAVIOR_FAMILY_NOT_PROVEN_AND",
        source_family="TTRADES",
        source_url="https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/",
        claim=(
            "The M1 entry section lists continuation behavior such as FVG interaction, "
            "CISD, and protected-swing formation. The source does not establish in that "
            "lesson that MSS AND FVG AND OB AND CISD must all be independently mandatory."
        ),
        evidence_class=V48EvidenceClass.SOURCE_STRONGLY_IMPLIED,
        semantic_role=V48SemanticRole.EXECUTION_OPTION_FAMILY,
        universal_hard_gate_supported=False,
    ),
    V48SourceRule(
        rule_id="TTRADES_ASIA_HAS_TWO_PRIMARY_EXECUTION_ROUTES",
        source_family="TTRADES",
        source_url="https://ttrades.com/how-to-trade-asia-using-the-ttrades-fractal-model/",
        claim=(
            "The Asia lesson explicitly defines two primary approaches: a positional "
            "entry when the higher-timeframe framework/protected swing is already in "
            "place, OR a 4H Candle-2 plus 15M fractal confirmation route."
        ),
        evidence_class=V48EvidenceClass.SOURCE_EXPLICIT,
        semantic_role=V48SemanticRole.ALTERNATIVE_ROUTE,
        universal_hard_gate_supported=False,
    ),
    V48SourceRule(
        rule_id="TTRADES_LONDON_DAILY_4H_15M_ROUTE",
        source_family="TTRADES",
        source_url="https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/",
        claim=(
            "The London lesson uses Daily bias, 4H wick/swing structure, and 15M "
            "protected-swing/CISD confirmation; it does not define H1-M15-M1 as a "
            "universal London requirement."
        ),
        evidence_class=V48EvidenceClass.SOURCE_EXPLICIT,
        semantic_role=V48SemanticRole.SESSION_ROUTE,
        universal_hard_gate_supported=False,
    ),
    V48SourceRule(
        rule_id="TTRADES_NEW_YORK_ENTRY_MODELS_ARE_PLURAL",
        source_family="TTRADES",
        source_url="https://ttrades.com/daily-profile-understanding-the-new-york-manipulation/",
        claim=(
            "The New York manipulation lesson permits entry refinement using FVGs, "
            "Order Blocks, or the trader's choice of an entry model after the sweep/CISD."
        ),
        evidence_class=V48EvidenceClass.SOURCE_EXPLICIT,
        semantic_role=V48SemanticRole.EXECUTION_OPTION_FAMILY,
        universal_hard_gate_supported=False,
    ),
    V48SourceRule(
        rule_id="TTRADES_FTM_CORE_FAILURE_THEN_CONTINUATION",
        source_family="TTRADES",
        source_url="https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/",
        claim=(
            "FTM is defined by a taken high/low failing to form the expected reversal, "
            "followed by continuation structure in alignment with higher-timeframe bias."
        ),
        evidence_class=V48EvidenceClass.SOURCE_EXPLICIT,
        semantic_role=V48SemanticRole.REQUIRED_SEQUENCE,
        universal_hard_gate_supported=True,
    ),
    V48SourceRule(
        rule_id="TTRADES_FTM_REQUIRES_HTF_REASON_AND_LTF_CONFIRMATION",
        source_family="TTRADES",
        source_url="https://ttrades.com/how-to-trade-breakouts-failure-to-manipulate/",
        claim=(
            "The source says FTM is not a standalone model: HTF provides the reason/bias "
            "and LTF structure confirms the new protected swing before participation."
        ),
        evidence_class=V48EvidenceClass.SOURCE_EXPLICIT,
        semantic_role=V48SemanticRole.CONTEXT,
        universal_hard_gate_supported=True,
    ),
    V48SourceRule(
        rule_id="ICT_2022_PRIMARY_SEQUENCE_EXACT_V48_BINDING_PENDING",
        source_family="ICT",
        source_url="https://www.youtube.com/watch?v=tmeCWULSTHc",
        claim=(
            "ICT 2022 Mentorship is retained as primary-source material, but V48 has not "
            "yet completed exact timestamp-level binding of every QORE ICT requirement."
        ),
        evidence_class=V48EvidenceClass.UNRESOLVED,
        semantic_role=V48SemanticRole.UNRESOLVED,
        universal_hard_gate_supported=False,
    ),
)


@dataclass(frozen=True, slots=True)
class V48QoreMismatch:
    mismatch_id: str
    current_file: str
    current_behavior: str
    status: V48MismatchStatus
    source_rule_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.mismatch_id or self.mismatch_id != self.mismatch_id.upper():
            raise ValueError("V48 mismatch_id must be non-empty uppercase")
        if not self.current_file.startswith("src/"):
            raise ValueError("V48 mismatch must point to current source code")
        if not self.current_behavior:
            raise ValueError("V48 mismatch requires current behavior")
        if not self.source_rule_ids:
            raise ValueError("V48 mismatch requires source-rule provenance")


QORE_DIFFERENTIAL_MISMATCHES: tuple[V48QoreMismatch, ...] = (
    V48QoreMismatch(
        mismatch_id="UNIVERSAL_H1_M15_M1_SESSION_GRAMMAR",
        current_file=(
            "src/qore/infrastructure/trader_lab/"
            "capitalizer_source_strategy_grammar_v2.py"
        ),
        current_behavior=(
            "The module docstring and FRACTAL route encode H1 -> M15 -> M1 as the "
            "TTrades scalp sequence without session-specific route choice."
        ),
        status=V48MismatchStatus.SOURCE_CONFLICT,
        source_rule_ids=(
            "TTRADES_ASIA_HAS_TWO_PRIMARY_EXECUTION_ROUTES",
            "TTRADES_LONDON_DAILY_4H_15M_ROUTE",
        ),
    ),
    V48QoreMismatch(
        mismatch_id="M1_PROMOTED_TO_SECOND_DECISION_SYSTEM",
        current_file=(
            "src/qore/infrastructure/trader_lab/"
            "capitalizer_dual_source_entry_acceptance_v1.py"
        ),
        current_behavior=(
            "Acceptance requires an independently complete M1 MSS + FVG + Order Block "
            "triad in addition to upstream ICT and TTrades confirmations."
        ),
        status=V48MismatchStatus.SOURCE_SUPPORT_NOT_ESTABLISHED,
        source_rule_ids=(
            "TTRADES_M1_IS_EXECUTION_NOT_PRIMARY_DECISION_LAYER",
            "TTRADES_M1_CONTINUATION_BEHAVIOR_FAMILY_NOT_PROVEN_AND",
        ),
    ),
    V48QoreMismatch(
        mismatch_id="DUAL_SOURCE_SUPERINTERSECTION_ALL_MANDATORY",
        current_file=(
            "src/qore/infrastructure/trader_lab/"
            "capitalizer_dual_source_entry_acceptance_v1.py"
        ),
        current_behavior=(
            "The gate requires every ICT field, every TTrades field, wick formation, "
            "and the complete M1 triad simultaneously before acceptance."
        ),
        status=V48MismatchStatus.SOURCE_SUPPORT_NOT_ESTABLISHED,
        source_rule_ids=(
            "TTRADES_M1_CONTINUATION_BEHAVIOR_FAMILY_NOT_PROVEN_AND",
            "TTRADES_NEW_YORK_ENTRY_MODELS_ARE_PLURAL",
        ),
    ),
    V48QoreMismatch(
        mismatch_id="FTM_CONTINUATION_OVERCOMPOSED_AFTER_CORE_IDENTITY",
        current_file=(
            "src/qore/infrastructure/trader_lab/"
            "capitalizer_dual_source_entry_acceptance_v1.py"
        ),
        current_behavior=(
            "The generic dual-source acceptance layer can force FTM through the same "
            "full downstream confirmation inventory instead of preserving only the "
            "route-specific failure-then-continuation thesis plus a valid execution model."
        ),
        status=V48MismatchStatus.REQUIRES_SOURCE_RESOLUTION,
        source_rule_ids=(
            "TTRADES_FTM_CORE_FAILURE_THEN_CONTINUATION",
            "TTRADES_FTM_REQUIRES_HTF_REASON_AND_LTF_CONFIRMATION",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class V48DifferentialAuditState:
    identity: str = IDENTITY
    source_rules: tuple[V48SourceRule, ...] = SOURCE_RULES
    mismatches: tuple[V48QoreMismatch, ...] = QORE_DIFFERENTIAL_MISMATCHES
    economics_authorized: bool = False
    fresh_holdout_authorized: bool = False
    certification_authorized: bool = False
    deployment_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 differential audit identity is frozen")
        rule_ids = tuple(item.rule_id for item in self.source_rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("V48 source rule IDs must be unique")
        known = set(rule_ids)
        for mismatch in self.mismatches:
            missing = set(mismatch.source_rule_ids) - known
            if missing:
                raise ValueError(f"V48 mismatch references unknown rules: {sorted(missing)}")
        if (
            self.economics_authorized
            or self.fresh_holdout_authorized
            or self.certification_authorized
            or self.deployment_authorized
        ):
            raise ValueError("V48-A source reconstruction is pre-economic and research-only")


V48_DIFFERENTIAL_AUDIT = V48DifferentialAuditState()
