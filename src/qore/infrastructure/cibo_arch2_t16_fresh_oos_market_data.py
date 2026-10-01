"""Pure read-only market-data transforms for Architect-2 T16 fresh OOS."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_arch2_t16_fresh_oos_utility import (
    T16UtilityObservation,
)


def align_contiguous_m1_returns(
    target: tuple[tuple[datetime, Decimal], ...],
    hedge: tuple[tuple[datetime, Decimal], ...],
) -> tuple[T16UtilityObservation, ...]:
    """Align shared closed M1 bars without bridging missing minutes."""

    target_map = dict(target)
    hedge_map = dict(hedge)
    shared = tuple(sorted(set(target_map) & set(hedge_map)))
    observations: list[T16UtilityObservation] = []
    for previous, current in zip(shared, shared[1:], strict=False):
        if current - previous != timedelta(minutes=1):
            continue
        target_previous = target_map[previous]
        hedge_previous = hedge_map[previous]
        observations.append(
            T16UtilityObservation(
                market_at=current,
                target_return=(target_map[current] / target_previous) - Decimal(1),
                hedge_return=(hedge_map[current] / hedge_previous) - Decimal(1),
            )
        )
    return tuple(observations)


def market_rows_sha256(
    rows: tuple[tuple[datetime, Decimal], ...],
) -> str:
    raw = json.dumps(
        [[at.isoformat(), format(price, "f")] for at, price in rows],
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
