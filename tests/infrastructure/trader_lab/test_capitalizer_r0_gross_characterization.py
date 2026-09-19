from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    build_r0_trades,
    summarize_r0,
)

_NY = ZoneInfo("America/New_York")


def _m5(
    opened_at: datetime,
    *,
    low: int,
    open_: int,
    high: int,
    close: int,
) -> dict[str, object]:
    return {
        "schema": "qore.cibo_market_atlas.raw_m5.v1",
        "identity": "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1",
        "canonical_symbol": "USDJPY",
        "opened_at": opened_at.astimezone(UTC).isoformat(),
        "digits": 3,
        "volume": 100,
        "low_relative": low,
        "open_relative": open_,
        "high_relative": high,
        "close_relative": close,
    }


def _write_m5(root: Path, rows: tuple[dict[str, object], ...]) -> None:
    ledger = root / "RAW_M5_LEDGER"
    ledger.mkdir(parents=True)
    with (ledger / "2026.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _write_journey(root: Path, departure_at: datetime) -> None:
    root.mkdir(parents=True)
    row = {
        "schema": "qore.cibo_market_atlas.market_journey.v1",
        "identity": "CIBO_MARKET_JOURNEY_LAYER_V1",
        "episode_id": "USDJPY:R0",
        "event_id": "R0",
        "symbol": "USDJPY",
        "asset_class": "fx",
        "provider": "USDJPY",
        "side": "long",
        "source_timeframe": "H1",
        "source_boundary_type": "PRIOR_HIGH_LOW",
        "source_boundary": "100.000",
        "opposite_boundary": "100.100",
        "source_boundary_created_at": (departure_at - timedelta(hours=1)).isoformat(),
        "liquidity_raid_at": (departure_at - timedelta(minutes=5)).isoformat(),
        "reclaim_at": departure_at.isoformat(),
        "departure_at": departure_at.isoformat(),
        "departure_detector": "CAUSAL_CISD_V1",
        "last_structure_before_departure": "CISD_RELATED_STRUCTURE",
        "session_bucket": "asia",
        "ny_minute_of_day": 1200,
        "causal_feature": True,
        "outcome_only": False,
        "source_run_id": 35166210458,
        "source_git_sha": "a" * 40,
    }
    with (root / "MARKET_JOURNEY_LEDGER.jsonl").open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def _write_target(root: Path, departure_at: datetime) -> None:
    root.mkdir(parents=True)
    row = {
        "schema": "qore.cibo_market_atlas.target_destination.v2",
        "identity": "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE",
        "episode_id": "USDJPY:R0",
        "candidate_id": "TARGET-1",
        "symbol": "USDJPY",
        "side": "long",
        "departure_at": departure_at.isoformat(),
        "departure_anchor_price": "100.020",
        "candidate_type": "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
        "source_timeframe": "H1",
        "candidate_price": "100.100",
        "candidate_distance_ticks": "80",
        "candidate_known_at": (departure_at - timedelta(minutes=30)).isoformat(),
        "candidate_structural_opened_at": (
            departure_at - timedelta(hours=1)
        ).isoformat(),
        "active_untouched_at_departure": True,
        "causal_feature": True,
        "outcome_only": False,
        "result_fields_outcome_only": True,
        "touch_within_24h": True,
        "time_to_touch_minutes": 5,
    }
    with (root / "TARGET_DESTINATION_LEDGER_V2.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        handle.write(json.dumps(row) + "\n")


def _roots(tmp_path: Path, *, ambiguous: bool) -> tuple[Path, Path, Path]:
    m5_root = tmp_path / "m5"
    journey_root = tmp_path / "journey"
    target_root = tmp_path / "target"
    start = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    source = start + timedelta(minutes=5)
    departure = source + timedelta(minutes=5)
    entry = source + timedelta(minutes=5)

    entry_low = 9_994_000 if ambiguous else 10_001_000
    _write_m5(
        m5_root,
        (
            _m5(
                start,
                low=10_000_000,
                open_=10_005_000,
                high=10_010_000,
                close=10_005_000,
            ),
            _m5(
                source,
                low=9_995_000,
                open_=10_004_000,
                high=10_008_000,
                close=10_002_000,
            ),
            _m5(
                entry,
                low=entry_low,
                open_=10_002_000,
                high=10_011_000,
                close=10_008_000,
            ),
        ),
    )
    _write_journey(journey_root, departure)
    _write_target(target_root, departure)
    return m5_root, journey_root, target_root


def test_r0_clean_target_hit_uses_next_m5_open_and_causal_target(tmp_path: Path) -> None:
    m5_root, journey_root, target_root = _roots(tmp_path, ambiguous=False)
    trades = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    assert len(trades) == 1
    trade = trades[0]
    assert trade.exit_reason == "TARGET"
    assert trade.realized_gross_r > 1
    assert trade.same_bar_stop_target_ambiguity is False
    report = summarize_r0(trades)
    assert report.characterization_only is True
    assert report.economic_candidate is False
    assert report.execution_costs_applied is False
    assert report.portfolio_session_budget_applied is False


def test_r0_same_bar_stop_target_is_stop_first(tmp_path: Path) -> None:
    m5_root, journey_root, target_root = _roots(tmp_path, ambiguous=True)
    trades = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    assert len(trades) == 1
    trade = trades[0]
    assert trade.exit_reason == "STOP"
    assert trade.realized_gross_r == -1
    assert trade.same_bar_stop_target_ambiguity is True
