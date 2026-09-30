from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_post_third_slot_preentry_atlas_2y_v1 as post,
)


def _row(value: str, reason: str) -> dict[str, object]:
    return {
        "realized_gross_r": value,
        "exit_reason": reason,
    }


def test_metrics_preserve_ordered_drawdown() -> None:
    rows = (
        _row("2", "TARGET"),
        _row("-1", "STOP"),
        _row("-2", "STOP"),
        _row("1", "TARGET"),
    )

    metrics = post._metrics(rows)

    assert metrics["trades"] == 4
    assert metrics["wins"] == 2
    assert metrics["losses"] == 2
    assert metrics["stops"] == 2
    assert metrics["total_r"] == "0"
    assert metrics["max_drawdown_r"] == "3"
