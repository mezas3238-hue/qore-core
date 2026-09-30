from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_gross_economics_v47_s2b as s2b,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide


def _tick(second: int, price: str) -> s0.DecodedProviderTick:
    return s0.DecodedProviderTick(
        observed_at=datetime(2026, 1, 1, 10, 0, second, tzinfo=UTC),
        price=Decimal(price),
    )


def _trade(value: str, *, reason: str = "SESSION_EXIT") -> s2b.S2BGrossTrade:
    return s2b.S2BGrossTrade(
        identity=s2b.IDENTITY,
        source_identity=s2b.SOURCE_S2A_IDENTITY,
        period="development",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-01",
        side="LONG",
        route="FRACTAL_SCALP_CONTINUATION",
        entry_at="2026-01-01T10:00:00+00:00",
        entry_price="100",
        stop_price="99",
        target_price="102",
        initial_risk_price="1",
        target_r="2",
        exit_at="2026-01-01T10:30:00+00:00",
        exit_price=str(Decimal("100") + Decimal(value)),
        exit_reason=reason,
        realized_gross_r=value,
        m1_bars_held=30,
        exact_exit_ticks_required=False,
        stop_first_fallback_used=False,
    )


def test_first_exact_exit_respects_tick_chronology() -> None:
    ticks = (
        _tick(1, "100.2"),
        _tick(2, "102.1"),
        _tick(3, "98.9"),
    )
    result = s2b._first_exact_exit(
        ticks,
        side=CapitalizerSide.LONG,
        stop=Decimal("99"),
        target=Decimal("102"),
    )
    assert result is not None
    reason, at, price = result
    assert reason == "TARGET"
    assert at == ticks[1].observed_at
    assert price == Decimal("102")


def test_r_law_is_directionally_symmetric() -> None:
    assert s2b._risk(
        side=CapitalizerSide.LONG,
        entry=Decimal("100"),
        stop=Decimal("99"),
    ) == Decimal("1")
    assert s2b._risk(
        side=CapitalizerSide.SHORT,
        entry=Decimal("100"),
        stop=Decimal("101"),
    ) == Decimal("1")
    assert s2b._realized_r(
        side=CapitalizerSide.LONG,
        entry=Decimal("100"),
        exit_price=Decimal("102"),
        risk=Decimal("1"),
    ) == Decimal("2")
    assert s2b._realized_r(
        side=CapitalizerSide.SHORT,
        entry=Decimal("100"),
        exit_price=Decimal("98"),
        risk=Decimal("1"),
    ) == Decimal("2")


def test_metrics_preserve_sequence_drawdown_and_pf() -> None:
    rows = (
        _trade("2", reason="TARGET"),
        _trade("-1", reason="STOP"),
        _trade("-1", reason="STOP"),
        _trade("1", reason="SESSION_EXIT"),
    )
    report = s2b.metrics(rows)
    assert report.trades == 4
    assert report.wins == 2
    assert report.losses == 2
    assert Decimal(report.total_r) == Decimal("1")
    assert Decimal(report.gross_profit_r) == Decimal("3")
    assert Decimal(report.gross_loss_r) == Decimal("2")
    assert Decimal(report.profit_factor or "0") == Decimal("1.5")
    assert Decimal(report.max_drawdown_r) == Decimal("2")
    assert report.max_losing_streak == 2
    assert report.target_exits == 1
    assert report.stop_exits == 2
    assert report.session_exits == 1


def test_trade_row_rejects_certification_or_mutation() -> None:
    with pytest.raises(ValueError, match="governance drift"):
        s2b.S2BGrossTrade(
            identity=s2b.IDENTITY,
            source_identity=s2b.SOURCE_S2A_IDENTITY,
            period="development",
            symbol="EURUSD",
            session="LONDON",
            operating_date="2026-01-01",
            side="LONG",
            route="FRACTAL_SCALP_CONTINUATION",
            entry_at="2026-01-01T10:00:00+00:00",
            entry_price="100",
            stop_price="99",
            target_price="102",
            initial_risk_price="1",
            target_r="2",
            exit_at="2026-01-01T10:30:00+00:00",
            exit_price="102",
            exit_reason="TARGET",
            realized_gross_r="2",
            m1_bars_held=30,
            exact_exit_ticks_required=False,
            stop_first_fallback_used=False,
            trader_certified=True,
        )
