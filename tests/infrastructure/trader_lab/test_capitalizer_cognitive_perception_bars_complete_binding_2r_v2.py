from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_historical_bar_completeness_audit_2r_v1 as bars,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_perception_bars_complete_binding_2r_v2 as perception_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_perception_evidence_binding_audit_2r_v1 as perception_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_provider_absence_tick_revalidation_2r_v1 as ticks,
)


SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _perception_row(symbol: str, entry_at: str) -> dict[str, object]:
    supported = perception_v1.PerceptionEvidenceState.SUPPORTED_TRUE.value
    return {
        "symbol": symbol,
        "session": "ASIA" if symbol != "NAS100" else "NEW_YORK",
        "operating_date": "2026-01-05",
        "entry_at": entry_at,
        "provenance": "CAUSAL_ARBITRATION_BASE",
        "quote_fresh": perception_v1.PerceptionEvidenceState.UNBOUND.value,
        "bars_complete": perception_v1.PerceptionEvidenceState.UNBOUND.value,
        "timestamps_ordered": supported,
        "session_clock_valid": supported,
        "provenance_valid": supported,
        "microstructure_complete": supported,
        "known_hard_integrity_failure": False,
        "full_perception_status_supported": False,
        "current_trade_outcome_visible_to_binding": False,
    }


def _bar_row(
    symbol: str,
    entry_at: str,
    *,
    state: str,
    missing: int,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "ASIA" if symbol != "NAS100" else "NEW_YORK",
        "operating_date": "2026-01-05",
        "h1_open": "2026-01-05T00:00:00+00:00",
        "entry_at": entry_at,
        "expected_minutes": 11,
        "observed_minutes": 11 - missing,
        "missing_calendar_minutes": missing,
        "first_missing_minute": (
            None if missing == 0 else "2026-01-05T00:01:00+00:00"
        ),
        "last_missing_minute": (
            None if missing == 0 else "2026-01-05T00:01:00+00:00"
        ),
        "entry_bar_present": True,
        "state": state,
        "provider_native_m1": True,
        "current_trade_outcome_visible_to_binding": False,
    }


def test_perception_v2_promotes_only_tick_resolved_unbound_bar_span(
    tmp_path: Path,
) -> None:
    perception_root = tmp_path / "perception"
    bar_root = tmp_path / "bars"
    tick_root = tmp_path / "ticks"

    perception_rows: list[dict[str, object]] = []
    for index, symbol in enumerate(SYMBOLS):
        entry = f"2026-01-05T00:{10 + index:02d}:00+00:00"
        perception_rows.append(_perception_row(symbol, entry))
        state = (
            bars.BarCompletenessState.UNBOUND.value
            if symbol == "AUDJPY"
            else bars.BarCompletenessState.SUPPORTED_TRUE.value
        )
        missing = 1 if symbol == "AUDJPY" else 0
        _write_jsonl(
            bar_root
            / symbol
            / (
                f"capitalizer-{symbol.lower()}-cognitive-historical-"
                "bar-completeness-audit-2r-v1-rows.jsonl"
            ),
            [_bar_row(symbol, entry, state=state, missing=missing)],
        )

    _write_json(
        perception_root
        / "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1.json",
        {
            "identity": perception_v1.IDENTITY,
            "control_trades": len(perception_rows),
        },
    )
    _write_jsonl(
        perception_root
        / "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1-rows.jsonl",
        perception_rows,
    )

    audjpy_entry = "2026-01-05T00:10:00+00:00"
    _write_json(
        tick_root
        / "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1.json",
        {
            "identity": ticks.IDENTITY,
            "all_native_m1_absences_explained_by_no_ticks": True,
        },
    )
    _write_jsonl(
        tick_root
        / "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1-rows.jsonl",
        [
            {
                "symbol": "AUDJPY",
                "entry_at": audjpy_entry,
                "minute": "2026-01-05T00:01:00+00:00",
                "bid_ticks": 0,
                "ask_ticks": 0,
                "bid_has_more": False,
                "ask_has_more": False,
                "provider_no_ticks": True,
                "contradiction_ticks_without_trendbar": False,
                "current_trade_outcome_visible_to_audit": False,
            }
        ],
    )

    report, rows = perception_v2.build_report(
        perception_root,
        bar_root,
        tick_root,
    )

    assert report["control_trades"] == 9
    assert report["bars_complete_state_counts"] == {
        "SUPPORTED_TRUE": 9,
        "SUPPORTED_FALSE": 0,
        "UNBOUND": 0,
    }
    assert report["bars_complete_source_counts"] == {
        "HISTORICAL_NATIVE_M1_CONTIGUOUS": 8,
        "PROVIDER_BID_ASK_NO_TICKS": 1,
    }
    assert report["bars_complete_evidence_bound"] is True
    assert report["quote_fresh_evidence_bound"] is False
    assert report["fully_known_integrity_except_quote_fresh_trades"] == 9
    assert report["runtime_perception_assessor_called"] is False
    assert report["full_perception_status_supported_trades"] == 0

    audjpy = next(row for row in rows if row.symbol == "AUDJPY")
    assert audjpy.bars_complete == "SUPPORTED_TRUE"
    assert audjpy.bars_complete_source == "PROVIDER_BID_ASK_NO_TICKS"


