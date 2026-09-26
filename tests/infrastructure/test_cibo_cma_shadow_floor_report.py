"""CMA shadow-floor report invariants."""
# ruff: noqa: I001

from __future__ import annotations

import json
from pathlib import Path

from scripts.cibo_cma_shadow_floor_report import build_summary, load_reports


def _row(*, realized: str, settled: bool) -> dict[str, object]:
    return {
        "case_id": "signal:" + "a" * 64,
        "trader": "VT31_NAS100",
        "symbol": "NAS100",
        "first_observed_at": "2026-09-26T12:00:00+00:00",
        "last_observed_at": "2026-09-26T12:01:00+00:00",
        "event_count": 1,
        "stages": {},
        "event_names": [],
        "requested_volumes": ["0.04"],
        "requested_stop_risks": ["10"],
        "protection_events": [],
        "partial_close_events": [],
        "exit_events": ["CTRADER_DEMO_EXIT_SETTLEMENT"] if settled else [],
        "fault_events": [],
        "settlement_events": ["CTRADER_DEMO_EXIT_SETTLEMENT"] if settled else [],
        "realized_net_pnl": realized,
        "settlement_prices": [],
        "settled_source_volumes": [],
        "estimated_initial_risk_pnl": "10",
        "estimated_remaining_stop_pnl": None,
        "estimated_economic_floor_pnl": None,
        "estimated_economic_floor_r": None,
        "path_sample_count": 0,
        "max_unrealized_pnl": None,
        "min_unrealized_pnl": None,
        "max_favorable_price_delta": None,
        "max_adverse_price_delta": None,
        "stop_history": [],
        "volume_history": [],
        "observations": [],
    }


def test_report_counts_recovered_loss_and_insufficient(tmp_path: Path) -> None:
    path = tmp_path / "case-report.json"
    path.write_text(
        json.dumps(
            [
                _row(realized="64.06", settled=True),
                {
                    **_row(realized="-10.56", settled=True),
                    "case_id": "signal:" + "b" * 64,
                },
                {
                    **_row(realized="0", settled=False),
                    "case_id": "signal:" + "c" * 64,
                },
            ]
        ),
        encoding="utf-8",
    )

    summary = build_summary(load_reports(path))
    row = summary["traders"]["VT31_NAS100"]  # type: ignore[index]

    assert summary["total_cases"] == 3
    assert row["BASE_RECOVERED"] == 1
    assert row["BASE_NOT_RECOVERED"] == 1
    assert row["INSUFFICIENT_EVIDENCE"] == 1
