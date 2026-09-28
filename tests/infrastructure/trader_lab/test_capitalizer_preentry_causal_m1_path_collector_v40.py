from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_preentry_causal_m1_path_collector_v40 as collector,
)
from qore.infrastructure.trader_lab import (
    capitalizer_preentry_causal_m1_path_state_v40 as state,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _bars() -> tuple[CapitalizerM1Bar, ...]:
    start = datetime(2026, 1, 5, 9, 30, tzinfo=UTC)
    return tuple(
        CapitalizerM1Bar(
            symbol="EURUSD",
            opened_at=start + timedelta(minutes=index),
            closed_at=start + timedelta(minutes=index + 1),
            open=Decimal("100") + Decimal(index) / Decimal("10"),
            high=Decimal("100.10") + Decimal(index) / Decimal("10"),
            low=Decimal("99.95") + Decimal(index) / Decimal("10"),
            close=Decimal("100.05") + Decimal(index) / Decimal("10"),
            volume=100 + index,
            digits=5,
        )
        for index in range(30)
    )


def _selected() -> collector.SelectedPathState:
    path = state.build_path_state(
        symbol="EURUSD",
        side="LONG",
        entry_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
        risk_price=Decimal("1"),
        bars=_bars(),
    )
    return collector.SelectedPathState(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at=path.entry_at,
        provenance="CAUSAL_ARBITRATION_BASE",
        path=path,
    )


def test_exact_path_bars_ends_at_entry() -> None:
    bars = _bars()
    by_open = {bar.opened_at: bar for bar in bars}
    selected = collector._path_bars(
        by_open,
        entry_at=datetime(2026, 1, 5, 10, 0, tzinfo=UTC),
    )

    assert selected == bars
    assert selected[-1].closed_at == datetime(
        2026, 1, 5, 10, 0, tzinfo=UTC
    )


def test_load_path_rows_rehydrates_nested_tuple_contract(tmp_path: Path) -> None:
    row = _selected()
    path = tmp_path / "capitalizer-v40-development-eurusd-path.jsonl"
    path.write_text(json.dumps(asdict(row)) + "\n", encoding="utf-8")

    loaded = collector.load_path_rows(tmp_path, slug="development")

    assert loaded == {(row.symbol, row.entry_at): row}
