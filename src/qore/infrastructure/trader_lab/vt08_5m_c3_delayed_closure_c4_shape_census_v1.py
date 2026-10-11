"""Research-only C3 delayed closure -> C4 source geometry, NO TRADES/PNL.

Source: TTrades Dec 2025 Candle 3 Closure; simplified body-bound tests
are explicitly geometric PROXIES, not complete author-adjudicated POI/PS.
C3 only becomes observable at its H4 close; C4 at the next H4 open.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import (
    SOURCE_SHA,
    attest_bias,
)
from qore.infrastructure.trader_lab.vt08_5m_ttrades_c2_c3_source_eq_range_v1 import (
    source_eq_after_closure,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _window_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.trader_lab.vt08_5m_c3_delayed_closure_c4_shape.v1"
SOURCE_FAMILY: Final = "C3_CLOSURE_TO_C4_M15_SOURCE_SHAPE_V1"
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class Closure:
    side: DemoTradingSetupSide
    body_engulfed: bool
    c3_confirmed_at: datetime

    def __post_init__(self) -> None:
        if self.c3_confirmed_at.tzinfo is None:
            raise ValueError("C3 closure needs verified close time")


def c2_reversal_closure(c1: Vt08B01Bar, c2: Vt08B01Bar) -> bool:
    """Existing source reversal definition, distinct from potential C2 entry."""
    high = c2.high > c1.high and c1.low < c2.close < c1.high
    low = c2.low < c1.low and c1.low < c2.close < c1.high
    # Both sides swept needs independent ambiguity adjudication.
    return high != low


def c3_body_closure(c2: Vt08B01Bar, c3: Vt08B01Bar) -> tuple[Closure, ...]:
    """C3 strictly closes outside body C2 WITHOUT sweeping its H/L.

    A completed H4 C3 is mandatory. This is a shape candidate, not a
    full TTrades validated POI/HTF swing or a C4-entry authorization.
    """
    if c3.opened_at.astimezone(UTC) != c2.closed_at.astimezone(UTC):
        raise ValueError("C3 must begin exactly as C2 completes")
    if c3.closed_at.astimezone(UTC) != (
        c3.opened_at.astimezone(UTC) + timedelta(hours=4)
    ):
        raise ValueError("C3 must be complete before evaluating closure")
    if c3.high > c2.high or c3.low < c2.low:
        return ()
    body_hi, body_lo = max(c2.open, c2.close), min(c2.open, c2.close)
    hits: list[Closure] = []
    if c3.close > body_hi:
        hits.append(Closure(
            side=DemoTradingSetupSide.LONG,
            body_engulfed=c3.open < body_lo,
            c3_confirmed_at=c3.closed_at,
        ))
    if c3.close < body_lo:
        hits.append(Closure(
            side=DemoTradingSetupSide.SHORT,
            body_engulfed=c3.open > body_hi,
            c3_confirmed_at=c3.closed_at,
        ))
    return tuple(hits)


def first_c4_eq_observation(
    *,
    c3: Vt08B01Bar,
    c4_first: Vt08B01Bar | None,
    side: DemoTradingSetupSide,
) -> dict[str, object]:
    """ONLY observation after C4 M15 closes; zero orders or hindsight fills."""
    eq_proof = source_eq_after_closure(
        c3,
        candle_label="C3",
        intended_side=side,
        closure_adjudicated=True,
        decision_at=c3.closed_at,
    )
    if eq_proof is None:
        raise ValueError("C3 closed source EQ proof is missing")
    eq = eq_proof.eq
    payload: dict[str, object] = {
        "eq_level": str(eq),
        "eq_basis": "C3_FULL_WICK_TO_WICK_AS_OF_C3_CLOSE",
        "c4_first_15m_closed_at": None,
        "first_15m_eq_half_respected": None,
        "first_15m_wick_reentered_c3_half": None,
    }
    if c4_first is None:
        return payload
    if c4_first.opened_at.astimezone(UTC) != c3.closed_at.astimezone(UTC):
        raise ValueError("C4 must open after completed C3")
    if c4_first.closed_at.astimezone(UTC) != (
        c4_first.opened_at.astimezone(UTC) + timedelta(minutes=15)
    ):
        raise ValueError("C4 first M15 is incomplete")
    bullish = side is DemoTradingSetupSide.LONG
    respected = (
        c4_first.close >= eq if bullish else c4_first.close <= eq
    )
    wick_half = (
        eq <= c4_first.low <= c3.high if bullish
        else c3.low <= c4_first.high <= eq
    )
    payload.update({
        "c4_first_15m_closed_at": c4_first.closed_at.isoformat(),
        "first_15m_eq_half_respected": respected,
        "first_15m_wick_reentered_c3_half": wick_half,
    })
    return payload


def evaluate(path: Path) -> dict[str, object]:
    fp, market, checked, sha, rows = load_market_evidence(path)
    if sha != SOURCE_SHA or market not in EXPANSION_MARKETS:
        raise ValueError("not the admitted consumed 1095D source")
    by_open = {x.opened_at: x for x in rows}
    if len(by_open) != len(rows):
        raise ValueError("duplicate M15 candle open")
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    shapes: list[dict[str, object]] = []

    def stage(name: str, year: str) -> None:
        counts[name] += 1
        by_year[year][name] += 1

    for anchor in rows:
        local = anchor.opened_at.astimezone(_NY)
        if local.minute != 0 or local.second != 0 or local.hour not in ANCHORS_NY:
            continue
        year = str(local.year)
        stage("OWNER_C3_START_H4", year)
        c1 = source_h4_from_m15(
            by_open, opened_at_local=local - timedelta(hours=8)
        )
        c2 = source_h4_from_m15(
            by_open, opened_at_local=local - timedelta(hours=4)
        )
        c3 = source_h4_from_m15(by_open, opened_at_local=local)
        if c1 is None or c2 is None or c3 is None:
            reasons["INCOMPLETE_C1_C2_OR_C3"] += 1
            continue
        if c1.closed_at != c2.opened_at or c2.closed_at != c3.opened_at:
            reasons["H4_SEQUENCE_NOT_CONTIGUOUS"] += 1
            continue
        stage("C1_C2_C3_COMPLETE", year)
        if c2_reversal_closure(c1, c2):
            reasons["C2_ALREADY_COMPLETED_REVERSAL_CLOSURE"] += 1
            continue
        stage("C2_FAILED_REVERSAL_CLOSURE", year)
        c2_sweep_any = c2.high > c1.high or c2.low < c1.low
        if c2_sweep_any:
            stage("C2_SWEPT_BUT_FAILED_REVERSAL", year)
        else:
            stage("C2_NO_C1_SWEEP", year)
        raw = c3_body_closure(c2, c3)
        if not raw:
            reasons["NO_STRICT_C3_BODY_CLOSE_INSIDE_C2_HL"] += 1
            continue
        stage("C3_STRICT_BODY_CLOSE_NO_C2_SWEEP_SHAPE", year)
        att = attest_bias(by_open, decision_at=c3.closed_at)
        ny_c4 = c3.closed_at.astimezone(_NY)
        within_owner = (
            ny_c4.hour in ANCHORS_NY
            and ny_c4.minute == 0
            and ny_c4.second == 0
        )
        for item in raw:
            if item.c3_confirmed_at != c3.closed_at:
                raise AssertionError("C3 source close leakage")
            if item.body_engulfed:
                stage("C3_BODY_ENGULF_STRONG_PROXY", year)
            if att is not None and att.bias is item.side:
                stage("C3_ALIGNED_WITH_OLD_DAILY_BIAS", year)
            if within_owner:
                stage("C4_H4_OPEN_OWNER_ELIGIBLE", year)
            else:
                stage("C4_H4_OPEN_OUTSIDE_OWNER", year)
            m15_c3 = _window_bars(
                by_open,
                opened_at=c3.opened_at,
                closed_at=c3.closed_at,
            )
            if m15_c3 is None:
                raise AssertionError("completed C3 must have M15 constituents")
            # An internal-LTF PS is a *proxy* using C3's first M15 high/low;
            # the source POI and swing point have NOT been identified.
            proxy_level = (
                m15_c3[0].low
                if item.side is DemoTradingSetupSide.LONG
                else m15_c3[0].high
            )
            ps = protected_swings_in_candle2(
                m15_c3, side=item.side, important_level=proxy_level,
            )
            if ps:
                stage("C3_INTERNAL_M15_CISD_PS_PROXY", year)
            c4_first = by_open.get(c3.closed_at.astimezone(UTC))
            c4_eq = first_c4_eq_observation(
                c3=c3,
                c4_first=c4_first,
                side=item.side,
            )
            if c4_eq["first_15m_eq_half_respected"] is True:
                stage("C4_FIRST_M15_CLOSE_RESPECTS_C3_EQ", year)
            if c4_eq["first_15m_wick_reentered_c3_half"] is True:
                stage("C4_FIRST_M15_WICKS_IN_RESPECTED_HALF", year)
            if within_owner and ps and att is not None and att.bias is item.side:
                stage("SHAPE_WITH_OWNER_OLD_BIAS_INTERNAL_PS", year)
            case_sha = hashlib.sha256(
                f"{SCHEMA}|{market}|{c3.opened_at.isoformat()}|{item.side.value}".encode()
            ).hexdigest()
            shapes.append({
                "shape_id": f"vt08-c3closure:{case_sha}",
                "market": market,
                "source_family": SOURCE_FAMILY,
                "c3_at": c3.opened_at.isoformat(),
                "c3_closed_at": c3.closed_at.isoformat(),
                "c4_h4_open_at": c3.closed_at.isoformat(),
                "c4_owner_permitted": within_owner,
                "c3_close_side": item.side.value,
                "strong_full_body_engulf_proxy": item.body_engulfed,
                "c2_swept_c1": c2_sweep_any,
                "old_bias_asof_c3_close": (
                    att.bias.value if att is not None and att.bias else "UNRESOLVED"
                ),
                "old_bias_cutoff": (
                    att.current_day.day.closed_at.isoformat() if att else None
                ),
                "c3_ps_internal_proxy_count": len(ps),
                "c3_full_high": str(c3.high),
                "c3_full_low": str(c3.low),
                "c3_full_close": str(c3.close),
                **c4_eq,
                "poi_source_confirmed": False,
                "methodology_status": "SHAPE_ONLY_NOT_SOURCE_COMPLETE",
                "trades_executed": 0,
            })
    if counts["OWNER_C3_START_H4"] != (
        sum(reasons.values()) + counts["C3_STRICT_BODY_CLOSE_NO_C2_SWEEP_SHAPE"]
    ):
        raise AssertionError("C3 closure first failure attribution mismatch")
    if len(shapes) != counts["C3_STRICT_BODY_CLOSE_NO_C2_SWEEP_SHAPE"]:
        raise AssertionError("C3 closure shape cardinality mismatch")
    return {
        "schema": SCHEMA,
        "market": market,
        "source_sha": sha,
        "evidence_checked_at": checked.isoformat(),
        "evidence_fingerprint": fp,
        "stage_counts": dict(sorted(counts.items())),
        "failure_counts": dict(sorted(reasons.items())),
        "by_year_stage_counts": {
            x: dict(sorted(c.items())) for x, c in sorted(by_year.items())
        },
        "shapes": shapes,
        "source_poi_confirmed": False,
        "c4_orders_authorized": False,
        "cognitive_feature_provenance_complete": False,
        "trades_executed": 0,
        "pnl_evaluated": False,
        "seven_year_sealed_accessed": False,
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
