"""True closed-bar as-of nine-market synchronizer has no forward M1 or quote flags."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_a1_native_nine_market_bar_witness_v1 import (
    A1NativeMarketObservation,
    observe_market_asof,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _bar(at: datetime) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="AUDJPY", opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal("100.000"), high=Decimal("100.100"),
        low=Decimal("99.900"), close=Decimal("100.040"),
        volume=None, digits=3,
    )


def test_witness_never_reads_unfinished_native_m1_or_fabricates_quotes() -> None:
    at = datetime(2026, 1, 5, tzinfo=UTC)
    bars = (_bar(at), _bar(at + timedelta(minutes=2)))
    decisions = (
        at,
        at + timedelta(minutes=1),
        at + timedelta(minutes=2),
        at + timedelta(minutes=3),
    )
    out = observe_market_asof(
        symbol="AUDJPY", decision_times=decisions, bars=bars
    )
    assert len(out) == 4
    assert not out[0].has_exact_predecision_m1
    assert out[0].last_native_m1_closed_at is None
    assert out[1].has_exact_predecision_m1
    assert not out[2].has_exact_predecision_m1
    assert out[2].last_native_m1_closed_at == decisions[1].isoformat()
    assert out[3].has_exact_predecision_m1
    assert all(not row.bid_ask_quote_available for row in out)
    assert all(not row.regime_attested for row in out)
    assert all(not row.full_master_frame_attested for row in out)


def test_witness_rejects_future_unknown_market_duplicate_event() -> None:
    at = datetime(2026, 1, 5, tzinfo=UTC)
    with pytest.raises(ValueError, match="chronological"):
        observe_market_asof(
            symbol="AUDJPY", decision_times=(at + timedelta(minutes=1), at),
            bars=(_bar(at),),
        )
    with pytest.raises(ValueError, match="unique"):
        observe_market_asof(
            symbol="AUDJPY", decision_times=(at, at), bars=(_bar(at),)
        )
    with pytest.raises(ValueError, match="future M1"):
        A1NativeMarketObservation(
            symbol="AUDJPY", decision_at=at.isoformat(),
            last_native_m1_opened_at=at.isoformat(),
            last_native_m1_closed_at=(
                at + timedelta(minutes=1)
            ).isoformat(),
            last_completed_close="100", has_exact_predecision_m1=False,
        )
    with pytest.raises(ValueError, match="market symbol"):
        observe_market_asof(
            symbol="USDJPY", decision_times=(at,), bars=(_bar(at),)
        )
