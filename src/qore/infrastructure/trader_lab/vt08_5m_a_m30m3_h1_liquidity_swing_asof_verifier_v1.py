"""Auditable pre-C2 external liquidity pivots + H1 FVG, NOT valid EQ swing.

TTrades 2026-08-22 defines three-candle external pivot high/low.  The
right candle must be CLOSED before the proposed C2 decision. This is
NOT sufficient to prove a valid TTrades EQ swing or a source POI/trade.
Existing M30→M3 research SHAPES are externally reverified on native
source bars, with new upstream H1 liquidity geometry recorded separately.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    SCHEMA as ORIGINAL_M30_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    aggregate,
    closed_source_window,
    same_ohlc,
    source_m30_reversal,
)
from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    evaluate as audit_existing_m30_m3,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    _load_m3,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
)

SCHEMA = "qore.vt08.5m.m30m3.h1_pivot_liquidity_asof.research.v1"
NY = ZoneInfo("America/New_York")
PIVOT_SOURCE = "https://ttrades.com/internal-external-liquidity-using-the-ttrades-fractal-model/"
CISD_SOURCE = "https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/"


class ExternalPivotKind(StrEnum):
    HIGH = "EXTERNAL_SWING_HIGH_GEOMETRY"
    LOW = "EXTERNAL_SWING_LOW_GEOMETRY"


@dataclass(frozen=True, slots=True)
class ClosedExternalPivot:
    kind: ExternalPivotKind
    extreme: Decimal
    pivot_candle_opened_at: datetime
    confirmed_at: datetime
    definition_source: str = PIVOT_SOURCE

    def payload(self) -> dict[str, str]:
        return {
            "kind": self.kind.value,
            "level": str(self.extreme),
            "pivot_candle_opened_at": self.pivot_candle_opened_at.astimezone(UTC).isoformat(),
            "pivot_confirmed_at": self.confirmed_at.astimezone(UTC).isoformat(),
            "written_definition_source": self.definition_source,
            "eq_regime_authorized": "false",
        }


def closed_external_pivots(
    three: tuple[Vt08B01Bar, ...],
    *,
    as_of: datetime,
    constituent_minutes: int = 60,
) -> tuple[ClosedExternalPivot, ...]:
    """Strict three-candle pivot, never backdate to central candle."""
    if as_of.utcoffset() is None:
        raise ValueError("decision time must be timezone aware")
    if len(three) != 3:
        raise ValueError("three completed candles are required")
    t = three[0].opened_at.astimezone(UTC)
    for candle in three:
        if candle.opened_at.astimezone(UTC) != t:
            raise ValueError("pivot candles are not continuous")
        if candle.closed_at.astimezone(UTC) != t + timedelta(
            minutes=constituent_minutes
        ):
            raise ValueError("pivot source timeframe duration invalid")
        if candle.closed_at.astimezone(UTC) > as_of.astimezone(UTC):
            raise ValueError("pivot right candle cannot be future")
        t = candle.closed_at.astimezone(UTC)
    left, middle, right = three
    out: list[ClosedExternalPivot] = []
    if middle.high > left.high and middle.high > right.high:
        out.append(ClosedExternalPivot(
            ExternalPivotKind.HIGH, middle.high, middle.opened_at, right.closed_at,
        ))
    if middle.low < left.low and middle.low < right.low:
        out.append(ClosedExternalPivot(
            ExternalPivotKind.LOW, middle.low, middle.opened_at, right.closed_at,
        ))
    return tuple(out)


def prior_h1_liquidity_context(
    m15_index: dict[datetime, Vt08B01Bar],
    *,
    before_c2_open: datetime,
) -> dict[str, object]:
    """EXACTLY preceding three fully closed H1 bars from independent M15."""
    if before_c2_open.utcoffset() is None:
        raise ValueError("C2 open must have timezone")
    cutoff = before_c2_open.astimezone(UTC)
    latest_h1_end = cutoff.replace(minute=0, second=0, microsecond=0)
    oldest = latest_h1_end - timedelta(hours=3)
    candles = closed_source_window(
        m15_index, begin=oldest, count=12, minutes=15,
    )
    if candles is None:
        return {"status": "H1_PRE_C2_SOURCE_INCOMPLETE"}
    h1 = tuple(
        aggregate(candles[i:i + 4], period_minutes=60, member_minutes=15)
        for i in (0, 4, 8)
    )
    if h1[-1].closed_at.astimezone(UTC) > cutoff:
        raise AssertionError("H1 source uses C2 future")
    pivots = closed_external_pivots(h1, as_of=cutoff)
    fvg_bull = h1[0].high < h1[2].low
    fvg_bear = h1[2].high < h1[0].low
    fvg = (
        ("BULL", h1[0].high, h1[2].low)
        if fvg_bull
        else ("BEAR", h1[2].high, h1[0].low) if fvg_bear else None
    )
    pre = {
        "h1_last_closed_at": h1[-1].closed_at.astimezone(UTC).isoformat(),
        "h1_triplet_first_open": h1[0].opened_at.astimezone(UTC).isoformat(),
        "h1_triplet_source_count": 12,
        "h1_external_pivots": [p.payload() for p in pivots],
        "h1_closed_fvg": {
            "direction": fvg[0], "lower": str(fvg[1]), "upper": str(fvg[2]),
            "formed_at": h1[-1].closed_at.astimezone(UTC).isoformat(),
            "poi_author_validated": False,
        } if fvg else None,
    }
    return {
        "status": "H1_PRE_C2_GEOMETRY_ONLY",
        **pre,
        "evidence_fingerprint": hashlib.sha256(
            json.dumps(pre, sort_keys=True).encode()
        ).hexdigest(),
        "source_POI_significance_confirmed": False,
        "valid_C2_EQ_swing_confirmed": False,
    }


def verify_record(
    record: dict[str, object],
    *,
    m15_index: dict[datetime, Vt08B01Bar],
    m3_index: dict[datetime, Vt08B01Bar],
) -> dict[str, object]:
    """Independent pre-C2 source/PS verification; no declared bool trusted."""
    c3_at = datetime.fromisoformat(str(record["entry_positional_proposed_at"]))
    if c3_at.utcoffset() is None:
        raise ValueError("source event clock has no UTC offset")
    c2_open = c3_at - timedelta(minutes=30)
    c1_open = c2_open - timedelta(minutes=30)
    b1 = closed_source_window(m3_index, begin=c1_open, count=10, minutes=3)
    b2 = closed_source_window(m3_index, begin=c2_open, count=10, minutes=3)
    h1 = closed_source_window(m15_index, begin=c1_open, count=2, minutes=15)
    h2 = closed_source_window(m15_index, begin=c2_open, count=2, minutes=15)
    if b1 is None or b2 is None or h1 is None or h2 is None:
        raise ValueError("original source record has missing M30 constituents")
    c1 = aggregate(b1, period_minutes=30, member_minutes=3)
    c2 = aggregate(b2, period_minutes=30, member_minutes=3)
    if not (
        same_ohlc(c1, aggregate(h1, period_minutes=30, member_minutes=15))
        and same_ohlc(c2, aggregate(h2, period_minutes=30, member_minutes=15))
    ):
        raise ValueError("original M30 source failed M3 vs M15 independent replay")
    side = source_m30_reversal(c1, c2)
    if side is None or side.value != record["side"]:
        raise ValueError("historical C2 reversal direction unsupported")
    if c2.low < c1.low and c2.high > c1.high:
        raise ValueError("C2 dual sweep cannot pass verifier")
    important = c1.low if side is DemoTradingSetupSide.LONG else c1.high
    swings = protected_swings_in_candle2(b2, side=side, important_level=important)
    if len(swings) != 1:
        raise ValueError("historical PS not unique source M3")
    ps = swings[0]
    if (
        ps.price != Decimal(str(record["c2_m3_ps_price"]))
        or ps.cisd_level != Decimal(str(record["c2_m3_cisd_retest_level"]))
        or ps.confirmed_at.astimezone(UTC) != datetime.fromisoformat(
            str(record["c2_m3_cisd_confirmed_at"])
        ).astimezone(UTC)
        or ps.confirmed_at.astimezone(UTC) > c2.closed_at.astimezone(UTC)
        or ps.opposing_series_opened_at.astimezone(UTC) < c2.opened_at.astimezone(UTC)
    ):
        raise ValueError("CISD/PS historical provenance mismatch")
    if (
        record.get("c1_closed_at") != c1.closed_at.isoformat()
        or record.get("c2_closed_at") != c2.closed_at.isoformat()
        or record.get("c2_m3_opposing_series_start") != ps.opposing_series_opened_at.isoformat()
    ):
        raise ValueError("C1/C2/CISD opposing series source lineage mismatch")
    original_market = record.get("market")
    if not isinstance(original_market, str):
        raise ValueError("record missing mother market")
    expected_id = "vt08-m30m3:" + hashlib.sha256(
        (
            f"{ORIGINAL_M30_SCHEMA}|{original_market}|{c2.opened_at.isoformat()}|"
            f"{side.value}|{ps.confirmed_at.isoformat()}"
        ).encode()
    ).hexdigest()
    if record.get("origin_id") != expected_id:
        raise ValueError("mother structural ID mismatch")
    evidence = prior_h1_liquidity_context(
        m15_index, before_c2_open=c2.opened_at,
    )
    if evidence["status"] != "H1_PRE_C2_GEOMETRY_ONLY":
        return {"status": "H1_SOURCE_UNAVAILABLE", "c2_closed_at": c2.closed_at.isoformat()}
    pivot_records = evidence["h1_external_pivots"]
    assert isinstance(pivot_records, list)
    relevant_kind = (
        ExternalPivotKind.LOW.value
        if side is DemoTradingSetupSide.LONG else ExternalPivotKind.HIGH.value
    )
    relevant_pivot = next(
        (p for p in pivot_records if p["kind"] == relevant_kind), None
    )
    fvg = evidence["h1_closed_fvg"]
    geometry_fvg_touch = (
        isinstance(fvg, dict)
        and c2.low <= Decimal(str(fvg["upper"]))
        and c2.high >= Decimal(str(fvg["lower"]))
    )
    pivot_swept = (
        relevant_pivot is not None
        and (
            c2.low < Decimal(relevant_pivot["level"])
            if side is DemoTradingSetupSide.LONG
            else c2.high > Decimal(relevant_pivot["level"])
        )
    )
    c2_body_with_side = (
        c2.close > c2.open if side is DemoTradingSetupSide.LONG
        else c2.close < c2.open
    )
    return {
        "status": "INDEPENDENT_M3_CISD_VERIFIED_HTF_POI_STILL_D",
        "origin_id": record["origin_id"],
        "c2_opened_at": c2.opened_at.astimezone(UTC).isoformat(),
        "c2_closed_at": c2.closed_at.astimezone(UTC).isoformat(),
        "side": side.value,
        "c2_directional_close_with_reversal": c2_body_with_side,
        "cisd_confirmed_at": ps.confirmed_at.astimezone(UTC).isoformat(),
        "protected_swing_price": str(ps.price),
        "poi_before_c2": evidence,
        "prior_h1_fvg_touched_by_c2": geometry_fvg_touch,
        "prior_h1_external_pivot_relevant_found": relevant_pivot is not None,
        "prior_h1_relevant_pivot_swept_c2": pivot_swept,
        "eq_C2_close_to_wick_regime_authorized": False,
        "h1_context_poi_source_complete": False,
        "cognitive_ready": False,
        "orders_authorized": False,
        "physical_fills": 0,
    }


def evaluate(base_path: Path, m3_path: Path) -> dict[str, object]:
    prior = audit_existing_m30_m3(base_path, m3_path)
    _, symbol, _, _, m15 = load_market_evidence(base_path)
    native_m3 = _load_m3(m3_path, expected_symbol=symbol)
    a15 = {x.opened_at: x for x in m15}
    a3 = {x.opened_at: x for x in native_m3}
    if len(a15) != len(m15) or len(a3) != len(native_m3):
        raise ValueError("duplicate source timestamps")
    observations: list[dict[str, object]] = []
    stages: Counter[str] = Counter()
    years: dict[str, Counter[str]] = defaultdict(Counter)
    for row in prior["research_observations"]:
        assert isinstance(row, dict)
        verified = verify_record(row, m15_index=a15, m3_index=a3)
        stages[verified["status"]] += 1
        c2_year = str(row["market_ny_date"])[:4]
        years[c2_year][verified["status"]] += 1
        if verified["status"] == "INDEPENDENT_M3_CISD_VERIFIED_HTF_POI_STILL_D":
            for label, exists in (
                ("H1_PRE_C2_FVG_TOUCHED_C2", verified["prior_h1_fvg_touched_by_c2"]),
                (
                    "H1_PRE_C2_RELEVANT_PIVOT_EXISTS",
                    verified["prior_h1_external_pivot_relevant_found"],
                ),
                (
                    "H1_PRE_C2_RELEVANT_PIVOT_SWEPT_C2",
                    verified["prior_h1_relevant_pivot_swept_c2"],
                ),
                (
                    "C2_BODY_CLOSED_WITH_SIDE",
                    verified["c2_directional_close_with_reversal"],
                ),
            ):
                if exists:
                    stages[label] += 1
                    years[c2_year][label] += 1
        observations.append(verified)
    if len(observations) != prior["counts"]["M30_M3_SOURCE_GEOMETRY_ONLY"]:
        raise AssertionError("independent verifier didn't cover all M30 M3 records")
    return {
        "schema": SCHEMA,
        "market": symbol,
        "prior_geometry_count": len(observations),
        "counts": dict(sorted(stages.items())),
        "per_year": {y: dict(sorted(c.items())) for y, c in sorted(years.items())},
        "source_receipts": observations,
        "source_authors": [PIVOT_SOURCE, CISD_SOURCE],
        "source_external_pivot_geometry_pre_c2_tested": True,
        "valid_EQ_C2_swing_definition_fully_adjudicated": False,
        "HTF_POI_significance_verified": False,
        "source_complete_signals": 0,
        "approved_cognitive_events": 0,
        "orders": 0,
        "fills": 0,
        "pnl_evaluated": False,
        "sealed_7y_accessed": False,
    }
