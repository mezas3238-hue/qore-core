from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_structure_v1_1 import (
    EQUAL_LIQUIDITY_DETECTOR,
    IDENTITY,
    event_ledgers_v1_1,
)


def _event() -> behavior.Event:
    return behavior.Event(
        evidence_id="test",
        symbol="NAS100",
        asset_class="index",
        provider="USTEC",
        timeframe="H4",
        reference_type="swing-3",
        side="long",
        reference_opened_at=datetime(2025, 1, 2, 12, tzinfo=UTC),
        source_opened_at=datetime(2025, 1, 2, 16, tzinfo=UTC),
        raid_at=datetime(2025, 1, 2, 16, 15, tzinfo=UTC),
        reference_level=Decimal("20000"),
        opposite_reference=Decimal("20200"),
        tick_size=Decimal("0.01"),
        reference_age_bars=2,
        exact_equal_count=1,
        nearest_peer_ticks=Decimal("30"),
        raid_depth_ticks=Decimal("20"),
        raid_depth_pct=Decimal("0.001"),
        raid_depth_range_units=Decimal("0.10"),
        source_range_ticks=Decimal("500"),
        body_fraction=Decimal("0.40"),
        rejection_wick_fraction=Decimal("0.50"),
        close_location=Decimal("0.70"),
        prior_body_alignment="opposed",
        session_bucket="new-york",
        ny_minute_of_day=675,
        same_source_reclaim=True,
        reclaim_latency_minutes=10,
        reclaim_depth_ticks=Decimal("4"),
        cisd_confirmed=True,
        cisd_latency_minutes=30,
        protected_swing_distance_ticks=Decimal("80"),
        fvg_after_raid=False,
        opposite_reference_hit_24h=True,
        opposite_reference_hit_minutes=90,
        mfe_15m_ticks=Decimal("40"),
        mae_15m_ticks=Decimal("10"),
        mfe_30m_ticks=Decimal("70"),
        mae_30m_ticks=Decimal("10"),
        mfe_60m_ticks=Decimal("100"),
        mae_60m_ticks=Decimal("15"),
        mfe_240m_ticks=Decimal("180"),
        mae_240m_ticks=Decimal("20"),
        mfe_1440m_ticks=Decimal("260"),
        mae_1440m_ticks=Decimal("35"),
        outcome="rejection-with-cisd",
    )


def test_single_reference_does_not_invent_equal_liquidity() -> None:
    ledgers = event_ledgers_v1_1(_event())
    structures = ledgers["STRUCTURE_TOUCH_LEDGER"]
    assert all(row["structure_type"] != "EQUAL_LIQUIDITY" for row in structures)
    assert ledgers["MARKET_JOURNEY_LEDGER"][0]["source_exact_equal_liquidity"] is False


def test_exact_equal_reference_materializes_causal_structure() -> None:
    event = replace(_event(), exact_equal_count=3, nearest_peer_ticks=Decimal("12"))
    ledgers = event_ledgers_v1_1(event)
    rows = [
        row
        for row in ledgers["STRUCTURE_TOUCH_LEDGER"]
        if row["structure_type"] == "EQUAL_LIQUIDITY"
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["identity"] == IDENTITY
    assert row["detector_version"] == EQUAL_LIQUIDITY_DETECTOR
    assert row["exact_equal_count"] == 3
    assert row["tolerance_ticks"] == "0"
    assert row["classification_basis"] == "EXACT_PROVIDER_PRICE_EQUALITY_ONLY"
    assert row["causal_feature"] is True
    assert row["outcome_only"] is False


def test_v1_1_preserves_base_causal_outcome_split() -> None:
    event = replace(_event(), exact_equal_count=2)
    ledgers = event_ledgers_v1_1(event)
    market = ledgers["MARKET_JOURNEY_LEDGER"][0]
    target = ledgers["TARGET_DESTINATION_LEDGER"][0]
    assert market["identity"] == IDENTITY
    assert market["causal_feature"] is True
    assert target["identity"] == IDENTITY
    assert target["outcome_only"] is True
