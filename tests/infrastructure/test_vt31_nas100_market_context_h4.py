from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_nas100_market_context_runtime import (
    build_higher_context,
)

_NY = ZoneInfo("America/New_York")


def _bars(
    start: datetime,
    minutes: int,
    *,
    base: float,
    slope: float,
) -> tuple[object, ...]:
    rows = []
    for index in range(minutes):
        opened = start + timedelta(minutes=index)
        closed = opened + timedelta(minutes=1)
        price = base + slope * index
        rows.append(
            SimpleNamespace(
                opened_at=opened,
                closed_at=closed,
                open=price,
                high=price + 0.5,
                low=max(0.01, price - 0.5),
                close=price,
            )
        )
    return tuple(rows)


def test_h4_uses_prior_causal_history_when_current_day_bucket_is_incomplete() -> None:
    prior = _bars(
        datetime(2026, 10, 5, 0, 0, tzinfo=_NY),
        8 * 60,
        base=100.0,
        slope=0.01,
    )
    current = _bars(
        datetime(2026, 10, 6, 8, 0, tzinfo=_NY),
        2 * 60,
        base=110.0,
        slope=0.01,
    )
    decision_at = datetime(2026, 10, 6, 10, 0, tzinfo=_NY)

    context = build_higher_context(
        day_bars=current,
        prior_admitted_day_bars=prior,
        decision_at=decision_at,
        side="long",
        reference_high=Decimal("112"),
        reference_low=Decimal("108"),
    )

    assert context.h4_state == "bullish"


def test_h4_history_is_separate_from_latest_prior_day_context() -> None:\n    older_a = _bars(\n        datetime(2026, 10, 1, 12, 0, tzinfo=_NY),\n        4 * 60,\n        base=100.0,\n        slope=0.01,\n    )\n    older_b = _bars(\n        datetime(2026, 10, 3, 12, 0, tzinfo=_NY),\n        4 * 60,\n        base=105.0,\n        slope=0.01,\n    )\n    latest_prior = _bars(\n        datetime(2026, 10, 5, 0, 0, tzinfo=_NY),\n        4 * 60,\n        base=120.0,\n        slope=-0.02,\n    )\n    current = _bars(\n        datetime(2026, 10, 6, 8, 0, tzinfo=_NY),\n        2 * 60,\n        base=110.0,\n        slope=0.01,\n    )\n    decision_at = datetime(2026, 10, 6, 10, 0, tzinfo=_NY)\n\n    context = build_higher_context(\n        day_bars=current,\n        prior_admitted_day_bars=latest_prior,\n        prior_h4_history_bars=older_a + older_b,\n        decision_at=decision_at,\n        side="long",\n        reference_high=Decimal("112"),\n        reference_low=Decimal("108"),\n    )\n\n    assert context.prior_day_state == "bearish"\n    assert context.h4_state == "bullish"\n