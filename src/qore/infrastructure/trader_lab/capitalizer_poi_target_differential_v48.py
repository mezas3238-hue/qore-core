"""V48 POI and target differential audit.

This audit separates source concepts from QORE disambiguation policy. It preserves
consumed V47 evidence and does not choose a new target policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_POI_TARGET_DIFFERENTIAL"


class V48POITargetStatus(StrEnum):
    SOURCE_GAP = "SOURCE_GAP"
    QORE_OVERCONSTRAINT = "QORE_OVERCONSTRAINT"
    SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
    REQUIRES_ROUTE_POLICY = "REQUIRES_ROUTE_POLICY"


@dataclass(frozen=True, slots=True)
class V48POITargetFinding:
    finding_id: str
    status: V48POITargetStatus
    current_behavior: str
    source_behavior: str
    source_url: str
    consumed_run_id: int | None = None
    affected_count: int | None = None
    denominator: int | None = None

    def __post_init__(self) -> None:
        if not self.finding_id or self.finding_id != self.finding_id.upper():
            raise ValueError("finding_id must be non-empty uppercase")
        if not self.source_url.startswith("https://"):
            raise ValueError("finding requires source URL")
        if (self.affected_count is None) != (self.denominator is None):
            raise ValueError("affected_count and denominator must be supplied together")
        if self.affected_count is not None and self.denominator is not None:
            if not 0 <= self.affected_count <= self.denominator:
                raise ValueError("invalid affected population")


FINDINGS: tuple[V48POITargetFinding, ...] = (
    V48POITargetFinding(
        "POI_CISD_FALLBACK_MISSING_FROM_V2",
        V48POITargetStatus.SOURCE_GAP,
        (
            "capitalizer_source_poi_v2 detects FVG and swing-high/low POIs only; CISD is "
            "not represented as the final POI fallback."
        ),
        (
            "TTrades 2026 POI framework uses FVG first, then swing high/low, then CISD "
            "as the final point-of-interest fallback when earlier POIs are absent."
        ),
        "https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/",
    ),
    V48POITargetFinding(
        "POI_HIERARCHY_FLATTENED_TO_ANY_INTERACTION",
        V48POITargetStatus.REQUIRES_ROUTE_POLICY,
        (
            "capitalizer_source_poi_v2 exposes any_source_poi_interaction() over the POI set "
            "without encoding the newer TTrades priority/fallback order."
        ),
        (
            "TTrades defines an ordered search from protected swing toward current range: "
            "FVG first; if absent, swing; if absent, CISD."
        ),
        "https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/",
    ),
    V48POITargetFinding(
        "TARGET_EXACTLY_ONE_PRICE_AND_KIND_REQUIRED",
        V48POITargetStatus.QORE_OVERCONSTRAINT,
        (
            "V46/V47 resolve_structural_target() resolves only when all eligible causal targets "
            "collapse to exactly one price and one target kind; multiple distinct valid targets "
            "fail closed as MULTIPLE_STRUCTURAL_TARGETS_REVIEW_REQUIRED."
        ),
        (
            "TTrades defines targets from higher-timeframe structure/untouched prior highs or "
            "lows. The reviewed source does not state that only one structural target may exist."
        ),
        "https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/",
        consumed_run_id=36615057309,
        affected_count=465,
        denominator=487,
    ),
    V48POITargetFinding(
        "TARGET_UNTOUCHED_HTF_STRUCTURE",
        V48POITargetStatus.SOURCE_SUPPORTED,
        (
            "Current target candidates preserve causal known_at timestamps and require "
            "directionally valid untouched HTF structure."
        ),
        (
            "TTrades uses higher-timeframe untouched highs/lows and previous candle highs/lows "
            "as structural objectives; levels already taken are invalid."
        ),
        "https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/",
    ),
    V48POITargetFinding(
        "EVENT_SPECIFIC_BOUNDARY_RECOVERED_POPULATION",
        V48POITargetStatus.REQUIRES_ROUTE_POLICY,
        (
            "Consumed V47 diagnostic recovered an event-specific opposite-boundary identity "
            "for 368 of 487 H1/M15 events instead of demanding a globally unique target."
        ),
        (
            "This is consumed diagnostic evidence only; V48 must still prove each route's target "
            "identity from source before using event-specific boundaries productively."
        ),
        "https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/",
        consumed_run_id=36616856631,
        affected_count=368,
        denominator=487,
    ),
)


@dataclass(frozen=True, slots=True)
class V48POITargetDifferential:
    identity: str = IDENTITY
    findings: tuple[V48POITargetFinding, ...] = FINDINGS
    new_target_selector_chosen: bool = False
    nearest_target_assumed: bool = False
    rr_target_assumed: bool = False
    outcome_ranked_target_allowed: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 POI/target differential identity is frozen")
        if (
            self.new_target_selector_chosen
            or self.nearest_target_assumed
            or self.rr_target_assumed
            or self.outcome_ranked_target_allowed
        ):
            raise ValueError("V48 differential cannot invent target selection policy")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("POI/target differential is pre-economic")


V48_POI_TARGET_DIFFERENTIAL = V48POITargetDifferential()
