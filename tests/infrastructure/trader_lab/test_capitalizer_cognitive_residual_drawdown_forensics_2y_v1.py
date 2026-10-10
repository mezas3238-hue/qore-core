from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_residual_drawdown_forensics_2y_v1 as residual,
)


def _row(value: str) -> dict[str, object]:
    return {"realized_gross_r": value}


def test_max_drawdown_episode_tracks_peak_to_trough_segment() -> None:
    rows = (
        _row("2"),
        _row("-1"),
        _row("-2"),
        _row("1"),
        _row("-3"),
        _row("4"),
    )

    episode = residual._max_drawdown_episode(rows)

    assert episode.max_drawdown_r == "5"
    assert episode.peak_equity_r == "2"
    assert episode.trough_equity_r == "-3"
    assert episode.peak_after_trade_index == 0
    assert episode.trough_trade_index == 4
    assert episode.segment_start_index == 1
    assert episode.segment_end_index == 4
    assert episode.segment_trade_count == 4


def test_max_drawdown_episode_handles_monotonic_gain() -> None:
    rows = (_row("1"), _row("2"), _row("3"))

    episode = residual._max_drawdown_episode(rows)

    assert episode.max_drawdown_r == "0"
    assert episode.trough_trade_index is None
    assert episode.segment_trade_count == 0
