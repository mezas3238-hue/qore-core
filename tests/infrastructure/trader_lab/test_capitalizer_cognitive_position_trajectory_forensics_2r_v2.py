from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_position_trajectory_forensics_2r_v2 as audit,
)


def _row(symbol: str, entry_at: str, value: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "entry_at": entry_at,
        "post_audit_realized_gross_r": value,
    }


def test_max_drawdown_segment_uses_true2r_outcomes() -> None:
    rows = (
        _row("A", "2026-01-01T00:00:00+00:00", "1"),
        _row("B", "2026-01-01T00:01:00+00:00", "-1"),
        _row("C", "2026-01-01T00:02:00+00:00", "-1"),
        _row("D", "2026-01-01T00:03:00+00:00", "0.5"),
    )
    keys, drawdown = audit._max_drawdown_segment(rows)
    assert drawdown == Decimal("2")
    assert keys == {
        ("B", "2026-01-01T00:01:00+00:00"),
        ("C", "2026-01-01T00:02:00+00:00"),
    }


def test_mfe_count_uses_predeclared_r_threshold() -> None:
    rows = (
        audit.True2RTrajectoryRow(
            symbol="AUDJPY",
            session="ASIA",
            operating_date="2026-01-01",
            side="LONG",
            entry_at="2026-01-01T00:00:00+00:00",
            exit_at="2026-01-01T00:10:00+00:00",
            entry_price="100",
            stop_price="99",
            target_price="102",
            realized_gross_r="-1",
            exit_reason="STOP",
            strict_prior_mfe_r="0.49",
            strict_prior_mae_r="0.50",
            confirmed_improving_m3_swing=False,
            confirmed_profitable_m3_swing=False,
            first_improving_m3_confirmed_at=None,
            first_profitable_m3_confirmed_at=None,
            in_true2r_max_drawdown_segment=True,
        ),
        audit.True2RTrajectoryRow(
            symbol="AUDJPY",
            session="ASIA",
            operating_date="2026-01-01",
            side="LONG",
            entry_at="2026-01-01T01:00:00+00:00",
            exit_at="2026-01-01T01:10:00+00:00",
            entry_price="100",
            stop_price="99",
            target_price="102",
            realized_gross_r="-1",
            exit_reason="STOP",
            strict_prior_mfe_r="0.50",
            strict_prior_mae_r="0.50",
            confirmed_improving_m3_swing=True,
            confirmed_profitable_m3_swing=False,
            first_improving_m3_confirmed_at="2026-01-01T01:06:00+00:00",
            first_profitable_m3_confirmed_at=None,
            in_true2r_max_drawdown_segment=True,
        ),
    )
    assert audit._mfe_count(rows, Decimal("0.50")) == 1
    assert all(not row.current_outcome_used_to_discover_trajectory for row in rows)
