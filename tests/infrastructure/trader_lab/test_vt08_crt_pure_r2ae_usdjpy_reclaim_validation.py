from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2ae_usdjpy_reclaim_validation import (
    EFF5_HIGH,
    EFF5_LOW,
    END,
    MARKET,
    RECLAIM_HIGH,
    RECLAIM_LOW,
    START,
    _accepted_context,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def _context(eff5: str, reclaim: str) -> tuple[object, ...]:
    return (
        Decimal("1"),
        Decimal("1"),
        Decimal("0.1"),
        Decimal(eff5),
        "ALIGNED",
        "ALIGNED",
        "ALIGNED",
        Decimal("0.2"),
        "ALIGNED",
        Decimal("1"),
        Decimal("0.5"),
        Decimal("1"),
        Decimal("0.2"),
        Decimal(reclaim),
    )


def test_r2ae_candidate_bounds_are_frozen() -> None:
    assert MARKET is CrtPureMarket.USDJPY
    assert EFF5_LOW == Decimal("0.10")
    assert EFF5_HIGH == Decimal("0.20")
    assert RECLAIM_LOW == Decimal("0.25")
    assert RECLAIM_HIGH == Decimal("0.50")
    assert _accepted_context(_context("0.15", "0.20"))
    assert not _accepted_context(_context("0.15", "0.30"))
    assert _accepted_context(_context("0.15", "0.50"))
    assert not _accepted_context(_context("0.20", "0.20"))


def test_r2ae_validation_window_is_2014_2018() -> None:
    assert START.isoformat() == "2014-09-21T00:00:00+00:00"
    assert END.isoformat() == "2018-09-21T00:00:00+00:00"
