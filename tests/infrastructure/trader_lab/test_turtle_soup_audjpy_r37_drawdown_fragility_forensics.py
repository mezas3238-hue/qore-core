from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r37_drawdown_fragility_forensics as r37,
)


def test_r37_is_forensics_on_frozen_owner_gate() -> None:
    assert r37.MIN_TRADES == 350
    assert r37.MIN_PF_010 == Decimal("1.90")
    assert r37.MAX_DD_010 == Decimal("6.0")
    assert set(r37.ENSEMBLES) == {"R37_FORENSIC_BASELINE"}


def test_r37_authority_order_preserves_positive_audjpy_memories() -> None:
    layers = r37.ENSEMBLES["R37_FORENSIC_BASELINE"]
    assert [scheme for scheme, _classes in layers] == [
        r37.CORE,
        r37.DIRECTION,
        r37.TIMEFRAME,
    ]
    assert r37.RANGE_FALSIFIED not in {scheme for scheme, _classes in layers}
