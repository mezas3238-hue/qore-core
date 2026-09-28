from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_preentry_causal_m1_path_state_v40 as v40,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _bars() -> tuple[CapitalizerM1Bar, ...]:
    start = datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
    rows: list[CapitalizerM1Bar] = []
    for index in range(30):
        opened = start + timedelta(minutes=index)
        open_price = Decimal("100") + Decimal(index) / Decimal("10")
        close = open_price + Decimal("0.04")
        rows.append(
            CapitalizerM1Bar(
                symbol="EURUSD",
                opened_at=opened,
                closed_at=opened + timedelta(minutes=1),
                open=open_price,
                high=close + Decimal("0.03"),
                low=open_price - Decimal("0.02"),
                close=close,
                volume=100 + index,
                digits=5,
            )
        )
    return tuple(rows)


def test_v40_path_is_exactly_preentry_and_18d() -> None:
    entry_at = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    row = v40.build_path_state(
        symbol="EURUSD",
        side="LONG",
        entry_at=entry_at,
        risk_price=Decimal("1"),
        bars=_bars(),
    )

    assert row.feature_names == v40.FEATURE_NAMES
    assert row.feature_count == len(v40.FEATURE_NAMES) == 18
    assert row.bars_used == 30
    assert row.feature_timestamp_max == entry_at.isoformat()
    assert row.entry_bar_used is False
    assert row.future_bar_used is False
    assert row.outcome_used is False
    assert row.exit_used is False
    assert row.mae_mfe_used is False
    assert Decimal(row.vector[0]) > 0
    assert Decimal(row.vector[10]) > 0
    assert Decimal(row.vector[15]) > Decimal("0.5")


def test_v40_rejects_gap_inside_30m_path() -> None:
    bars = list(_bars())
    shifted = bars[12]
    bars[12] = CapitalizerM1Bar(
        symbol=shifted.symbol,
        opened_at=shifted.opened_at + timedelta(minutes=1),
        closed_at=shifted.closed_at + timedelta(minutes=1),
        open=shifted.open,
        high=shifted.high,
        low=shifted.low,
        close=shifted.close,
        volume=shifted.volume,
        digits=shifted.digits,
    )

    with pytest.raises(ValueError, match="gap"):
        v40.build_path_state(
            symbol="EURUSD",
            side="LONG",
            entry_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
            risk_price=Decimal("1"),
            bars=tuple(bars),
        )


def test_v40_rejects_entry_bar() -> None:
    bars = list(_bars())
    last = bars[-1]
    bars[-1] = CapitalizerM1Bar(
        symbol=last.symbol,
        opened_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
        closed_at=datetime(2026, 1, 5, 10, 1, tzinfo=UTC),
        open=last.open,
        high=last.high,
        low=last.low,
        close=last.close,
        volume=last.volume,
        digits=last.digits,
    )

    with pytest.raises(ValueError):
        v40.build_path_state(
            symbol="EURUSD",
            side="LONG",
            entry_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
            risk_price=Decimal("1"),
            bars=tuple(bars),
        )


def test_v40_json_roundtrip_restores_tuple_contract() -> None:
    row = v40.build_path_state(
        symbol="EURUSD",
        side="SHORT",
        entry_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
        risk_price=Decimal("1"),
        bars=_bars(),
    )
    payload = json.loads(json.dumps(v40.as_json_dict(row)))

    assert isinstance(payload["feature_names"], list)
    assert isinstance(payload["vector"], list)
    assert v40.from_json_dict(payload) == row
