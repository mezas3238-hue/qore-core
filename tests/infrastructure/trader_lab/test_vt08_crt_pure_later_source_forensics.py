"""Causal flag proof for qualitative VT08 later-source forensic ledger."""

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab.vt08_crt_pure_later_source_forensics import (
    audit_88_original_cases,
    classify_preentry_context,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

BASE = datetime(2026, 1, 14, 13, tzinfo=UTC)


def _bar(index: int, high: int, low: int, close: int) -> M15Bar:
    return M15Bar(
        opened_at=BASE + timedelta(minutes=index * 15),
        open_price=95,
        high_price=high,
        low_price=low,
        close_price=close,
    )


def _classify(
    pre_entry: tuple[M15Bar, ...],
    *,
    first_ids: tuple[str, ...] = ("A",),
    later_ids: tuple[str, ...] = ("B",),
    first_prices: tuple[int, ...] = (80,),
    later_prices: tuple[int, ...] = (85,),
    first_source_extreme: int = 80,
) -> dict[str, object]:
    return classify_preentry_context(
        direction=CrtPureCandidateDirection.BULLISH,
        parent_side=90,
        target_midpoint=100,
        first_source_extreme=first_source_extreme,
        first_reference_ids=first_ids,
        later_reference_ids=later_ids,
        first_reference_prices=first_prices,
        later_reference_prices=later_prices,
        post_first=pre_entry,
        pre_entry=pre_entry,
    )


def test_distinct_level_without_adverse_preentry_evidence_is_not_authorized() -> None:
    row = _classify((_bar(0, 99, 91, 95),))
    assert row["observational_class"] == "DISTINCT_REFERENCE_NO_OBSERVED_ADVERSE_CONTEXT"
    assert row["methodology_authorization"] == "OPEN_NOT_CERTIFIED"


def test_same_price_with_different_level_ids_is_not_claimed_independent() -> None:
    row = _classify(
        (_bar(0, 99, 91, 95),),
        first_ids=("A",), later_ids=("B",),
        first_prices=(85,), later_prices=(85,),
    )
    assert row["observational_class"] == "REPEATED_REFERENCE_ID_OR_PRICE"
    assert row["same_reference_id"] is False
    assert row["same_reference_price"] is True


def test_parent_side_close_prioritized_before_earlier_midpoint_touch() -> None:
    row = _classify((_bar(0, 115, 80, 85),))
    assert row["observational_class"] == "PARENT_SIDE_BODY_ACCEPTANCE"
    assert row["parent_side_close_beyond_at"] == BASE.isoformat()
    assert row["c1_midpoint_pre_touched_at"] == BASE.isoformat()
    assert row["first_source_extreme_re_touched_at"] == BASE.isoformat()


def test_previously_touched_target_context_is_not_live_target() -> None:
    row = _classify((_bar(0, 101, 91, 98),))
    assert row["observational_class"] == "TARGET_ALREADY_TOUCHED"
    assert row["c1_midpoint_pre_touched_at"] == BASE.isoformat()


def test_first_source_extreme_retouch_class_keeps_authority_open() -> None:
    row = _classify(
        (_bar(0, 99, 79, 95),), first_source_extreme=80
    )
    assert row["observational_class"] == "FIRST_SOURCE_EXTREME_RETOUCHED"
    assert row["methodology_authorization"] == "OPEN_NOT_CERTIFIED"


def test_unknown_context_never_promoted_by_missing_bar() -> None:
    with pytest.raises(ValueError, match="pre-entry window"):
        _classify(())


def test_btcusd_remains_frozen_before_any_market_data() -> None:
    with pytest.raises(ValueError, match="BTCUSD frozen"):
        audit_88_original_cases(CrtPureMarket.BTCUSD, ())