def test_perception_v2_keeps_unresolved_bar_span_unbound(
    tmp_path: Path,
) -> None:
    perception_root = tmp_path / "perception"
    bar_root = tmp_path / "bars"
    tick_root = tmp_path / "ticks"

    perception_rows: list[dict[str, object]] = []
    for index, symbol in enumerate(SYMBOLS):
        entry = f"2026-01-05T00:{10 + index:02d}:00+00:00"
        perception_rows.append(_perception_row(symbol, entry))
        state = (
            bars.BarCompletenessState.UNBOUND.value
            if symbol == "AUDJPY"
            else bars.BarCompletenessState.SUPPORTED_TRUE.value
        )
        missing = 1 if symbol == "AUDJPY" else 0
        _write_jsonl(
            bar_root
            / symbol
            / (
                f"capitalizer-{symbol.lower()}-cognitive-historical-"
                "bar-completeness-audit-2r-v1-rows.jsonl"
            ),
            [_bar_row(symbol, entry, state=state, missing=missing)],
        )

    _write_json(
        perception_root
        / "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1.json",
        {
            "identity": perception_v1.IDENTITY,
            "control_trades": len(perception_rows),
        },
    )
    _write_jsonl(
        perception_root
        / "capitalizer-cognitive-perception-evidence-binding-audit-2r-v1-rows.jsonl",
        perception_rows,
    )
    _write_json(
        tick_root
        / "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1.json",
        {
            "identity": ticks.IDENTITY,
            "all_native_m1_absences_explained_by_no_ticks": False,
        },
    )
    _write_jsonl(
        tick_root
        / "capitalizer-cognitive-provider-absence-tick-revalidation-2r-v1-rows.jsonl",
        [
            {
                "symbol": "AUDJPY",
                "entry_at": "2026-01-05T00:10:00+00:00",
                "minute": "2026-01-05T00:01:00+00:00",
                "bid_ticks": 1,
                "ask_ticks": 1,
                "bid_has_more": False,
                "ask_has_more": False,
                "provider_no_ticks": False,
                "contradiction_ticks_without_trendbar": True,
                "current_trade_outcome_visible_to_audit": False,
            }
        ],
    )

    report, rows = perception_v2.build_report(
        perception_root,
        bar_root,
        tick_root,
    )

    assert report["bars_complete_state_counts"]["UNBOUND"] == 1
    assert report["bars_complete_evidence_bound"] is False
    audjpy = next(row for row in rows if row.symbol == "AUDJPY")
    assert audjpy.bars_complete == "UNBOUND"
    assert audjpy.bars_complete_source == "UNBOUND"
