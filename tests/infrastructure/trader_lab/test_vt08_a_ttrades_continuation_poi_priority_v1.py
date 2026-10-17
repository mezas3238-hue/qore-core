"""Adversarial source category priority: no conversion into real trade."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_a_ttrades_continuation_poi_priority_v1 import (
    FAMILY,
    ObservedPoi,
    ReviewStatus,
    resolve_continuation_poi_tier,
)

T = datetime(2026, 10, 15, 12, tzinfo=UTC)


def poi(kind, ident):
    return ObservedPoi(
        poi_id=ident, category=kind,
        formed_at=T-timedelta(minutes=6), available_at=T-timedelta(minutes=3),
        bar_ids=(ident+"-raw",),
        relevance_independently_checked=True,
        between_ps_and_current_range_checked=True,
    )


def choose(*items, **kw):
    return resolve_continuation_poi_tier(
        family=FAMILY,
        observed=tuple(items),
        as_of=T,
        protected_swing_authentic=kw.get("ps", True),
        inventory_exhaustive_asof=kw.get("complete", True),
    )


def test_author_fvg_first_over_swing_and_cisd_without_trade_authority():
    result=choose(poi("CISD_RETEST","c"),poi("SWING_HIGH_LOW","s"),poi("FVG","f"))
    assert result.status is ReviewStatus.TIER_KNOWN
    assert result.category == "FVG"
    assert result.poi_id == "f"
    assert not result.source_author_entry_complete
    assert not result.cognitive_ready
    assert not result.broker_order_authorized


def test_author_swing_second_if_fvg_absent():
    result=choose(poi("CISD_RETEST","c"),poi("SWING_HIGH_LOW","s"))
    assert result.category=="SWING_HIGH_LOW"


def test_cisd_final_tier_not_universal_entry():
    result=choose(poi("CISD_RETEST","c"))
    assert result.category=="CISD_RETEST"
    assert not result.source_author_entry_complete


def test_same_tier_fvg_tie_is_ambiguous_not_nearest_or_best_rr():
    result=choose(poi("FVG","a"),poi("FVG","b"),poi("SWING_HIGH_LOW","c"))
    assert result.status is ReviewStatus.AMBIGUOUS
    assert result.poi_id is None
    assert result.category=="FVG"


def test_missing_source_swing_or_incomplete_inventory_prevents_tier_priority():
    for kw in ({"ps":False},{"complete":False}):
        result=choose(poi("FVG","a"),**kw)
        assert result.status is ReviewStatus.INCOMPLETE
        assert result.poi_id is None


def test_unchecked_poi_relevance_cannot_be_skipped_in_favor_of_known():
    unverified=replace(poi("FVG","a"),relevance_independently_checked=False)
    result=choose(unverified,poi("SWING_HIGH_LOW","b"))
    assert result.status is ReviewStatus.INCOMPLETE
    assert result.poi_id is None


def test_unchecked_spatial_context_does_not_enable_lower_priority():
    unverified=replace(poi("FVG","a"),between_ps_and_current_range_checked=False)
    result=choose(unverified,poi("CISD_RETEST","b"))
    assert result.status is ReviewStatus.INCOMPLETE
    assert result.poi_id is None


def test_nonexistent_poi_does_not_create_trade():
    result=choose()
    assert result.status is ReviewStatus.NO_POI
    assert result.poi_id is None


def test_future_poi_and_non_ttrades_family_fail():
    future=replace(poi("FVG","a"),available_at=T+timedelta(minutes=3))
    with pytest.raises(ValueError,match="future"):
        choose(future)
    with pytest.raises(ValueError,match="cannot be transferred"):
        resolve_continuation_poi_tier(
            family="VT08_B01",observed=(),as_of=T,
            protected_swing_authentic=True,inventory_exhaustive_asof=True,
        )


def test_broken_bar_receipts_duplicates_and_fake_flags_fail_closed():
    with pytest.raises(ValueError,match="duplicate"):
        choose(poi("FVG","a"),poi("FVG","a"))
    with pytest.raises(ValueError,match="source bars"):
        choose(replace(poi("FVG","a"),bar_ids=()))
    with pytest.raises(ValueError,match="exact bool"):
        choose(replace(poi("FVG","a"),relevance_independently_checked="True"))


def test_poi_cannot_be_available_before_formation():
    with pytest.raises(ValueError,match="existence"):
        choose(replace(poi("FVG","a"),formed_at=T,available_at=T-timedelta(minutes=5)))
