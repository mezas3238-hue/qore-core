from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_index_market_journey_atlas import (
    Bar,
    _fvg_events,
    _local_sweep_events,
    build_window,
)


def _bar(
    minute: int,
    *,
    opened: str,
    high: str,
    low: str,
    closed: str,
) -> Bar:
    start = datetime(2020, 1, 6, 5, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return Bar(
        opened_at=start,
        closed_at=start + timedelta(minutes=15),
        open=Decimal(opened),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(closed),
    )


def test_detects_local_sweep_and_fvg_diagnostics() -> None:
    sweep_bars = (
        _bar(0, opened="10", high="10.2", low="9.8", closed="10.1"),
        _bar(15, opened="10.1", high="10.3", low="9.9", closed="10.2"),
        _bar(30, opened="10.2", high="10.4", low="10", closed="10.3"),
        _bar(45, opened="10.3", high="10.5", low="10.1", closed="10.4"),
        _bar(60, opened="10.4", high="10.8", low="10.2", closed="10.45"),
    )
    sweeps = _local_sweep_events(sweep_bars)
    assert sweeps
    assert sweeps[-1]["kind"] == "high-sweep-close-back"

    fvg_bars = (
        _bar(0, opened="10", high="10.2", low="9.8", closed="10.1"),
        _bar(15, opened="10.1", high="10.4", low="10", closed="10.3"),
        _bar(30, opened="10.8", high="11", low="10.6", closed="10.9"),
    )
    fvgs = _fvg_events(fvg_bars)
    assert fvgs
    assert fvgs[-1]["kind"] == "bullish-fvg"


def _write_evidence(path: Path, symbol: str, offset: Decimal) -> None:
    bars: list[dict[str, object]] = []
    start = datetime(2020, 1, 5, 23, 0, tzinfo=UTC)
    price = Decimal("100") + offset
    for index in range(80):
        opened_at = start + timedelta(minutes=15 * index)
        opened = price + Decimal(index) * Decimal("0.05")
        high = opened + Decimal("0.45")
        low = opened - Decimal("0.35")
        closed = opened + Decimal("0.10")
        if index >= 34:
            high += Decimal(index - 33) * Decimal("0.25")
            closed = high - Decimal("0.05")
        bars.append(
            {
                "period": "M15",
                "opened_at": opened_at.isoformat(),
                "closed_at": (opened_at + timedelta(minutes=15)).isoformat(),
                "open": str(opened),
                "high": str(high),
                "low": str(low),
                "close": str(closed),
            }
        )
    path.write_text(
        json.dumps({"canonical_symbol": symbol, "periods": {"M15": bars}}),
        encoding="utf-8",
    )


def test_build_window_explains_journey_targets_and_governance(tmp_path: Path) -> None:
    evidence: dict[str, Path] = {}
    for symbol, offset in (
        ("NAS100", Decimal("0")),
        ("SP500", Decimal("10")),
        ("US30", Decimal("20")),
    ):
        path = tmp_path / f"{symbol}.json"
        _write_evidence(path, symbol, offset)
        evidence[symbol] = path

    signal_at = datetime(2020, 1, 6, 8, 45, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    for symbol, offset in (
        ("NAS100", Decimal("0")),
        ("SP500", Decimal("10")),
        ("US30", Decimal("20")),
    ):
        entry = Decimal("101.90") + offset
        rows.append(
            {
                "symbol": symbol,
                "signal_at": signal_at.isoformat(),
                "h4_opened_at": datetime(2020, 1, 6, 6, 0, tzinfo=UTC).isoformat(),
                "entry": str(entry),
                "risk_points": "1",
                "side": "long",
                "anchor_hour_new_york": 1,
                "model_kind": "same-c2-intracandle",
                "poi_kind": "fvg",
                "primary_r": "-1.05",
                "raw_r": "-1",
                "exit_reason": "stop",
                "exited_at": (signal_at + timedelta(minutes=30)).isoformat(),
                "prior_h4_range_regime": "compressed",
                "peer_alignment_count": 2,
                "side_adjusted_relative_strength_rank": 3,
            }
        )
    report_path = tmp_path / "window.json"
    report_path.write_text(
        json.dumps(
            {
                "candidate_id": "VT08_INDEX_V7_TTRADES_SOURCE_CORRECTED_001",
                "rule_fingerprint": "frozen",
                "window_id": "synthetic",
                "partition": {
                    "start_date": "2020-01-05",
                    "end_date_exclusive": "2020-01-08",
                },
                "trades": rows,
            }
        ),
        encoding="utf-8",
    )

    result = build_window(
        input_report=report_path,
        nas100=evidence["NAS100"],
        sp500=evidence["SP500"],
        us30=evidence["US30"],
    )
    assert result["trade_count"] == 3
    structures = result["structure_definition_status"]
    assert isinstance(structures, dict)
    assert structures["order_block"] == "UNRESOLVED_SOURCE_DEFINITION_NOT_AUTOMATED"
    assert structures["breaker_block"] == "UNRESOLVED_SOURCE_DEFINITION_NOT_AUTOMATED"
    governance = result["governance"]
    assert isinstance(governance, dict)
    assert governance["diagnostic_only"] is True
    assert governance["changes_v7"] is False
    assert governance["target_atlas_is_descriptive_not_target_selection"] is True
    markets = result["market_summary"]
    assert isinstance(markets, dict)
    nas = markets["NAS100"]
    assert isinstance(nas, dict)
    overall = nas["overall"]
    assert isinstance(overall, dict)
    assert Decimal(str(overall["hit_rate_by_r"]["1"])) > 0
    assert Decimal(str(overall["stopped_then_2r_24h_rate"])) > 0
