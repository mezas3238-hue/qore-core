from __future__ import annotations

from qore.infrastructure.trader_lab.turtle_soup_xauusd_r13_intelligence_alignment_forensics import (
    _ahead,
    _route_match,
)


def test_route_match_maps_cibo_families() -> None:
    trade = {"target_route": "SWING_H4"}
    assert _route_match(
        trade,
        {
            "candidate_type": "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
            "source_timeframe": "H4",
        },
    )
    assert not _route_match(
        trade,
        {
            "candidate_type": "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY",
            "source_timeframe": "H4",
        },
    )


def test_ahead_respects_side() -> None:
    assert _ahead(
        {"entry": "100", "side": "long"},
        {"candidate_price": "101"},
    )
    assert not _ahead(
        {"entry": "100", "side": "long"},
        {"candidate_price": "99"},
    )
    assert _ahead(
        {"entry": "100", "side": "short"},
        {"candidate_price": "99"},
    )
    assert not _ahead(
        {"entry": "100", "side": "short"},
        {"candidate_price": "101"},
    )
