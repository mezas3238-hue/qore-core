from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.active_perception_v14_observability import (
    V14_CHECKPOINTS_MINUTES,
    V14_EXPECTED_SOURCE_COUNT,
    V14PeerCheckpointQuoteState,
    summarize_v14_cross_peer_observability,
)
from qore.infrastructure.core_stack_v2.active_perception_v14_peer_acquisition import (
    V14PeerFamily,
)


def _states(*, age_ms: int) -> tuple[V14PeerCheckpointQuoteState, ...]:
    rows = []
    for peer in V14PeerFamily:
        for source_index in range(V14_EXPECTED_SOURCE_COUNT):
            for checkpoint in V14_CHECKPOINTS_MINUTES:
                rows.append(
                    V14PeerCheckpointQuoteState(
                        peer=peer,
                        source_index=source_index,
                        checkpoint_minutes=checkpoint,
                        evaluation_at=datetime(2017, 1, 1, tzinfo=UTC),
                        bid_age_ms=age_ms,
                        ask_age_ms=age_ms,
                        bid_relative_price=100,
                        ask_relative_price=101,
                    )
                )
    return tuple(rows)


def test_v14_selects_smallest_shared_threshold() -> None:
    report = summarize_v14_cross_peer_observability(_states(age_ms=9_000))
    assert report["status"] == "source_only_frozen"
    assert report["selected_staleness_limit_ms"] == 10_000


def test_v14_rejects_when_shared_120s_gate_cannot_pass() -> None:
    report = summarize_v14_cross_peer_observability(_states(age_ms=121_000))
    assert report["status"] == "source_only_rejected"
    assert report["selected_staleness_limit_ms"] is None


def test_v14_crossed_quotes_are_not_usable() -> None:
    rows = list(_states(age_ms=1_000))
    rows[0] = V14PeerCheckpointQuoteState(
        peer=rows[0].peer,
        source_index=rows[0].source_index,
        checkpoint_minutes=rows[0].checkpoint_minutes,
        evaluation_at=rows[0].evaluation_at,
        bid_age_ms=1_000,
        ask_age_ms=1_000,
        bid_relative_price=102,
        ask_relative_price=101,
    )
    report = summarize_v14_cross_peer_observability(tuple(rows))
    first = report["threshold_reports"][0]
    first_rows = first["peer_checkpoint"]
    matching = [
        item
        for item in first_rows
        if item["peer"] == V14PeerFamily.SP500.value
        and item["checkpoint_minutes"] == 0
    ][0]
    assert matching["crossed_count"] == 1
    assert matching["usable_count"] == V14_EXPECTED_SOURCE_COUNT - 1
