from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_cibo_market_dossiers import (
    _cross_summary,
    _metric_block,
    _metrics_from_values,
    _quarter,
    _semester,
    _year,
)


def _row(
    symbol: str = "NAS100",
    *,
    signal_offset: int = 0,
    primary_r: str = "-1.05",
    exit_reason: str = "stop",
    later2: bool = True,
) -> dict[str, object]:
    signal = datetime(2024, 1, 2, 15, 0, tzinfo=UTC) + timedelta(
        minutes=signal_offset
    )
    return {
        "symbol": symbol,
        "signal_at": signal.isoformat(),
        "primary_r": primary_r,
        "exit_reason": exit_reason,
        "side": "long",
        "post_stop_afterlife": (
            {"levels": {"2": {"hit": later2}}}
            if exit_reason == "stop"
            else None
        ),
    }


def _departure(row: dict[str, object]) -> dict[str, object]:
    return {
        "symbol": row["symbol"],
        "signal_at": row["signal_at"],
        "minutes_cisd_to_continuation": 15,
        "minutes_poi_arrival_to_cisd": 30,
    }


def _sync(row: dict[str, object]) -> dict[str, object]:
    return {
        "symbol": row["symbol"],
        "signal_at": row["signal_at"],
        "error_taxonomy": {
            "A_DIRECTION_ERROR": {
                "status": "candidate",
                "basis": "synthetic",
            },
            "E_CONFIRMATION_ERROR": {
                "status": "unresolved",
                "basis": "synthetic",
            },
            "non_causal_multi_label": True,
        },
    }


def test_metrics_from_values_preserves_primary_economics() -> None:
    result = _metrics_from_values(
        [Decimal("2"), Decimal("-1"), Decimal("-1"), Decimal("2")]
    )
    assert result["sample"] == 4
    assert result["total_primary_r"] == "2"
    assert result["mean_primary_r"] == "0.5"
    assert result["profit_factor_primary"] == "2"
    assert result["max_drawdown_primary_r"] == "2"


def test_metric_block_uses_semantic_departure_and_afterlife() -> None:
    row = _row()
    key = (str(row["symbol"]), str(row["signal_at"]))
    result = _metric_block(
        [row],
        {key: _departure(row)},
        {key: _sync(row)},
    )
    assert result["stop_rate"] == "1"
    assert result["stopped_then_later_2r_rate"] == "1"
    assert result["median_minutes_cisd_to_continuation"] == 15
    assert result["median_minutes_poi_arrival_to_cisd"] == 30
    rates = result["taxonomy_candidate_rates"]
    assert isinstance(rates, dict)
    assert rates["A_DIRECTION_ERROR"] == "1"
    assert "E_CONFIRMATION_ERROR" not in rates


def test_temporal_labels_are_new_york_calendar_bound() -> None:
    row = _row()
    assert _year(row) == "2024"
    assert _semester(row) == "2024-H1"
    assert _quarter(row) == "2024-Q1"


def test_cross_summary_counts_multi_market_same_side_stops() -> None:
    nas = _row("NAS100", signal_offset=0)
    sp = _row("SP500", signal_offset=15)
    us = _row(
        "US30",
        signal_offset=30,
        primary_r="1.95",
        exit_reason="target",
        later2=False,
    )
    journey = {
        (str(row["symbol"]), str(row["signal_at"])): row
        for row in (nas, sp, us)
    }
    signals = {
        str(row["symbol"]): row["signal_at"] for row in (nas, sp, us)
    }
    cross = [
        {
            "new_york_date": "2024-01-02",
            "anchor_hour_new_york": 6,
            "symbols_present": ["NAS100", "SP500", "US30"],
            "side_agreement": True,
            "event_order": {
                "source_poi_arrival": {"leader": "NAS100"},
                "cisd_confirmation": {"leader": "SP500"},
                "continuation_departure": {"leader": "US30"},
            },
        }
    ]
    v1_cross: dict[tuple[str, int], dict[str, object]] = {
        ("2024-01-02", 6): {
            "signals": signals,
        }
    }
    result = _cross_summary(cross, journey, v1_cross)
    assert result["cohort_count"] == 1
    assert result["three_market_cohort_rate"] == "1"
    assert result["side_agreement_rate"] == "1"
    assert result["multi_market_stop_cohorts"] == 1
    assert result["same_side_multi_market_stop_cohorts"] == 1
    transitions = result["leader_transition_counts"]
    assert isinstance(transitions, dict)
    assert transitions["NAS100->SP500->US30"] == 1
