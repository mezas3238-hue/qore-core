from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    IDENTITY,
    SOURCE_GIT_SHA,
    SOURCE_IDENTITY,
    SOURCE_RUN_ID,
    cross_index_rows,
    event_ledgers,
    load_raw_m5,
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
        fvg_after_raid=True,
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


def test_event_ledgers_preserve_causal_outcome_boundary() -> None:
    ledgers = event_ledgers(_event())
    market = ledgers["MARKET_JOURNEY_LEDGER"][0]
    target = ledgers["TARGET_DESTINATION_LEDGER"][0]
    timing = ledgers["DEPARTURE_TIMING_LEDGER"][0]

    assert market["identity"] == IDENTITY
    assert market["source_run_id"] == SOURCE_RUN_ID
    assert market["source_git_sha"] == SOURCE_GIT_SHA
    assert market["departure_detector"] == "CAUSAL_CISD_V1"
    assert market["causal_feature"] is True
    assert market["outcome_only"] is False
    assert timing["minutes_source_event_to_departure"] == 15
    assert target["candidate_known_at_raid"] is True
    assert target["result_fields_outcome_only"] is True
    assert target["outcome_only"] is True


def test_load_raw_m5_reconstructs_provider_relative_prices(tmp_path: Path) -> None:
    ledger = tmp_path / "RAW_M5_LEDGER"
    ledger.mkdir()
    row = {
        "schema": "qore.cibo_market_atlas.raw_m5.v1",
        "identity": SOURCE_IDENTITY,
        "parent_identity": "CIBO_MARKET_ATLAS_20Y_V1",
        "canonical_symbol": "EURUSD",
        "provider_symbol": "EURUSD",
        "provider_symbol_id": 1,
        "digits": 5,
        "pip_position": 4,
        "opened_at": "2025-01-02T00:00:00+00:00",
        "utc_timestamp_in_minutes": 28929600,
        "low_relative": 103000,
        "delta_open": 20,
        "delta_high": 80,
        "delta_close": 60,
        "volume": 10,
        "open_relative": 103020,
        "high_relative": 103080,
        "close_relative": 103060,
    }
    (ledger / "2025.jsonl").write_text(json.dumps(row) + "\n")

    evidence, provenance = load_raw_m5(tmp_path)

    assert evidence.symbol == "EURUSD"
    assert evidence.bars[0].low == Decimal("1.03000")
    assert evidence.bars[0].open == Decimal("1.03020")
    assert evidence.bars[0].high == Decimal("1.03080")
    assert evidence.bars[0].close == Decimal("1.03060")
    assert provenance["retained_bars"] == 1


def test_cross_index_lead_lag_is_association_only() -> None:
    nas = [
        {
            "episode_id": "nas-1",
            "departure_at": "2025-01-02T14:00:00+00:00",
            "side": "long",
        }
    ]
    sp = [
        {
            "episode_id": "sp-1",
            "departure_at": "2025-01-02T14:10:00+00:00",
            "side": "long",
        }
    ]
    us = [
        {
            "episode_id": "us-1",
            "departure_at": "2025-01-02T14:25:00+00:00",
            "side": "short",
        }
    ]

    rows = cross_index_rows(nas, sp, us)
    nas_row = next(row for row in rows if row["symbol"] == "NAS100")

    assert nas_row["association_only"] is True
    assert nas_row["causal_feature"] is False
    assert nas_row["peer_states"]["SP500"]["lead_lag_minutes"] == 10
    assert nas_row["peer_states"]["SP500"]["agreement"] is True
    assert nas_row["peer_states"]["US30"]["agreement"] is False
