"""Immutable-by-export seven-family structural event tape (research only).

Source detector counts are NOT prices, fills, strategy orders or evidence of
Pine parity. These records keep individual event identity/closed-bar times and
family-owned source geometry, and explicitly mark absent pricing prerequisites.
Provider-sourced M5 OHLC is not equivalent to historical bid/ask.
NO BROKER API, NO DEMO/LIVE ORDERS, NO CERTIFICATION.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from research.crt_r4a_holdout.causal_crt_m5_engine import CausalCRTM5
from research.crt_r4a_holdout.seven_family_contract import (
    Family,
    research_family_from_base_event,
)

PINE_BLOB = "693e3f49719e86e2ea0702f7b355af33bd0c4c7c"
SCHEMA = "QORE_CRT_R4A_SEVEN_FAMILY_STRUCTURAL_EVENT_V1"
ALIASES = {"NAS100": "USTEC", "SP500": "US500"}
COHORTS = frozenset((
    "ATLAS_DEMO_BROKER_UNVERIFIED", "ICMARKETS_DEMO_CONFIRMED",
))
GATES_NOT_SATISFIED = (
    "ORIGINAL_PINE_F_ENGINE_PARITY",
    "OWN_CLOSED_H4_SETUP_OPEN_AND_ATR14_PRICE_TICK",
    "SOURCE_MATCHED_HISTORICAL_BID_ASK",
    "VERIFIED_CONTRACT_CURRENCY_AND_BROKER_COSTS",
    "24_MONTH_UNSEEN_HOLDOUT",
)


def _dt(t: datetime) -> str:
    if t.tzinfo is None:
        raise ValueError("source event timestamps must be offset-aware")
    return t.isoformat()


def _price(x: float) -> str:
    if not isinstance(x, (int, float)) or x <= 0:
        raise ValueError("source geometry must contain actual positive price")
    return repr(x)


def build_event_tape(
    engine: CausalCRTM5, *, provider_cohort: str
) -> list[dict[str, Any]]:
    """Reconcile all seven pathways against original independent source events.

    No missing geometry is interpolated and no event is auto-upgraded to a
    FrozenResearchSignal / hypothetical trade. Unavailable prices are omitted.
    """
    if provider_cohort not in COHORTS:
        raise ValueError("unregistered provider evidence cohort")
    expected = engine.readout()["seven_family_research_event_counts"]
    symbol = engine.symbol
    base = {e.identity: e for e in engine.evidence}
    if len(base) != len(engine.evidence):
        raise ValueError("duplicate primary CRT event source identities")
    records: list[dict[str, Any]] = []

    def new(
        family: Family, event_id: str, *,
        direction: int, c1_at: datetime, mss_at: datetime,
        ratified_at: datetime, available_at: datetime,
        provenance: str, parent_id: str | None = None,
    ) -> dict[str, Any]:
        if (
            direction not in (1, -1) or not event_id
            or not c1_at < available_at
            or not mss_at <= available_at
            or not ratified_at <= available_at
        ):
            raise ValueError("noncausal or incomplete seven-family event")
        return {
            "schema": SCHEMA,
            "source_pine_blob": PINE_BLOB,
            "symbol": ALIASES.get(symbol, symbol),
            "original_provider_symbol": symbol,
            "provider_cohort": provider_cohort,
            "family": family.value,
            "source_event_id": event_id,
            "direction": direction,
            "c1_at": _dt(c1_at),
            "mss_at": _dt(mss_at),
            "ratified_at": _dt(ratified_at),
            "available_at": _dt(available_at),
            "source_ownership": provenance,
            "parent_event_id": parent_id,
            "geometry": {},
            "economic_ready": False,
            "missing_certification_gates": list(GATES_NOT_SATISFIED),
            "broker_orders_executed": 0,
        }

    for e in engine.evidence:
        if e.symbol != symbol or e.side not in ("LONG", "SHORT"):
            raise ValueError("base CRT source ownership mismatch")
        if not e.sweep_at < e.mss_at <= e.available_at:
            raise ValueError("base CRT sweep/MSS timing invalid")
        family = research_family_from_base_event(
            model=e.model, mss_at=e.mss_at, ratified_at=e.ratified_at
        )
        rec = new(
            family, e.identity,
            direction=1 if e.side == "LONG" else -1,
            c1_at=e.c1_at, mss_at=e.mss_at,
            ratified_at=e.ratified_at, available_at=e.available_at,
            provenance="OWN_BASE_CRT_FROZEN_MSS",
        )
        rec["sweep_at"] = _dt(e.sweep_at)
        rec["mss_pivot"] = _price(e.mss_pivot)
        rec["geometry"] = {
            "c1_high": _price(e.c1_high),
            "c1_low": _price(e.c1_low),
            "sweep_high": _price(e.sweep_high),
            "sweep_low": _price(e.sweep_low),
        }
        records.append(rec)

    known = {
        (g.family, g.c1_at, g.ratified_at, g.direction)
        for g in engine.secondary.events
    }
    for e in engine.secondary_mss.events:
        if e.symbol != symbol or e.side not in ("LONG", "SHORT"):
            raise ValueError("secondary MSS source ownership mismatch")
        side = 1 if e.side == "LONG" else -1
        if (
            (e.family, e.c1_at, e.ratified_at, side) not in known
            or e.family not in (
                Family.INSIDE_RETURN, Family.MULTI4, Family.MULTIN
            )
            or not e.own_pivot_at < e.sweep_at < e.own_mss15_at
            or e.own_mss15_at > e.available_at
        ):
            raise ValueError("unmatched own H4/auxiliary MSS event")
        rec = new(
            e.family, e.identity, direction=side,
            c1_at=e.c1_at, mss_at=e.own_mss15_at,
            ratified_at=e.ratified_at, available_at=e.available_at,
            provenance="OWN_SECONDARY_MSS15_FROZEN_PRE_SWEEP_PIVOT",
        )
        if None in (
            e.c1_high, e.c1_low, e.terminal_high, e.terminal_low,
            e.terminal_close
        ):
            raise ValueError("secondary source event missing own H4 evidence")
        rec["sweep_at"] = _dt(e.sweep_at)
        rec["mss_pivot"] = _price(e.own_pivot_price)
        rec["mss_pivot_at"] = _dt(e.own_pivot_at)
        rec["geometry"] = {
            "c1_high": _price(e.c1_high),
            "c1_low": _price(e.c1_low),
            "terminal_high": _price(e.terminal_high),
            "terminal_low": _price(e.terminal_low),
            "terminal_close": _price(e.terminal_close),
        }
        # Terminal H4 is not necessarily the Multi4 C2a sweep candle.
        # Do not mislabel terminal wick as the family's sweep extreme.
        records.append(rec)

    for g in engine.secondary.events:
        if g.family != Family.M15_RETEST:
            continue
        parent = base.get(g.source_parent_id or "")
        if (
            parent is None or parent.model != "A_2C_MSS15"
            or not g.has_parent_owned_mss
            or g.c1_at != parent.c1_at
            or g.direction != (1 if parent.side == "LONG" else -1)
            or g.retest_closed_at is None
            or g.retest_high is None
            or g.retest_low is None
            or g.retest_close is None
            or not parent.mss_at < g.retest_closed_at
            or g.retest_closed_at > parent.mss_at + timedelta(hours=4)
            or g.retest_closed_at > g.ratified_at
            or not g.retest_low <= g.retest_close <= g.retest_high
        ):
            raise ValueError("M15 retest not linked to own parent closed M15")
        rec = new(
            Family.M15_RETEST,
            f"{symbol}|{Family.M15_RETEST.value}|"
            f"{parent.identity}|{g.retest_closed_at.isoformat()}",
            direction=g.direction, c1_at=g.c1_at,
            mss_at=parent.mss_at,
            ratified_at=g.ratified_at, available_at=g.ratified_at,
            provenance="LINKED_PARENT_2C_MSS15_CLOSED_M15_RETEST",
            parent_id=parent.identity,
        )
        rec["geometry"] = {
            "c1_high": _price(parent.c1_high),
            "c1_low": _price(parent.c1_low),
            "retest_high": _price(g.retest_high),
            "retest_low": _price(g.retest_low),
            "retest_close": _price(g.retest_close),
            "retest_closed_at": _dt(g.retest_closed_at),
        }
        records.append(rec)

    ids = [r["source_event_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("seven-family structural event identity collision")
    actual = Counter(r["family"] for r in records)
    if {family.value: actual[family.value] for family in Family} != expected:
        raise ValueError("seven-family individual tape/count mismatch")
    records.sort(
        key=lambda r: (
            r["available_at"], r["family"], r["source_event_id"]
        )
    )
    return records


def write_event_tape(
    path: Path, *, engine: CausalCRTM5, provider_cohort: str
) -> dict[str, Any]:
    """Write source individual records and return SHA256 without raw broker OHLC."""
    records = build_event_tape(engine, provider_cohort=provider_cohort)
    path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with path.open("wb") as dest:
        for rec in records:
            row = (
                json.dumps(rec, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode("utf-8")
            h.update(row)
            dest.write(row)
    return {
        "schema": SCHEMA,
        "events_file_sha256": h.hexdigest(),
        "rows": len(records),
        "by_family": {
            family.value: sum(r["family"] == family.value for r in records)
            for family in Family
        },
        "price_backtest_certified": False,
        "broker_orders_executed": 0,
        "status": "STRUCTURAL_EVENT_TAPE_NO_TRADES_NO_PINE_PARITY",
    }
