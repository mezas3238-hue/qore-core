from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_alignment_forensics import (
    build_cibo_alignment_responses,
    summarize_cibo_alignment,
)

_NY = ZoneInfo("America/New_York")


def _m5_row(
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
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _journey_row(
    *,
    raid_at: datetime,
    reclaim_at: datetime | None,
    departure_at: datetime | None,
    side: str = "long",
    timeframe: str = "H1",
    episode_id: str = "USDJPY:TEST",
) -> dict[str, object]:
    return {
        "schema": "qore.cibo_market_atlas.market_journey.v1",
        "identity": "CIBO_MARKET_JOURNEY_LAYER_V1",
        "episode_id": episode_id,
        "event_id": episode_id.split(":")[-1],
        "symbol": "USDJPY",
        "asset_class": "fx",
        "provider": "USDJPY",
        "side": side,
        "source_timeframe": timeframe,
        "source_boundary_type": "PRIOR_HIGH_LOW",
        "source_boundary": "100.000",
        "opposite_boundary": "100.500",
        "source_boundary_created_at": (raid_at - timedelta(hours=1)).isoformat(),
        "liquidity_raid_at": raid_at.isoformat(),
        "reclaim_at": None if reclaim_at is None else reclaim_at.isoformat(),
        "departure_at": None if departure_at is None else departure_at.isoformat(),
        "departure_detector": (
            "CAUSAL_CISD_V1" if departure_at is not None else "UNRESOLVED_DEPARTURE"
        ),
        "last_structure_before_departure": (
            "CISD_RELATED_STRUCTURE"
            if departure_at is not None
            else "LIQUIDITY_RAID_RECLAIM"
        ),
        "session_bucket": "asia",
        "ny_minute_of_day": raid_at.astimezone(_NY).hour * 60,
        "causal_feature": True,
        "outcome_only": False,
        "source_run_id": 35166210458,
        "source_git_sha": "ab782b8e9f890f86a2b6500070f0556b4b685e3d",
    }


def _write_journey(root: Path, rows: tuple[dict[str, object], ...]) -> None:
    root.mkdir(parents=True)
    with (root / "MARKET_JOURNEY_LEDGER.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def test_exact_cibo_alignment_uses_only_events_known_by_decision_close(
    tmp_path: Path,
) -> None:
    m5_root = tmp_path / "m5"
    journey_root = tmp_path / "journey"
    start = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    current = start + timedelta(minutes=5)
    decision = current + timedelta(minutes=5)
    _write_m5(
        m5_root,
        (
            _m5_row(
                start,
                low=10_000_000,
                open_=10_005_000,
                high=10_010_000,
                close=10_005_000,
            ),
            _m5_row(
                current,
                low=9_995_000,
                open_=10_004_000,
                high=10_008_000,
                close=10_002_000,
            ),
            _m5_row(
                current + timedelta(minutes=5),
                low=10_000_000,
                open_=10_002_000,
                high=10_010_000,
                close=10_008_000,
            ),
            _m5_row(
                current + timedelta(minutes=10),
                low=10_006_000,
                open_=10_008_000,
                high=10_014_000,
                close=10_012_000,
            ),
            _m5_row(
                current + timedelta(minutes=15),
                low=10_010_000,
                open_=10_012_000,
                high=10_018_000,
                close=10_016_000,
            ),
        ),
    )
    _write_journey(
        journey_root,
        (
            _journey_row(
                raid_at=current,
                reclaim_at=decision,
                departure_at=decision,
            ),
            _journey_row(
                raid_at=current + timedelta(minutes=5),
                reclaim_at=current + timedelta(minutes=10),
                departure_at=current + timedelta(minutes=10),
                episode_id="USDJPY:FUTURE",
            ),
        ),
    )

    responses = build_cibo_alignment_responses(
        m5_root=m5_root,
        journey_root=journey_root,
    )
    current_responses = tuple(
        item for item in responses if item.decision_at == decision
    )
    tags = {item.context_tag for item in current_responses}
    assert "RAID_ALIGNED_H1" in tags
    assert "RECLAIM_ALIGNED_H1" in tags
    assert "DEPARTURE_ALIGNED_H1" in tags
    assert all("FUTURE" not in item.context_tag for item in current_responses)
    assert all(item.outcome_only for item in current_responses)


def test_cibo_alignment_report_remains_consumed_research_only(tmp_path: Path) -> None:
    m5_root = tmp_path / "m5"
    journey_root = tmp_path / "journey"
    start = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    current = start + timedelta(minutes=5)
    decision = current + timedelta(minutes=5)
    _write_m5(
        m5_root,
        (
            _m5_row(
                start,
                low=10_000_000,
                open_=10_005_000,
                high=10_010_000,
                close=10_005_000,
            ),
            _m5_row(
                current,
                low=9_995_000,
                open_=10_004_000,
                high=10_008_000,
                close=10_002_000,
            ),
            _m5_row(
                current + timedelta(minutes=5),
                low=10_000_000,
                open_=10_002_000,
                high=10_010_000,
                close=10_008_000,
            ),
            _m5_row(
                current + timedelta(minutes=10),
                low=10_006_000,
                open_=10_008_000,
                high=10_014_000,
                close=10_012_000,
            ),
            _m5_row(
                current + timedelta(minutes=15),
                low=10_010_000,
                open_=10_012_000,
                high=10_018_000,
                close=10_016_000,
            ),
        ),
    )
    _write_journey(
        journey_root,
        (
            _journey_row(
                raid_at=current,
                reclaim_at=decision,
                departure_at=decision,
            ),
        ),
    )

    report = summarize_cibo_alignment(
        build_cibo_alignment_responses(
            m5_root=m5_root,
            journey_root=journey_root,
        )
    )
    assert report.evidence_status == "CONSUMED_RESEARCH_EVIDENCE"
    assert report.context_fields_causal is True
    assert report.outcome_fields_causal is False
    assert report.lookback_tuning_used is False
    assert report.rule_promotion_allowed is False
    assert report.candidate_freeze_allowed is False
    assert any(
        item.context_tag == "DEPARTURE_ALIGNED_H1"
        for item in report.aggregates
    )
