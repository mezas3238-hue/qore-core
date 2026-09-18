from __future__ import annotations

from qore.infrastructure.trader_lab.cibo_market_atlas_cross_index_fast_v1 import (
    cross_index_rows,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    cross_index_rows as reference_cross_index_rows,
)


def _row(episode: str, departure: str, side: str) -> dict[str, object]:
    return {"episode_id": episode, "departure_at": departure, "side": side}


def test_binary_search_cross_index_matches_reference_semantics() -> None:
    nas = [
        _row("nas-1", "2025-01-02T14:00:00+00:00", "long"),
        _row("nas-2", "2025-01-02T16:00:00+00:00", "short"),
    ]
    sp = [
        _row("sp-1", "2025-01-02T13:55:00+00:00", "long"),
        _row("sp-2", "2025-01-02T16:05:00+00:00", "short"),
    ]
    us = [
        _row("us-1", "2025-01-02T14:25:00+00:00", "short"),
        _row("us-2", "2025-01-02T20:30:00+00:00", "long"),
    ]

    assert cross_index_rows(nas, sp, us) == reference_cross_index_rows(nas, sp, us)


def test_binary_search_tie_chooses_earlier_departure_like_reference() -> None:
    nas = [_row("nas", "2025-01-02T14:00:00+00:00", "long")]
    sp = [
        _row("sp-before", "2025-01-02T13:55:00+00:00", "long"),
        _row("sp-after", "2025-01-02T14:05:00+00:00", "long"),
    ]
    us = [_row("us", "2025-01-02T14:00:00+00:00", "long")]

    rows = cross_index_rows(nas, sp, us)
    nas_row = next(row for row in rows if row["symbol"] == "NAS100")

    assert nas_row["peer_states"]["SP500"]["episode_id"] == "sp-before"
    assert nas_row["peer_states"]["SP500"]["lead_lag_minutes"] == -5
