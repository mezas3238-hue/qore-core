"""Four additional CRT family research lanes: independent geometry audit.

Calls source-grounded closed-H4 geometry, not a copied base MSS.
Retest MAY cite the verified MSS15 of its parent CRT, never another cycle.
Events have distinct source and are OBSERVE-ONLY, NEVER trading orders.
M5-specific MSS finite state machines for Inside/Multi remain future gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from research.crt_r4a_holdout.pine_h4_geometry import ClosedH4
from research.crt_r4a_holdout.pine_swing_primitives import M15Close
from research.crt_r4a_holdout.secondary_family_geometry import (
    Geometry,
    RetestSource,
    inside_return,
    multi4,
    multi_n,
    retest_m15,
)
from research.crt_r4a_holdout.seven_family_contract import Family


class Parent2C(Protocol):
    identity: str
    model: str
    side: str
    c1_at: datetime
    mss_at: datetime
    mss_pivot: float
    ratified_at: datetime


@dataclass(frozen=True)
class ObservedFamily:
    family: Family
    c1_at: datetime
    ratified_at: datetime
    direction: int
    source_parent_id: str | None = None
    has_parent_owned_mss: bool = False
    independently_mss_certified: bool = False
    broker_orders_executed: int = 0


class SecondaryGeometryObserver:
    """Observe separately 4 families, no inherited CRT base pivot."""

    def __init__(self, family: str) -> None:
        if family not in ("forex", "index", "btc"):
            raise ValueError("R4-A family required")
        self.family = family
        self.history: list[ClosedH4] = []
        self.events: list[ObservedFamily] = []
        self._seen: set[tuple[Family, datetime, datetime]] = set()
        self._retested_parents: set[str] = set()

    def _register(
        self, family: Family, g: Geometry, *,
        parent: str | None = None,
        own_parent_mss: bool = False,
    ) -> None:
        key = (family, g.c1_at, g.ratified_at)
        if key in self._seen:
            return
        self._seen.add(key)
        self.events.append(ObservedFamily(
            family, g.c1_at, g.ratified_at, g.direction,
            parent, own_parent_mss,
            # Geometry, even after a retest of parent MSS, is not a
            # certified own independent MSS.
            False,
        ))

    def on_closed_h4(self, closed: ClosedH4 | None) -> None:
        if closed is None or not closed.valid:
            self.history.clear()
            return
        self.history.append(closed)
        self.history = self.history[-7:]
        h = self.history
        if len(h) >= 3:
            g = inside_return(h[-3], h[-2], h[-1], self.family)
            if g is not None:
                self._register(Family.INSIDE_RETURN, g)
        if len(h) >= 4:
            g = multi4(h[-4], h[-3], h[-2], h[-1], self.family)
            if g is not None:
                self._register(Family.MULTI4, g)
            # R4-A selects the nearest viable C1 (smallest N first).
            for n in range(4, min(7, len(h)) + 1):
                g = multi_n(tuple(h[-n:]), self.family)
                if g is not None:
                    self._register(Family.MULTIN, g)
                    break

    def on_m15_retest(
        self, closed: M15Close | None, base_events: list[Parent2C]
    ) -> None:
        if closed is None:
            return
        for event in reversed(base_events):
            if (
                event.model != "A_2C_MSS15"
                or event.identity in self._retested_parents
            ):
                continue
            # The base detector is the sole owner of this pivot/MSS.
            parent = RetestSource(
                event.c1_at,
                1 if event.side == "LONG" else -1,
                event.mss_at, event.mss_pivot,
                event.ratified_at,
            )
            g = retest_m15(parent, closed, linked_c1_at=event.c1_at)
            if g is not None:
                self._register(
                    Family.M15_RETEST, g,
                    parent=event.identity, own_parent_mss=True
                )
                self._retested_parents.add(event.identity)

    def readout(self) -> dict[str, object]:
        names = (
            Family.INSIDE_RETURN, Family.MULTI4,
            Family.MULTIN, Family.M15_RETEST,
        )
        counts = {
            name.value: sum(e.family == name for e in self.events)
            for name in names
        }
        return {
            "status": "FOUR_EXTRA_CRT_FAMILY_GEOMETRIES_OBSERVE_ONLY",
            "family_geometry_event_counts": counts,
            "total_geometry_only_events": len(self.events),
            "family_own_mss_state_machines_certified": False,
            "trades_executed": 0,
            "pine_parity_certified": False,
        }
