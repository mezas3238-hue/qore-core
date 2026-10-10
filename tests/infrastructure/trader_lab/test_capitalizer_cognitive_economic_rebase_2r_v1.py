from __future__ import annotations

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)


def _row(
    *,
    symbol: str,
    side: str,
    entry_at: str,
    exit_at: str,
    realized_r: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": "LONDON",
        "operating_date": "2026-01-05",
        "side": side,
        "h1_open": "2026-01-05T09:00:00+00:00",
        "h1_deadline": "2026-01-05T10:00:00+00:00",
        "entry_at": entry_at,
        "entry_price": "1",
        "stop_price": "0.9",
        "target_r": "2.00",
        "target_price": "1.2",
        "exit_at": exit_at,
        "realized_gross_r": realized_r,
        "exit_reason": "TARGET" if realized_r == "2" else "STOP",
        "same_minute_stop_target_ambiguity": False,
        "provenance": "CAUSAL_ARBITRATION_BASE",
    }


def test_dynamic_context_uses_only_prior_2r_lifecycle() -> None:
    first = _row(
        symbol="EURUSD",
        side="LONG",
        entry_at="2026-01-05T09:00:00+00:00",
        exit_at="2026-01-05T09:15:00+00:00",
        realized_r="2",
    )
    second = _row(
        symbol="GBPUSD",
        side="LONG",
        entry_at="2026-01-05T09:10:00+00:00",
        exit_at="2026-01-05T09:30:00+00:00",
        realized_r="-1",
    )
    current = _row(
        symbol="EURUSD",
        side="SHORT",
        entry_at="2026-01-05T09:20:00+00:00",
        exit_at="2026-01-05T09:40:00+00:00",
        realized_r="-1",
    )

    context = rebase._dynamic_context(current, (first, second, current))

    assert context["baseline_active_positions"] == 1
    assert context["prior_closed_trades_today"] == 1
    assert context["prior_realized_r_today"] == "2"
    assert context["prior_same_session_selected"] == 2
    assert context["session_slots_remaining_before"] == 1
    assert "USD" in context["baseline_shared_factors"]


def test_simultaneous_candidate_is_not_prior_active_exposure() -> None:
    peer = _row(
        symbol="AUDJPY",
        side="SHORT",
        entry_at="2026-01-05T09:20:00+00:00",
        exit_at="2026-01-05T09:40:00+00:00",
        realized_r="-1",
    )
    current = _row(
        symbol="GBPJPY",
        side="SHORT",
        entry_at="2026-01-05T09:20:00+00:00",
        exit_at="2026-01-05T09:45:00+00:00",
        realized_r="-1",
    )

    context = rebase._dynamic_context(current, (peer, current))

    assert context["baseline_active_positions"] == 0
    assert context["baseline_shared_factors"] == []
    assert context["prior_closed_trades_today"] == 0
    assert context["prior_same_session_selected"] == 0
    assert context["session_slots_remaining_before"] == 3
