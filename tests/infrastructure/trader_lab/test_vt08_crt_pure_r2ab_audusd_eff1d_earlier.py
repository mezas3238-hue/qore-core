from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2ab_audusd_eff1d_earlier import (
    END,
    HIGH,
    LOW,
    MARKET,
    START,
    _accept,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2ab_candidate_is_unchanged() -> None:
    assert MARKET is CrtPureMarket.AUDUSD
    assert LOW == Decimal("0.10")
    assert HIGH == Decimal("0.20")
    assert _accept(Decimal("0.10"))
    assert not _accept(Decimal("0.20"))


def test_r2ab_validation_window_is_2016_2018() -> None:
    assert START.isoformat() == "2016-09-21T00:00:00+00:00"
    assert END.isoformat() == "2018-09-21T00:00:00+00:00"
