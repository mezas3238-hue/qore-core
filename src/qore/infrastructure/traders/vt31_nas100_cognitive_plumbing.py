"""Causal plumbing helpers for VT31 NAS100 cognitive inputs."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.traders.vt31_nas100_cibo_causal_structure import (
    causal_structure_events,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22SourceSetup,
)

_LIQUIDITY_EVENT_FAMILIES = frozenset(
    {"reference-liquidity-sweep", "local-liquidity-sweep"}
)


def recent_liquidity_event_count_10m(
    path: Sequence[OhlcSnapshot],
    source: Vt31R22SourceSetup,
    decision_at: datetime,
) -> int:
    """Count already-observable liquidity sweeps in the trailing 10 minutes."""

    window_start = decision_at - timedelta(minutes=10)
    return sum(
        event.family in _LIQUIDITY_EVENT_FAMILIES
        and window_start <= event.observed_at <= decision_at
        for event in causal_structure_events(path, source, decision_at)
    )
