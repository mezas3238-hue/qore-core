from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_m3_stop_protection_true_2r_v2 as lab,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import Pivot


def test_candidate_stop_is_monotonic_for_long() -> None:
    pivot = Pivot(
        kind="LOW",
        price=Decimal("101"),
        occurred_at=datetime(2026, 1, 5, 10, 3, tzinfo=UTC),
        confirmed_at=datetime(2026, 1, 5, 10, 6, tzinfo=UTC),
    )
    value = lab._candidate_stop(
        pivot=pivot,
        side=CapitalizerSide.LONG,
        entry=Decimal("100"),
        active_stop=Decimal("98"),
        confirmation_close=Decimal("102"),
        profitable_only=True,
    )
    assert value == Decimal("101")


def test_profitable_lock_rejects_long_pivot_below_entry() -> None:
    pivot = Pivot(
        kind="LOW",
        price=Decimal("99"),
        occurred_at=datetime(2026, 1, 5, 10, 3, tzinfo=UTC),
        confirmed_at=datetime(2026, 1, 5, 10, 6, tzinfo=UTC),
    )
    assert (
        lab._candidate_stop(
            pivot=pivot,
            side=CapitalizerSide.LONG,
            entry=Decimal("100"),
            active_stop=Decimal("98"),
            confirmation_close=Decimal("102"),
            profitable_only=True,
        )
        is None
    )


def test_metrics_preserve_full_r_values() -> None:
    rows = (
        lab.SimulatedTrade(
            symbol="NAS100",
            session="NEW_YORK",
            operating_date="2026-01-05",
            side="LONG",
            entry_at="2026-01-05T10:00:00+00:00",
            exit_at="2026-01-05T10:10:00+00:00",
            entry_price="100",
            original_stop_price="99",
            final_stop_price="99",
            target_price="102",
            realized_gross_r="2",
            exit_reason="TARGET",
            mode="ORIGINAL",
            stop_updates=0,
            first_stop_update_at=None,
            same_minute_stop_target_ambiguity=False,
        ),
        lab.SimulatedTrade(
            symbol="NAS100",
            session="NEW_YORK",
            operating_date="2026-01-05",
            side="LONG",
            entry_at="2026-01-05T11:00:00+00:00",
            exit_at="2026-01-05T11:10:00+00:00",
            entry_price="100",
            original_stop_price="99",
            final_stop_price="99.5",
            target_price="102",
            realized_gross_r="-0.5",
            exit_reason="STOP",
            mode="M3_SWING_IMPROVE",
            stop_updates=1,
            first_stop_update_at="2026-01-05T11:06:00+00:00",
            same_minute_stop_target_ambiguity=False,
        ),
    )
    metrics = lab._metrics(rows)
    assert metrics["total_r"] == "1.5"
    assert metrics["profit_factor"] == "4"
    assert metrics["max_drawdown_r"] == "0.5"


def test_m1_bar_contract_still_minute_aligned() -> None:
    opened = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    bar = CapitalizerM1Bar(
        schema_version="capitalizer-cibo-m1-v1",
        symbol="NAS100",
        period="M1",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=Decimal("1"),
    )
    assert bar.closed_at - bar.opened_at == timedelta(minutes=1)
