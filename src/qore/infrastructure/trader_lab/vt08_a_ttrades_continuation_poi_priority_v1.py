"""TTrades written POI category priority, only for continuation subphase.

Do not confuse the author-written FVG > swing high/low > CISD retest
priority with an algorithm that authenticates the actual POI. This
contract cannot authorize an entry; source-level relevance, protected
swing and unobserved candidates require independent B review.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

SOURCE = "https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/"
FAMILY = "TTRADES_PROTECTED_SWING_CONTINUATION_POI"
CATEGORIES = ("FVG", "SWING_HIGH_LOW", "CISD_RETEST")


class ReviewStatus(StrEnum):
    INCOMPLETE = "INCOMPLETE_NOT_SOURCE_COMPLETE"
    NO_POI = "NO_ELIGIBLE_POI"
    TIER_KNOWN = "AUTHOR_WRITTEN_TIER_PRIORITY_ONLY"
    AMBIGUOUS = "SAME_TIER_MULTIPLE_POIS_D"


@dataclass(frozen=True, slots=True)
class ObservedPoi:
    """Candidate location already present by cutoff; semantic proof external.

    No price/stop/target/fill, and no automatic 'relevant' selection.
    """
    poi_id: str
    category: str
    formed_at: datetime
    available_at: datetime
    bar_ids: tuple[str, ...]
    relevance_independently_checked: bool
    between_ps_and_current_range_checked: bool


@dataclass(frozen=True, slots=True)
class PoiPriorityResult:
    status: ReviewStatus
    category: str | None
    poi_id: str | None
    reason: str
    source_author_entry_complete: bool = False
    cognitive_ready: bool = False
    broker_order_authorized: bool = False


def resolve_continuation_poi_tier(
    *,
    family: str,
    observed: tuple[ObservedPoi, ...],
    as_of: datetime,
    protected_swing_authentic: bool,
    inventory_exhaustive_asof: bool,
) -> PoiPriorityResult:
    """Do not backfill later FVG or use geometry as author's judgment.

    Inventory completeness covers existence/absence of each candidate in
    this specific protected-swing -> current-range area. B must independently
    verify it from original bars, NOT by trusting these boolean flags.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if family != FAMILY:
        raise ValueError("POI priority cannot be transferred to other models")
    if type(protected_swing_authentic) is not bool or type(inventory_exhaustive_asof) is not bool:
        raise ValueError("verification flags must be exact bool")
    seen: set[str] = set()
    eligible: list[ObservedPoi] = []
    cutoff = as_of.astimezone(UTC)
    for poi in observed:
        if not poi.poi_id or poi.poi_id in seen:
            raise ValueError("candidate POI identity duplicate or empty")
        seen.add(poi.poi_id)
        if poi.category not in CATEGORIES:
            raise ValueError("unrecognized POI class")
        if not poi.bar_ids or len(set(poi.bar_ids)) != len(poi.bar_ids):
            raise ValueError("POI source bars must have unique nonempty lineage")
        if any(not x for x in poi.bar_ids):
            raise ValueError("POI empty source bar ID")
        if any(
            t.tzinfo is None or t.utcoffset() is None
            for t in (poi.formed_at, poi.available_at)
        ):
            raise ValueError("POI clocks must be timezone-aware")
        if poi.formed_at.astimezone(UTC) > poi.available_at.astimezone(UTC):
            raise ValueError("POI existence clock exceeds availability")
        if poi.available_at.astimezone(UTC) > cutoff:
            raise ValueError("future POI not observed before decision")
        if (type(poi.relevance_independently_checked) is not bool
                or type(poi.between_ps_and_current_range_checked) is not bool):
            raise ValueError("POI attestation flags must be exact bool")
        if poi.relevance_independently_checked and poi.between_ps_and_current_range_checked:
            eligible.append(poi)
    if not protected_swing_authentic or not inventory_exhaustive_asof:
        return PoiPriorityResult(
            ReviewStatus.INCOMPLETE, None, None,
            "PROTECTED_SWING_OR_POI_CENSUS_D",
        )
    if any(
        not poi.relevance_independently_checked
        or not poi.between_ps_and_current_range_checked
        for poi in observed
    ):
        return PoiPriorityResult(
            ReviewStatus.INCOMPLETE, None, None,
            "UNADJUDICATED_POI_RELEVANCE_OR_SPATIAL_CONTEXT",
        )
    if not eligible:
        return PoiPriorityResult(
            ReviewStatus.NO_POI, None, None, "ABSENCE_CONFIRMED_ASOF",
        )
    best = next(
        category for category in CATEGORIES
        if any(p.category == category for p in eligible)
    )
    same_tier = [p for p in eligible if p.category == best]
    if len(same_tier) != 1:
        return PoiPriorityResult(
            ReviewStatus.AMBIGUOUS, best, None,
            "AUTHOR_DID_NOT_SPECIFY_TIEBREAK_BETWEEN_SAME_TIER_POIS",
        )
    return PoiPriorityResult(
        ReviewStatus.TIER_KNOWN, best, same_tier[0].poi_id,
        "SOURCE_A_CATEGORY_ORDER_ONLY_EXTERNAL_SEMANTICS_REQUIRED",
    )
