"""Source-faithful full trader design contract for QORE Capitalizer V2.

This module describes the complete methodology boundary that must exist before integrated
nine-market replay. It separates ICT/TTrades author-supported behavior from QORE portfolio
governance. It contains no economic optimization and grants no execution/capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_review_v2 import (
    FROZEN_SOURCE_STRATEGY_REVIEW,
    CapitalizerSourceFactType,
)

SOURCE_FAITHFUL_TRADER_DESIGN_ID = "QORE_CAPITALIZER_SOURCE_FAITHFUL_TRADER_DESIGN_V2"


class CapitalizerTraderDesignAuthority(StrEnum):
    ICT = "ICT"
    TTRADES = "TTRADES"
    ICT_TTRADES = "ICT_TTRADES"
    QORE = "QORE"


class CapitalizerTraderDesignComponent(StrEnum):
    SESSION_CONTEXT = "SESSION_CONTEXT"
    HIGHER_TIMEFRAME_NARRATIVE = "HIGHER_TIMEFRAME_NARRATIVE"
    LIQUIDITY_OBJECTIVE = "LIQUIDITY_OBJECTIVE"
    FRACTAL_SCALP_ENTRY_ROUTE = "FRACTAL_SCALP_ENTRY_ROUTE"
    FAILURE_TO_MANIPULATE_ROUTE = "FAILURE_TO_MANIPULATE_ROUTE"
    PROTECTED_SWING_INVALIDATION = "PROTECTED_SWING_INVALIDATION"
    STOP_PLACEMENT = "STOP_PLACEMENT"
    TARGET_PLACEMENT = "TARGET_PLACEMENT"
    WAIT_NO_TRADE = "WAIT_NO_TRADE"
    COGNITIVE_HANDOFF = "COGNITIVE_HANDOFF"
    QORE_RISK_HANDOFF = "QORE_RISK_HANDOFF"
    PORTFOLIO_GOVERNANCE = "PORTFOLIO_GOVERNANCE"


@dataclass(frozen=True, slots=True)
class CapitalizerTraderDesignRule:
    rule_id: str
    component: CapitalizerTraderDesignComponent
    authority: CapitalizerTraderDesignAuthority
    statement: str
    source_fact_ids: tuple[str, ...] = ()
    qore_operationalization: bool = False

    def __post_init__(self) -> None:
        if not self.rule_id or self.rule_id != self.rule_id.upper():
            raise ValueError("trader design rule_id must be non-empty uppercase")
        if not self.statement:
            raise ValueError("trader design rule requires statement")
        if self.authority is CapitalizerTraderDesignAuthority.QORE:
            if not self.qore_operationalization:
                raise ValueError("QORE trader design rule must declare operationalization")
            if self.source_fact_ids:
                raise ValueError("QORE governance cannot masquerade as author-sourced")
        else:
            if self.qore_operationalization:
                raise ValueError("author-supported trader rule cannot be tagged QORE")
            if not self.source_fact_ids:
                raise ValueError("author-supported trader rule requires source fact provenance")


TRADER_DESIGN_RULES: tuple[CapitalizerTraderDesignRule, ...] = (
    CapitalizerTraderDesignRule(
        rule_id="SOURCE_SESSION_CONTEXT_REQUIRED",
        component=CapitalizerTraderDesignComponent.SESSION_CONTEXT,
        authority=CapitalizerTraderDesignAuthority.ICT,
        statement=(
            "The methodology is evaluated only in reviewed source session context: London and "
            "New York use their reviewed ICT kill-zone windows; Asia is resolved relative to the "
            "historical Asian Open rather than a universal fixed clock."
        ),
        source_fact_ids=(
            "ICT_ASIAN_OPEN_RELATIVE_TWO_HOUR_WINDOW",
            "ICT_LONDON_KILLZONE_0200_0500_NY",
            "ICT_NEW_YORK_KILLZONE_0700_0900_NY",
        ),
    ),
    CapitalizerTraderDesignRule(
        rule_id="HTF_NARRATIVE_PRECEDES_ENTRY",
        component=CapitalizerTraderDesignComponent.HIGHER_TIMEFRAME_NARRATIVE,
        authority=CapitalizerTraderDesignAuthority.ICT_TTRADES,
        statement=(
            "A lower-timeframe scalp cannot create its own narrative: ICT higher-timeframe/daily "
            "directional context and TTrades hourly expansion bias must precede execution."
        ),
        source_fact_ids=(
            "ICT_DAILY_BIAS_PRECEDES_SCALP_EXECUTION",
            "TTRADES_H1_EXPANSION_BIAS_C2_C3",
            "TTRADES_SCALP_TOP_DOWN_H1_M15_M1",
        ),
    ),
    CapitalizerTraderDesignRule(
        rule_id="STRUCTURAL_LIQUIDITY_DESTINATION_REQUIRED",
        component=CapitalizerTraderDesignComponent.LIQUIDITY_OBJECTIVE,
        authority=CapitalizerTraderDesignAuthority.ICT_TTRADES,
        statement=(
            "A trade requires a structural/higher-timeframe liquidity destination; recent daily "
            "highs/lows and higher-timeframe objectives are source-supported examples."
        ),
        source_fact_ids=(
            "ICT_LIQUIDITY_TARGETS_RECENT_DAILY_HIGHS_LOWS",
            "TTRADES_TARGET_USES_HIGHER_TIMEFRAME_OBJECTIVE",
        ),
    ),
    CapitalizerTraderDesignRule(
        rule_id="FRACTAL_ROUTE_H1_M15_M1",
        component=CapitalizerTraderDesignComponent.FRACTAL_SCALP_ENTRY_ROUTE,
        authority=CapitalizerTraderDesignAuthority.TTRADES,
        statement=(
            "The fractal scalp route requires confirmed hourly expansion bias, aligned M15 swing "
            "structure, then M1 continuation/confirmation; M1 is execution, not narrative."
        ),
        source_fact_ids=(
            "TTRADES_H1_EXPANSION_BIAS_C2_C3",
            "TTRADES_M15_SWING_THEN_M1_CONTINUATION",
            "TTRADES_SCALP_TOP_DOWN_H1_M15_M1",
        ),
    ),
    CapitalizerTraderDesignRule(
        rule_id="FTM_ROUTE_FAILED_REVERSAL_THEN_CONTINUATION",
        component=CapitalizerTraderDesignComponent.FAILURE_TO_MANIPULATE_ROUTE,
        authority=CapitalizerTraderDesignAuthority.TTRADES,
        statement=(
            "Failure to Manipulate requires a liquidity level to be taken, the expected reversal "
            "to fail, candle/structure confirmation, and continuation aligned with HTF reasoning."
        ),
        source_fact_ids=(
            "TTRADES_FAILURE_TO_MANIPULATE_REQUIRES_FAILED_REVERSAL",
            "TTRADES_FAILURE_TO_MANIPULATE_USES_HTF_BIAS",
            "TTRADES_WAIT_FOR_CANDLE_CLOSURE_CONFIRMATION",
        ),
    ),
    CapitalizerTraderDesignRule(
        rule_id="PROTECTED_SWING_DEFINES_INVALIDATION",
        component=CapitalizerTraderDesignComponent.PROTECTED_SWING_INVALIDATION,
        authority=CapitalizerTraderDesignAuthority.TTRADES,
        statement=(
            "The logical protected swing is the structural invalidation anchor for the scalp; "
            "a candidate without a valid protected swing is not ready for execution."
        ),
        source_fact_ids=("TTRADES_PROTECTED_SWING_STOP",),
    ),
    CapitalizerTraderDesignRule(
        rule_id="STOP_AT_LOGICAL_PROTECTED_SWING",
        component=CapitalizerTraderDesignComponent.STOP_PLACEMENT,
        authority=CapitalizerTraderDesignAuthority.TTRADES,
        statement="Initial stop placement is anchored to the logical protected swing.",
        source_fact_ids=("TTRADES_PROTECTED_SWING_STOP",),
    ),
    CapitalizerTraderDesignRule(
        rule_id="TARGET_AT_STRUCTURAL_HTF_OBJECTIVE",
        component=CapitalizerTraderDesignComponent.TARGET_PLACEMENT,
        authority=CapitalizerTraderDesignAuthority.ICT_TTRADES,
        statement=(
            "Initial target must be a structural/higher-timeframe objective, not an arbitrary "
            "fixed scalp exit invented from backtest outcomes."
        ),
        source_fact_ids=(
            "ICT_LIQUIDITY_TARGETS_RECENT_DAILY_HIGHS_LOWS",
            "TTRADES_TARGET_USES_HIGHER_TIMEFRAME_OBJECTIVE",
        ),
    ),
    CapitalizerTraderDesignRule(
        rule_id="WAIT_WHILE_SOURCE_SEQUENCE_INCOMPLETE",
        component=CapitalizerTraderDesignComponent.WAIT_NO_TRADE,
        authority=CapitalizerTraderDesignAuthority.QORE,
        statement=(
            "QORE operationalizes missing source prerequisites as WAIT and contradictory/invalid "
            "source prerequisites as REJECT; absence of confirmation is never filled by guessing."
        ),
        qore_operationalization=True,
    ),
    CapitalizerTraderDesignRule(
        rule_id="COGNITIVE_PASS_REQUIRED_BEFORE_SOURCE_STRATEGY",
        component=CapitalizerTraderDesignComponent.COGNITIVE_HANDOFF,
        authority=CapitalizerTraderDesignAuthority.QORE,
        statement=(
            "Only a Cognitive V2 PASS_TO_STRATEGY candidate may enter the source-faithful "
            "methodology grammar."
        ),
        qore_operationalization=True,
    ),
    CapitalizerTraderDesignRule(
        rule_id="SOURCE_ELIGIBLE_STOPS_BEFORE_QORE_RISK",
        component=CapitalizerTraderDesignComponent.QORE_RISK_HANDOFF,
        authority=CapitalizerTraderDesignAuthority.QORE,
        statement=(
            "A fully source-eligible candidate is handed to QORE Risk; methodology eligibility "
            "does not authorize execution or position sizing."
        ),
        qore_operationalization=True,
    ),
    CapitalizerTraderDesignRule(
        rule_id="MAX3_AND_NINE_MARKETS_ARE_QORE_NOT_AUTHOR",
        component=CapitalizerTraderDesignComponent.PORTFOLIO_GOVERNANCE,
        authority=CapitalizerTraderDesignAuthority.QORE,
        statement=(
            "The nine-market universe and MAX3 per session are QORE portfolio governance, never "
            "claims attributed to ICT or TTrades."
        ),
        qore_operationalization=True,
    ),
)


_REQUIRED_COMPONENTS = tuple(CapitalizerTraderDesignComponent)


@dataclass(frozen=True, slots=True)
class CapitalizerSourceFaithfulTraderDesign:
    design_id: str = SOURCE_FAITHFUL_TRADER_DESIGN_ID
    rules: tuple[CapitalizerTraderDesignRule, ...] = TRADER_DESIGN_RULES
    status: CapitalizerChainStatus = CapitalizerChainStatus.FROZEN_APT

    exact_entry_algorithms_derived_from_terminal_outcomes: bool = False
    numeric_confidence_score_used: bool = False
    arbitrary_fixed_r_target_used: bool = False
    unsourced_entry_route_allowed: bool = False
    advanced_be_trailing_zigzig_claimed_as_source: bool = False
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    ready_for_integrated_nine_market_replay: bool = True
    integrated_nine_market_replay_completed: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.design_id != SOURCE_FAITHFUL_TRADER_DESIGN_ID:
            raise ValueError("source-faithful trader design identity is frozen")
        if self.status is not CapitalizerChainStatus.FROZEN_APT:
            raise ValueError("source-faithful trader design must be FROZEN_APT")

        components = tuple(rule.component for rule in self.rules)
        if set(components) != set(_REQUIRED_COMPONENTS):
            missing = set(_REQUIRED_COMPONENTS) - set(components)
            extra = set(components) - set(_REQUIRED_COMPONENTS)
            raise ValueError(
                f"trader design component coverage mismatch: missing={missing}, extra={extra}"
            )

        reviewed = {item.fact_id: item for item in FROZEN_SOURCE_STRATEGY_REVIEW.facts}
        rule_ids: set[str] = set()
        for rule in self.rules:
            if rule.rule_id in rule_ids:
                raise ValueError("source-faithful trader design rule ids must be unique")
            rule_ids.add(rule.rule_id)
            for fact_id in rule.source_fact_ids:
                fact = reviewed.get(fact_id)
                if fact is None:
                    raise ValueError(f"trader design references unknown source fact: {fact_id}")
                if fact.fact_type is not CapitalizerSourceFactType.AUTHOR_SUPPORTED:
                    raise ValueError("author trader design rule cites non-author fact")

        if (
            self.exact_entry_algorithms_derived_from_terminal_outcomes
            or self.numeric_confidence_score_used
            or self.arbitrary_fixed_r_target_used
            or self.unsourced_entry_route_allowed
            or self.advanced_be_trailing_zigzig_claimed_as_source
        ):
            raise ValueError("source-faithful trader design contains forbidden methodology drift")
        if self.executes_trade or self.sizes_position or self.grants_capital_authority:
            raise ValueError("source-faithful trader design stops before QORE Risk/execution")
        if not self.ready_for_integrated_nine_market_replay:
            raise ValueError("complete source-faithful design must open integrated replay")
        if self.integrated_nine_market_replay_completed or self.trader_certified:
            raise ValueError("design closure cannot claim replay/certification")


FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN = CapitalizerSourceFaithfulTraderDesign()
