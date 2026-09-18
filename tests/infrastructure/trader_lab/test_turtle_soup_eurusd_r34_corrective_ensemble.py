from __future__ import annotations

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r34_corrective_ensemble as r34,
)


def test_falsified_family_is_excluded() -> None:
    assert all(r34.F1 not in families for families in r34.FAMILY_SETS.values())
    assert r34.FAMILY_SETS["R34_F234"] == (r34.F2, r34.F3, r34.F4)
    assert r34.FAMILY_SETS["R34_F2345"] == (r34.F2, r34.F3, r34.F4, r34.F5)
