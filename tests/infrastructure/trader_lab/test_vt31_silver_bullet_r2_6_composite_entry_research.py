from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_6_composite_entry_research import (
    HYPOTHESIS_COUNT,
    VARIANTS,
    _select_nearest_retracement,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22EntryFamily,
    Vt31R22EvidenceClass,
)


def _candidate(
    family: Vt31R22EntryFamily,
    lower: str,
    upper: str,
) -> Vt31R22EntryEvidence:
    return Vt31R22EntryEvidence(
        family=family,
        formed_at=datetime(2026, 1, 2, 15, 5, tzinfo=UTC),
        source_candle_open=Decimal("103"),
        source_candle_high=Decimal("104"),
        source_candle_low=Decimal("102"),
        source_candle_close=Decimal("103"),
        zone_lower=Decimal(lower),
        zone_upper=Decimal(upper),
        zone_class=Vt31R22EvidenceClass.SOURCE_EXPLICIT,
        source_timestamps=("source",),
    )


def test_r2_6_predeclares_only_three_location_hypotheses() -> None:
    assert HYPOTHESIS_COUNT == 3 == len(VARIANTS)
    assert {item.location for item in VARIANTS} == {
        "near-stop",
        "midpoint",
        "near-target",
    }
    assert len({item.fingerprint() for item in VARIANTS}) == 3


def test_selector_uses_nearest_valid_long_retracement_across_families() -> None:
    candidates = (
        _candidate(Vt31R22EntryFamily.FAIR_VALUE_GAP, "100", "102"),
        _candidate(Vt31R22EntryFamily.ORDER_BLOCK, "102", "104"),
    )
    entry, reason = _select_nearest_retracement(
        candidates,
        side=DemoTradingSetupSide.LONG,
        confirmation_close=Decimal("105"),
        extreme=Decimal("95"),
        target=Decimal("120"),
        location="midpoint",
    )
    assert entry == Decimal("103")
    assert reason == "selected"


def test_selector_rejects_level_already_beyond_confirmation() -> None:
    candidates = (
        _candidate(Vt31R22EntryFamily.BREAKER, "106", "108"),
    )
    entry, reason = _select_nearest_retracement(
        candidates,
        side=DemoTradingSetupSide.LONG,
        confirmation_close=Decimal("105"),
        extreme=Decimal("95"),
        target=Decimal("120"),
        location="midpoint",
    )
    assert entry is None
    assert reason == "no-still-valid-retracement"
