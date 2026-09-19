from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
    scan_microstructure,
    summarize_microstructure,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import (
    capitalizer_session_at,
)

_NY = ZoneInfo("America/New_York")


def _row(
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


def _write_rows(root: Path, rows: tuple[dict[str, object], ...]) -> None:
    ledger = root / "RAW_M5_LEDGER"
    ledger.mkdir(parents=True)
    with (ledger / "2026.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def test_session_clock_is_dst_aware_and_boundary_exact() -> None:
    assert (
        capitalizer_session_at(datetime(2026, 7, 1, 20, 0, tzinfo=_NY))
        is CapitalizerSession.ASIA
    )
    assert (
        capitalizer_session_at(datetime(2026, 7, 2, 2, 0, tzinfo=_NY))
        is CapitalizerSession.LONDON
    )
    assert (
        capitalizer_session_at(datetime(2026, 7, 2, 8, 30, tzinfo=_NY))
        is CapitalizerSession.NEW_YORK
    )
    assert capitalizer_session_at(datetime(2026, 7, 2, 16, 0, tzinfo=_NY)) is None
    assert (
        capitalizer_session_at(datetime(2026, 1, 2, 8, 30, tzinfo=_NY))
        is CapitalizerSession.NEW_YORK
    )


def test_atlas_reader_converts_provider_relative_prices_exactly(tmp_path: Path) -> None:
    opened = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    _write_rows(
        tmp_path,
        (
            _row(
                opened,
                low=15_665_000,
                open_=15_665_600,
                high=15_666_700,
                close=15_666_200,
            ),
        ),
    )
    bars = tuple(iter_atlas_m5(tmp_path))
    assert len(bars) == 1
    bar = bars[0]
    assert isinstance(bar, CapitalizerM5Bar)
    assert bar.open == Decimal("156.656")
    assert bar.high == Decimal("156.667")
    assert bar.low == Decimal("156.650")
    assert bar.close == Decimal("156.662")
    assert bar.range == Decimal("0.017")
    assert bar.body == Decimal("0.006")


def test_microstructure_scanner_detects_causal_high_raid_rejection(
    tmp_path: Path,
) -> None:
    first = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    second = datetime(2026, 7, 1, 20, 5, tzinfo=_NY)
    _write_rows(
        tmp_path,
        (
            _row(
                first,
                low=10_000_000,
                open_=10_005_000,
                high=10_010_000,
                close=10_005_000,
            ),
            _row(
                second,
                low=10_002_000,
                open_=10_006_000,
                high=10_015_000,
                close=10_008_000,
            ),
        ),
    )
    observations = scan_microstructure(tmp_path)
    assert len(observations) == 1
    observation = observations[0]
    assert observation.session is CapitalizerSession.ASIA
    assert CapitalizerMicrostructureEvent.HIGH_BREAK_ATTEMPT in observation.events
    assert CapitalizerMicrostructureEvent.HIGH_RAID_REJECTION in observation.events
    summary = summarize_microstructure(observations)
    assert summary.observations == 1
    assert summary.event_counts["HIGH_RAID_REJECTION"] == 1
    assert summary.rule_promotion_allowed is False


def test_microstructure_scanner_skips_non_contiguous_gap(tmp_path: Path) -> None:
    first = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    second = datetime(2026, 7, 1, 20, 10, tzinfo=_NY)
    _write_rows(
        tmp_path,
        (
            _row(
                first,
                low=10_000_000,
                open_=10_005_000,
                high=10_010_000,
                close=10_005_000,
            ),
            _row(
                second,
                low=10_002_000,
                open_=10_006_000,
                high=10_015_000,
                close=10_008_000,
            ),
        ),
    )
    assert scan_microstructure(tmp_path) == ()


def test_microstructure_matrix_requires_exact_nine_cell_coverage(tmp_path: Path) -> None:
    from qore.infrastructure.trader_lab.capitalizer_contract import allowed_markets
    from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
        CapitalizerMicrostructureEvent,
    )
    from qore.infrastructure.trader_lab.capitalizer_microstructure_matrix import (
        build_microstructure_matrix,
    )

    event_counts = {event.value: 1 for event in CapitalizerMicrostructureEvent}
    event_rates = {event.value: "0.1" for event in CapitalizerMicrostructureEvent}
    for session in CapitalizerSession:
        for symbol in allowed_markets(session):
            cell = tmp_path / f"{session.value.lower()}-{symbol.lower()}"
            cell.mkdir()
            (cell / f"capitalizer-{symbol.lower()}-microstructure-v1.json").write_text(
                json.dumps(
                    {
                        "identity": "QORE_CAPITALIZER_M5_MICROSTRUCTURE_DISCOVERY_V1",
                        "symbol": symbol,
                        "session": session.value,
                        "observations": 10,
                        "event_counts": event_counts,
                        "event_rates": event_rates,
                        "median_range_price": "0.01",
                        "median_body_fraction": "0.5",
                        "median_previous_range_ratio": "1",
                        "research_only": True,
                        "rule_promotion_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

    matrix = build_microstructure_matrix(tmp_path)
    assert len(matrix.cells) == 9
    assert matrix.complete_frozen_universe is True
    assert matrix.total_observations == 90
    assert matrix.session_observations == {
        "ASIA": 40,
        "LONDON": 20,
        "NEW_YORK": 30,
    }


def test_forward_response_is_outcome_only_and_uses_future_bars_after_decision(
    tmp_path: Path,
) -> None:
    from qore.infrastructure.trader_lab.capitalizer_forward_response import (
        CapitalizerForwardEvent,
        build_forward_responses,
        summarize_forward_responses,
    )

    start = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    rows = (
        _row(
            start,
            low=10_000_000,
            open_=10_005_000,
            high=10_010_000,
            close=10_005_000,
        ),
        _row(
            start + timedelta(minutes=5),
            low=10_002_000,
            open_=10_006_000,
            high=10_015_000,
            close=10_008_000,
        ),
        _row(
            start + timedelta(minutes=10),
            low=9_995_000,
            open_=10_007_000,
            high=10_009_000,
            close=10_000_000,
        ),
        _row(
            start + timedelta(minutes=15),
            low=9_990_000,
            open_=10_000_000,
            high=10_004_000,
            close=9_995_000,
        ),
        _row(
            start + timedelta(minutes=20),
            low=9_988_000,
            open_=9_995_000,
            high=10_000_000,
            close=9_990_000,
        ),
    )
    _write_rows(tmp_path, rows)

    responses = build_forward_responses(tmp_path)
    rejection = tuple(
        item
        for item in responses
        if item.event is CapitalizerForwardEvent.HIGH_RAID_REJECTION
    )
    assert rejection
    assert all(item.outcome_only for item in rejection)
    five = next(item for item in rejection if item.horizon_minutes == 5)
    assert five.decision_at.endswith("+00:00")
    assert five.favorable_range_units > 0
    report = summarize_forward_responses(responses)
    assert report.causal_feature_allowed is False
    assert report.rule_promotion_allowed is False


def test_forward_response_censors_opposite_direction_outside_bar(tmp_path: Path) -> None:
    from qore.infrastructure.trader_lab.capitalizer_forward_response import (
        build_forward_responses,
    )

    start = datetime(2026, 7, 1, 20, 0, tzinfo=_NY)
    rows = (
        _row(
            start,
            low=10_000_000,
            open_=10_005_000,
            high=10_010_000,
            close=10_005_000,
        ),
        _row(
            start + timedelta(minutes=5),
            low=9_990_000,
            open_=10_005_000,
            high=10_020_000,
            close=10_005_000,
        ),
        _row(
            start + timedelta(minutes=10),
            low=10_000_000,
            open_=10_005_000,
            high=10_010_000,
            close=10_006_000,
        ),
    )
    _write_rows(tmp_path, rows)
    assert build_forward_responses(tmp_path) == ()
