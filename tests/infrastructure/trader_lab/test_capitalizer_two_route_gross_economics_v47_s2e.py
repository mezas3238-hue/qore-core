from __future__ import annotations

from dataclasses import asdict

from qore.infrastructure.trader_lab import (
    capitalizer_two_route_gross_economics_v47_s2e as s2e,
)


def _trade(value: str, *, stream: str, reason: str) -> s2e.S2EGrossTrade:
    return s2e.S2EGrossTrade(
        identity=s2e.IDENTITY,
        source_population_identity=(
            "QORE_CAPITALIZER_V47_S2D_TWO_ROUTE_POPULATION_FREEZE"
        ),
        source_stream=stream,
        period="development",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        route=(
            "FRACTAL_SCALP_CONTINUATION"
            if stream == "FRACTAL"
            else "FAILURE_TO_MANIPULATE_CONTINUATION"
        ),
        entry_at="2026-01-05T08:00:00+00:00",
        entry_price="100",
        stop_price="99",
        target_price="103",
        initial_risk_price="1",
        target_r="3",
        exit_at="2026-01-05T09:00:00+00:00",
        exit_price=str(100 + float(value)),
        exit_reason=reason,
        realized_gross_r=value,
        m1_bars_held=60,
        exact_exit_ticks_required=False,
        stop_first_fallback_used=False,
    )


def test_metrics_mix_routes_without_route_priority() -> None:
    rows = (
        _trade("2", stream="FRACTAL", reason="TARGET"),
        _trade("-1", stream="FTM", reason="STOP"),
        _trade("1", stream="FTM", reason="SESSION_EXIT"),
    )
    report = s2e.metrics(rows)
    assert report.trades == 3
    assert report.wins == 2
    assert report.losses == 1
    assert report.total_r == "2"
    assert report.profit_factor == "3"
    assert report.max_drawdown_r == "1"


def test_gross_trade_rejects_route_priority() -> None:
    row = _trade("1", stream="FTM", reason="TARGET")
    payload = asdict(row)
    payload["route_priority_used"] = True
    try:
        s2e.S2EGrossTrade(**payload)
    except ValueError:
        return
    raise AssertionError("S2E must reject route-priority selection")
