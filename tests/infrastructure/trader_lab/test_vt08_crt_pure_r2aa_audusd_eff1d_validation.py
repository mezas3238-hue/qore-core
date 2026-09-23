from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2aa_audusd_eff1d_validation import (
    END,
    HIGH,
    LOW,
    MARKET,
    START,
    _accept,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2aa_candidate_bounds_are_frozen() -> None:
    assert MARKET is CrtPureMarket.AUDUSD
    assert LOW == Decimal("0.10")
    assert HIGH == Decimal("0.20")
    assert _accept(Decimal("0.10"))
    assert _accept(Decimal("0.199999"))
    assert not _accept(Decimal("0.20"))


def test_r2aa_validation_window_is_2018_2020() -> None:
    assert START.isoformat() == "2018-09-21T00:00:00+00:00"
    assert END.isoformat() == "2020-09-21T00:00:00+00:00"
