from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r12_frozen_candidate_trader_replay import (
    _max_dd,
    _max_losing_streak,
    _metrics,
    _outlier_sensitivity,
)


def _row(
    *,
    episode: str,
    r: str,
    exit_reason: str,
    year: int = 2026,
) -> dict[str, object]:
    return {
        "episode_id": episode,
        "entry_at": f"{year}-01-01T00:00:00+00:00",
        "year": year,
        "side": "long",
        "source_timeframe": "H1",
        "entry_mode": "NEXT_SOURCE_OPEN",
        "target_route": "SOURCE_OPPOSITE",
        "exit_reason": exit_reason,
        "primary_net_r": r,
    }


def test_drawdown_and_losing_streak_are_chronological() -> None:
    values = [
        Decimal("1"),
        Decimal("-1"),
        Decimal("-2"),
        Decimal("0.5"),
        Decimal("-0.5"),
    ]
    assert _max_dd(values) == Decimal("3")
    assert _max_losing_streak(values) == 2


def test_metrics_report_primary_and_exit_counts() -> None:
    rows = [
        _row(episode="a", r="2", exit_reason="TARGET"),
        _row(episode="b", r="-1", exit_reason="STOP"),
        _row(episode="c", r="0", exit_reason="LIFECYCLE"),
    ]
    result = _metrics(rows)
    assert result["trades"] == 3
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["flats"] == 1
    assert result["total_r"] == "1"
    assert result["mean_r"] == "0.3333333333333333333333333333"
    assert result["profit_factor"] == "2"
    assert result["target_exits"] == 1
    assert result["stop_exits"] == 1
    assert result["lifecycle_other_exits"] == 1


def test_extra_friction_is_applied_per_trade() -> None:
    rows = [
        _row(episode="a", r="1", exit_reason="TARGET"),
        _row(episode="b", r="-1", exit_reason="STOP"),
    ]
    result = _metrics(rows, extra_friction_r=Decimal("0.05"))
    assert result["total_r"] == "-0.10"


def test_outlier_sensitivity_removes_only_largest_winner() -> None:
    rows = [
        _row(episode="a", r="10", exit_reason="TARGET"),
        _row(episode="b", r="2", exit_reason="TARGET"),
        _row(episode="c", r="-1", exit_reason="STOP"),
    ]
    result = _outlier_sensitivity(rows)
    assert result["largest_winner"]["episode_id"] == "a"
    assert result["largest_winner"]["primary_net_r"] == "10"
    assert (
        result["leave_largest_winner_out"]["primary_0p05R"]["trades"]
        == 2
    )
    assert (
        result["leave_largest_winner_out"]["primary_0p05R"]["total_r"]
        == "1"
    )
