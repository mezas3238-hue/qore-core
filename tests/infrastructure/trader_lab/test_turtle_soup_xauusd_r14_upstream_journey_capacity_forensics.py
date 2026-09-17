from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r14_upstream_journey_capacity_forensics import (
    _ahead,
)


def test_ahead_is_directional() -> None:
    assert _ahead({"entry": "100", "side": "long"}, {"candidate_price": "101"})
    assert not _ahead({"entry": "100", "side": "long"}, {"candidate_price": "99"})
    assert _ahead({"entry": "100", "side": "short"}, {"candidate_price": "99"})
    assert not _ahead({"entry": "100", "side": "short"}, {"candidate_price": "101"})
