"""Causal CIBO-equivalent structure events for VT31_NAS100.

Repairs two timestamp defects discovered in the consumed Eight-Ledger V1:

1. Liquidity sweeps require the bar close to establish a reclaim. Therefore the
   event cannot be known at bar open time.
2. A PD-array cannot be considered touched before it exists. A same-bar overlap
   is actionable no earlier than its formation time; later M1 touches are
   observable no earlier than the touching bar close.

This module consumes only closed M1 evidence no later than decision_at.
It does not reproduce known post-outcome timestamp leakage for the sake of
matching a legacy artifact.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22SourceSetup,
)


@dataclass(frozen=True, slots=True)
class CausalStructureEvent:
    observed_at: datetime
    family: str
    source: str

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("causal structure event requires aware timestamp")
        if not self.family:
            raise ValueError("causal structure event requires family")
        if not self.source:
            raise ValueError("causal structure event requires source")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _touches_zone(bar: OhlcSnapshot, candidate: Vt31R22EntryEvidence) -> bool:
    return (
        _d(bar.high) >= candidate.zone_lower
        and _d(bar.low) <= candidate.zone_upper
    )


def pd_array_events(
    path: Sequence[OhlcSnapshot],
    source: Vt31R22SourceSetup,
    decision_at: datetime,
) -> tuple[CausalStructureEvent, ...]:
    events: list[CausalStructureEvent] = []
    for candidate in source.candidates:
        if candidate.formed_at > decision_at:
            continue
        for bar in path:
            if bar.closed_at < candidate.formed_at:
                continue
            if bar.closed_at > decision_at:
                break
            if not _touches_zone(bar, candidate):
                continue
            observed_at = max(candidate.formed_at, bar.closed_at)
            events.append(
                CausalStructureEvent(
                    observed_at=observed_at,
                    family=candidate.family.value,
                    source="pd-array-touch-closed-m1",
                )
            )
            break
    return tuple(events)


def reference_sweep_events(
    path: Sequence[OhlcSnapshot],
    source: Vt31R22SourceSetup,
    decision_at: datetime,
) -> tuple[CausalStructureEvent, ...]:
    events: list[CausalStructureEvent] = []
    for bar in path:
        if bar.closed_at > decision_at:
            break
        high = _d(bar.high)
        low = _d(bar.low)
        close = _d(bar.close)
        if high > source.reference.high and close < source.reference.high:
            events.append(
                CausalStructureEvent(
                    observed_at=bar.closed_at,
                    family="reference-liquidity-sweep",
                    source="high-raid-close-reclaim",
                )
            )
        if low < source.reference.low and close > source.reference.low:
            events.append(
                CausalStructureEvent(
                    observed_at=bar.closed_at,
                    family="reference-liquidity-sweep",
                    source="low-raid-close-reclaim",
                )
            )
    return tuple(events)


def _confirmed_local_swing_indices(
    path: Sequence[OhlcSnapshot],
) -> tuple[list[int], list[int]]:
    highs: list[int] = []
    lows: list[int] = []
    for index in range(2, len(path) - 2):
        high = _d(path[index].high)
        low = _d(path[index].low)
        if (
            high >= max(_d(path[index - 2].high), _d(path[index - 1].high))
            and high > max(_d(path[index + 1].high), _d(path[index + 2].high))
        ):
            highs.append(index)
        if (
            low <= min(_d(path[index - 2].low), _d(path[index - 1].low))
            and low < min(_d(path[index + 1].low), _d(path[index + 2].low))
        ):
            lows.append(index)
    return highs, lows


def local_sweep_events(
    path: Sequence[OhlcSnapshot],
    decision_at: datetime,
) -> tuple[CausalStructureEvent, ...]:
    events: list[CausalStructureEvent] = []
    highs, lows = _confirmed_local_swing_indices(path)
    for index, bar in enumerate(path):
        if bar.closed_at > decision_at:
            break
        prior_highs = [item for item in highs if item <= index - 2]
        prior_lows = [item for item in lows if item <= index - 2]
        if prior_highs:
            level = _d(path[prior_highs[-1]].high)
            if _d(bar.high) > level and _d(bar.close) < level:
                events.append(
                    CausalStructureEvent(
                        observed_at=bar.closed_at,
                        family="local-liquidity-sweep",
                        source="confirmed-local-high-sweep-close-reclaim",
                    )
                )
        if prior_lows:
            level = _d(path[prior_lows[-1]].low)
            if _d(bar.low) < level and _d(bar.close) > level:
                events.append(
                    CausalStructureEvent(
                        observed_at=bar.closed_at,
                        family="local-liquidity-sweep",
                        source="confirmed-local-low-sweep-close-reclaim",
                    )
                )
    return tuple(events)


def causal_structure_events(
    path: Sequence[OhlcSnapshot],
    source: Vt31R22SourceSetup,
    decision_at: datetime,
) -> tuple[CausalStructureEvent, ...]:
    safe_path = tuple(bar for bar in path if bar.closed_at <= decision_at)
    events = [
        *pd_array_events(safe_path, source, decision_at),
        *local_sweep_events(safe_path, decision_at),
        *reference_sweep_events(safe_path, source, decision_at),
    ]
    return tuple(
        sorted(
            events,
            key=lambda event: (
                event.observed_at,
                (
                    2
                    if event.family == "reference-liquidity-sweep"
                    else 1
                    if event.family == "local-liquidity-sweep"
                    else 0
                ),
            ),
        )
    )


def last_causal_structure_event(
    path: Sequence[OhlcSnapshot],
    source: Vt31R22SourceSetup,
    decision_at: datetime,
) -> tuple[str, int | None]:
    events = causal_structure_events(path, source, decision_at)
    if not events:
        return "none", None
    event = events[-1]
    age = max(
        0,
        int((decision_at - event.observed_at).total_seconds() // 60),
    )
    return event.family, age
