"""Dual-source fidelity audit for QORE Capitalizer.

Authority order:
1. ICT / Michael J. Huddleston = original primary source.
2. TTrades = secondary refinement/specialization where it is compatible with ICT.
3. QORE = explicit operationalization only where the source leaves an implementation gap.

This audit does not assume that TTrades terminology (for example protected swings or
CISD grammar) was coined by ICT. It checks whether the refinement preserves the original
ICT structural intent and whether QORE has silently promoted a refinement into an
original-source claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_source_faithful_trader_design_v2 import (
    FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_review_v2 import (
    FROZEN_SOURCE_STRATEGY_REVIEW,
)

IDENTITY = "QORE_CAPITALIZER_ICT_TTRADES_DUAL_SOURCE_FIDELITY_AUDIT_V1"


class CapitalizerSourceAuthorityTier(StrEnum):
    ICT_ORIGINAL_PRIMARY = "ICT_ORIGINAL_PRIMARY"
    TTRADES_SECONDARY_REFINEMENT = "TTRADES_SECONDARY_REFINEMENT"
    QORE_OPERATIONALIZATION = "QORE_OPERATIONALIZATION"


class CapitalizerDualSourceStatus(StrEnum):
    ALIGNED = "ALIGNED"
    TTRADES_REFINEMENT_COMPATIBLE = "TTRADES_REFINEMENT_COMPATIBLE"
    ROUTE_SPECIFIC_VARIANCE = "ROUTE_SPECIFIC_VARIANCE"
    QORE_PROXY_GAP = "QORE_PROXY_GAP"


@dataclass(frozen=True, slots=True)
class CapitalizerDualSourceCheck:
    component: str
    ict_fact_ids: tuple[str, ...]
    ttrades_fact_ids: tuple[str, ...]
    trader_rule_ids: tuple[str, ...]
    status: CapitalizerDualSourceStatus
    conclusion: str


CHECKS: tuple[CapitalizerDualSourceCheck, ...] = (
    CapitalizerDualSourceCheck(
        component="HIGHER_TIMEFRAME_DIRECTION",
        ict_fact_ids=("ICT_DAILY_BIAS_PRECEDES_SCALP_EXECUTION",),
        ttrades_fact_ids=("TTRADES_DAILY_BIAS_CLOSURE_BEFORE_INTRADAY_EXECUTION",),
        trader_rule_ids=("HTF_NARRATIVE_PRECEDES_ENTRY",),
        status=CapitalizerDualSourceStatus.ALIGNED,
        conclusion=(
            "ICT is the primary directional authority. TTrades adds a mechanical C2/C3 "
            "closure grammar without replacing the higher-timeframe narrative."
        ),
    ),
    CapitalizerDualSourceCheck(
        component="SESSION_CONTEXT",
        ict_fact_ids=(
            "ICT_ASIAN_OPEN_RELATIVE_TWO_HOUR_WINDOW",
            "ICT_LONDON_KILLZONE_0200_0500_NY",
            "ICT_NEW_YORK_KILLZONE_0700_0900_NY",
        ),
        ttrades_fact_ids=(),
        trader_rule_ids=("SOURCE_SESSION_CONTEXT_REQUIRED",),
        status=CapitalizerDualSourceStatus.ALIGNED,
        conclusion=(
            "Session eligibility remains sourced from ICT; QORE broad session buckets must "
            "not be relabeled as ICT kill zones."
        ),
    ),
    CapitalizerDualSourceCheck(
        component="LIQUIDITY_OBJECTIVE",
        ict_fact_ids=("ICT_LIQUIDITY_TARGETS_RECENT_DAILY_HIGHS_LOWS",),
        ttrades_fact_ids=("TTRADES_TARGET_USES_HIGHER_TIMEFRAME_OBJECTIVE",),
        trader_rule_ids=(
            "STRUCTURAL_LIQUIDITY_DESTINATION_REQUIRED",
            "TARGET_AT_STRUCTURAL_HTF_OBJECTIVE",
        ),
        status=CapitalizerDualSourceStatus.ALIGNED,
        conclusion=(
            "Both sources require a structural/higher-timeframe objective rather than an "
            "arbitrary scalp target."
        ),
    ),
    CapitalizerDualSourceCheck(
        component="LOWER_TIMEFRAME_EXECUTION",
        ict_fact_ids=("ICT_LOWER_TIMEFRAME_REFINES_STOP_WITH_SAME_OBJECTIVE",),
        ttrades_fact_ids=(
            "TTRADES_SCALP_TOP_DOWN_H1_M15_M1",
            "TTRADES_M15_SWING_THEN_M1_CONTINUATION",
        ),
        trader_rule_ids=("FRACTAL_ROUTE_H1_M15_M1",),
        status=CapitalizerDualSourceStatus.TTRADES_REFINEMENT_COMPATIBLE,
        conclusion=(
            "ICT supports lower-timeframe refinement of a higher-timeframe trade idea. "
            "TTrades formalizes that refinement as H1 bias, M15 swing structure and M1 "
            "execution. The H1/M15/M1 grammar must be attributed to TTrades, not ICT."
        ),
    ),
    CapitalizerDualSourceCheck(
        component="STOP_INVALIDATION_ANCHOR",
        ict_fact_ids=("ICT_STRUCTURAL_STOP_USES_KEY_INVALIDATION_EXTREME",),
        ttrades_fact_ids=(
            "TTRADES_PROTECTED_SWING_STOP",
            "TTRADES_PROTECTED_SWING_IS_INVALIDATION_ANCHOR",
        ),
        trader_rule_ids=(
            "PROTECTED_SWING_DEFINES_INVALIDATION",
            "STOP_AT_LOGICAL_PROTECTED_SWING",
        ),
        status=CapitalizerDualSourceStatus.TTRADES_REFINEMENT_COMPATIBLE,
        conclusion=(
            "ICT and TTrades agree on structural invalidation rather than arbitrary fixed "
            "distance. TTrades' protected swing is a compatible refinement of the invalidating "
            "swing concept, but its terminology and confirmation grammar remain TTrades-specific."
        ),
    ),
    CapitalizerDualSourceCheck(
        component="EXACT_INITIAL_STOP_PRICE",
        ict_fact_ids=("ICT_STRUCTURAL_STOP_USES_KEY_INVALIDATION_EXTREME",),
        ttrades_fact_ids=("TTRADES_PROTECTED_SWING_STOP",),
        trader_rule_ids=("STOP_AT_LOGICAL_PROTECTED_SWING",),
        status=CapitalizerDualSourceStatus.ROUTE_SPECIFIC_VARIANCE,
        conclusion=(
            "The sources agree on the structural anchor but not on one universal execution "
            "offset. ICT ATM examples use stop placement beyond the key/rejection extreme and "
            "show lower-timeframe refinement; TTrades gives the protected high/low as the "
            "default while also documenting beyond/body alternatives. QORE must therefore keep "
            "the exact stop expression route-specific instead of claiming one universal rule."
        ),
    ),
    CapitalizerDualSourceCheck(
        component="STOP_MANAGEMENT",
        ict_fact_ids=("ICT_PROTECTIVE_STOP_MOVES_ONLY_AFTER_STRUCTURE_EARNS_IT",),
        ttrades_fact_ids=("TTRADES_PROTECTED_SWING_STOP",),
        trader_rule_ids=("STOP_AT_LOGICAL_PROTECTED_SWING",),
        status=CapitalizerDualSourceStatus.ALIGNED,
        conclusion=(
            "The trader does not authorize arbitrary widening or premature trailing. Advanced "
            "management remains a later lab, which preserves both sources' structural intent."
        ),
    ),
    CapitalizerDualSourceCheck(
        component="CURRENT_ECONOMIC_REPLAY",
        ict_fact_ids=(
            "ICT_LOWER_TIMEFRAME_REFINES_STOP_WITH_SAME_OBJECTIVE",
            "ICT_STRUCTURAL_STOP_USES_KEY_INVALIDATION_EXTREME",
        ),
        ttrades_fact_ids=(
            "TTRADES_SCALP_TOP_DOWN_H1_M15_M1",
            "TTRADES_PROTECTED_SWING_STOP",
        ),
        trader_rule_ids=("FRACTAL_ROUTE_H1_M15_M1", "STOP_AT_LOGICAL_PROTECTED_SWING"),
        status=CapitalizerDualSourceStatus.QORE_PROXY_GAP,
        conclusion=(
            "The current protected-swing corrected replay is still an M5 surrogate. It cannot "
            "establish full ICT+TTrades fidelity because the source execution/refinement layer "
            "requires native finer evidence, including M1 for the TTrades scalp route."
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class CapitalizerDualSourceFidelityAudit:
    identity: str = IDENTITY
    authority_order: tuple[CapitalizerSourceAuthorityTier, ...] = (
        CapitalizerSourceAuthorityTier.ICT_ORIGINAL_PRIMARY,
        CapitalizerSourceAuthorityTier.TTRADES_SECONDARY_REFINEMENT,
        CapitalizerSourceAuthorityTier.QORE_OPERATIONALIZATION,
    )
    checks: tuple[CapitalizerDualSourceCheck, ...] = CHECKS
    ict_is_original_primary_source: bool = True
    ttrades_may_override_ict: bool = False
    qore_may_masquerade_as_author: bool = False
    universal_stop_offset_supported: bool = False
    current_stop_anchor_structurally_compatible: bool = True
    current_exact_stop_expression_universally_dual_source_faithful: bool = False
    native_m1_required_for_final_fidelity: bool = True
    native_m1_present: bool = False
    replay_may_claim_full_source_fidelity: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        fact_ids = {item.fact_id for item in FROZEN_SOURCE_STRATEGY_REVIEW.facts}
        rule_ids = {item.rule_id for item in FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN.rules}
        for check in self.checks:
            missing_facts = set((*check.ict_fact_ids, *check.ttrades_fact_ids)) - fact_ids
            missing_rules = set(check.trader_rule_ids) - rule_ids
            if missing_facts:
                raise ValueError(f"dual-source audit missing facts: {sorted(missing_facts)}")
            if missing_rules:
                raise ValueError(f"dual-source audit missing rules: {sorted(missing_rules)}")
        if self.ttrades_may_override_ict or self.qore_may_masquerade_as_author:
            raise ValueError("dual-source authority hierarchy cannot be inverted")
        if self.universal_stop_offset_supported:
            raise ValueError("reviewed sources do not support one universal stop offset")
        if (
            self.native_m1_present
            or self.replay_may_claim_full_source_fidelity
            or self.rule_promotion_allowed
            or self.economic_candidate
            or self.trader_certified
        ):
            raise ValueError("dual-source audit cannot promote research state")


FROZEN_DUAL_SOURCE_FIDELITY_AUDIT = CapitalizerDualSourceFidelityAudit()
