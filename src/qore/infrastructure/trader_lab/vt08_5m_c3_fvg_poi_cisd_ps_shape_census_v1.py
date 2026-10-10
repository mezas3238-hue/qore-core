"""No-PnL causal C3 research geometry census: POI FVG -> CISD -> PS.

A Candle-3 continuation needs source-verified wick-depth classification and
POI priority before any of this can become an executable CandidateEvent.
All outcomes and prices after proposed entry are deliberately absent.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import (
    SOURCE_SHA,
    attest_bias,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _candle2_reversal_side,
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

SCHEMA: Final = "qore.trader_lab.vt08_5m_c3_fvg_poi_cisd_ps.shape.v1"
BUNDLE: Final = "C3_FVG_RETEST_M15_SHAPE_V1"
_NY = ZoneInfo("America/New_York")


def _active_c2_fvgs(
    bars: tuple[Vt08B01Bar, ...],
    *,
    side: DemoTradingSetupSide,
) -> tuple[tuple[Decimal, Decimal], ...]:
    """Three-candle C2 FVGs known at C3 open, with no old invalidation."""
    levels: list[tuple[Decimal, Decimal]] = []
    for index in range(2, len(bars)):
        left, right = bars[index - 2], bars[index]
        if side is DemoTradingSetupSide.LONG:
            lower, upper = left.high, right.low
        else:
            lower, upper = right.high, left.low
        if lower >= upper:
            continue
        invalidated = any(
            later.low < lower
            if side is DemoTradingSetupSide.LONG
            else later.high > upper
            for later in bars[index + 1 :]
        )
        if not invalidated:
            levels.append((lower, upper))
    return tuple(dict.fromkeys(levels))


def _contiguous_prefix(
    bars_by_open: dict,
    *,
    opened_at,
    closed_at,
) -> tuple[Vt08B01Bar, ...]:
    result: list[Vt08B01Bar] = []
    t = opened_at.astimezone(UTC)
    end = closed_at.astimezone(UTC)
    while t < end:
        bar = bars_by_open.get(t)
        if bar is None or bar.closed_at != t + timedelta(minutes=15):
            break
        result.append(bar)
        t += timedelta(minutes=15)
    return tuple(result)


def _first_c3_shape(
    c3: tuple[Vt08B01Bar, ...],
    *,
    levels: tuple[tuple[Decimal, Decimal], ...],
    side: DemoTradingSetupSide,
) -> dict[str, object] | None:
    """POI touch must occur before a independently closing CISD/PS."""
    candidates: list[tuple[object, ...]] = []
    by_open = {bar.opened_at: bar for bar in c3}
    for lower, upper in levels:
        touches = tuple(
            bar for bar in c3
            if bar.low <= upper and bar.high >= lower
        )
        if not touches:
            continue
        first_touch = touches[0]
        important = upper if side is DemoTradingSetupSide.LONG else lower
        swings = protected_swings_in_candle2(
            c3, side=side, important_level=important,
        )
        for swing in swings:
            if swing.confirmed_at <= first_touch.closed_at:
                continue
            next_bar = by_open.get(swing.confirmed_at)
            next_open_valid = bool(
                next_bar is not None
                and next_bar.opened_at == swing.confirmed_at
                and next_bar.closed_at == swing.confirmed_at + timedelta(minutes=15)
            )
            # Only observable next-bar OPEN, never next-bar high/low/close.
            oriented_risk = (
                (
                    next_bar.open > swing.price
                    if side is DemoTradingSetupSide.LONG
                    else next_bar.open < swing.price
                )
                if next_open_valid and next_bar is not None
                else False
            )
            row: dict[str, object] = {
                "poi_lower": str(lower),
                "poi_upper": str(upper),
                "poi_first_touched_bar_closed_at": first_touch.closed_at.isoformat(),
                "ps_opposing_series_opened_at": swing.opposing_series_opened_at.isoformat(),
                "ps_cisd_confirmed_at": swing.confirmed_at.isoformat(),
                "ps_protected_price": str(swing.price),
                "ps_cisd_level": str(swing.cisd_level),
                "hypothetical_next_m15_open_at": (
                    next_bar.opened_at.isoformat() if next_open_valid and next_bar else None
                ),
                "hypothetical_next_m15_open": (
                    str(next_bar.open) if next_open_valid and next_bar else None
                ),
                "causal_stop_oriented_geometry": oriented_risk,
                "methodology_status": "SHAPE_ONLY_NOT_SOURCE_COMPLETE",
                "wick_depth_classification": "NOT_SOURCE_CALIBRATED",
                "trades_executed": 0,
            }
            candidates.append((
                swing.confirmed_at,
                swing.opposing_series_opened_at,
                lower,
                upper,
                row,
            ))
    if not candidates:
        return None
    # Earliest causal confirmation, NO selection by next-open risk or future PnL.
    return sorted(candidates, key=lambda x: x[:4])[0][4]  # type: ignore[return-value]


def evaluate(path: Path) -> dict[str, object]:
    fp, market, checked, sha, m15 = load_market_evidence(path)
    if market not in EXPANSION_MARKETS or sha != SOURCE_SHA:
        raise ValueError("C3 scope requires original consumed M15 1095D")
    index = {bar.opened_at: bar for bar in m15}
    counts: Counter[str] = Counter()
    years: dict[str, Counter[str]] = defaultdict(Counter)
    source_events: list[dict[str, object]] = []
    failures: Counter[str] = Counter()

    def stage(name: str, year: str) -> None:
        counts[name] += 1
        years[year][name] += 1

    for anchor in m15:
        local = anchor.opened_at.astimezone(_NY)
        if local.minute != 0 or local.second != 0 or local.hour not in ANCHORS_NY:
            continue
        year = str(local.year)
        stage("OBSERVED_OWNER_ANCHOR", year)
        c1 = source_h4_from_m15(
            index, opened_at_local=local - timedelta(hours=8)
        )
        c2 = source_h4_from_m15(
            index, opened_at_local=local - timedelta(hours=4)
        )
        if c1 is None or c2 is None or c2.closed_at != anchor.opened_at:
            failures["REFERENCE_OR_C2_H4_MISSING"] += 1
            continue
        stage("C1_AND_C2_COMPLETE", year)
        att = attest_bias(index, decision_at=anchor.opened_at)
        if att is None:
            failures["SOURCE_BIAS_NOT_ATTESTED"] += 1
            continue
        if att.bias is None:
            failures["SOURCE_BIAS_UNRESOLVED"] += 1
            continue
        stage("BIAS_ASOF_ATTESTED", year)
        c2_side = _candle2_reversal_side(c1, c2)
        if c2_side is not att.bias:
            failures["C2_NOT_SINGLE_REVERSAL_IN_BIAS"] += 1
            continue
        stage("C2_CLOSED_REVERSAL_ALIGNED", year)
        old_c2_m15 = _window_bars(
            index, opened_at=c2.opened_at, closed_at=c2.closed_at
        )
        if old_c2_m15 is None:
            failures["C2_M15_MISSING"] += 1
            continue
        important = (
            c1.low if att.bias is DemoTradingSetupSide.LONG else c1.high
        )
        prior_ps = protected_swings_in_candle2(
            old_c2_m15, side=att.bias, important_level=important
        )
        if prior_ps:
            stage("C2_WITH_PROTECTED_SWING", year)
        levels = _active_c2_fvgs(old_c2_m15, side=att.bias)
        if not levels:
            failures["C2_HAS_NO_ACTIVE_SIDED_FVG"] += 1
            continue
        stage("C2_HAS_ACTIVE_SIDED_FVG", year)
        c3 = _contiguous_prefix(
            index,
            opened_at=anchor.opened_at,
            closed_at=anchor.opened_at + timedelta(hours=4),
        )
        if len(c3) < 2:
            failures["C3_M15_PREFIX_MISSING"] += 1
            continue
        touched = any(
            bar.low <= upper and bar.high >= lower
            for lower, upper in levels
            for bar in c3
        )
        if not touched:
            failures["NO_C3_POI_TOUCH"] += 1
            continue
        stage("C3_TOUCHES_PREEXISTING_C2_FVG", year)
        shape = _first_c3_shape(c3, levels=levels, side=att.bias)
        if shape is None:
            failures["NO_CAUSAL_C3_PS_AFTER_POI"] += 1
            continue
        stage("C3_POI_CISD_PS_SHAPE_ONLY", year)
        if shape["causal_stop_oriented_geometry"] is True:
            stage("C3_SHAPE_WITH_NEXT_OPEN_AND_ORIENTED_RISK", year)
        anchor_id = hashlib.sha256(
            f"{SCHEMA}|{market}|{anchor.opened_at.isoformat()}".encode()
        ).hexdigest()
        source_events.append({
            "anchor_shape_id": f"vt08-c3-shape:{anchor_id}",
            "market": market,
            "anchor_at": anchor.opened_at.isoformat(),
            "ny_date": local.date().isoformat(),
            "anchor_hour_ny": local.hour,
            "side": att.bias.value,
            "bias_feature_cutoff": att.current_day.day.closed_at.isoformat(),
            "source_day_m15_sha256": att.current_day.m15_sha256,
            "c1_closed_at": c1.closed_at.isoformat(),
            "c2_closed_at": c2.closed_at.isoformat(),
            "c2_ps_count": len(prior_ps),
            "c2_active_sided_fvg_count": len(levels),
            "c2_opposing_wick_length": str(
                c2.open - c2.low
                if att.bias is DemoTradingSetupSide.LONG
                else c2.high - c2.open
            ),
            "c2_full_range": str(c2.high - c2.low),
            **shape,
        })
    if counts["OBSERVED_OWNER_ANCHOR"] != (
        sum(failures.values()) + counts["C3_POI_CISD_PS_SHAPE_ONLY"]
    ):
        raise AssertionError("C3 shape/source failure attribution drift")
    if len(source_events) != counts["C3_POI_CISD_PS_SHAPE_ONLY"]:
        raise AssertionError("C3 event count mismatch")
    return {
        "schema": SCHEMA,
        "bundle": BUNDLE,
        "market": market,
        "source_sha": sha,
        "evidence_fingerprint": fp,
        "evidence_checked_at": checked.isoformat(),
        "stage_counts": dict(sorted(counts.items())),
        "first_failure_counts": dict(sorted(failures.items())),
        "by_year_stage_counts": {
            year: dict(sorted(c.items())) for year, c in sorted(years.items())
        },
        "shapes": source_events,
        "all_shapes_source_complete": False,
        "c3_wick_depth_numeric_source_rule_found": False,
        "entry_sl_target_lifecycle_source_complete": False,
        "candidate_event_export_authorized": False,
        "trades_executed": 0,
        "pnl_evaluated": False,
        "sealed_7y_read": False,
    }


def to_json(path: Path) -> str:
    return json.dumps(evaluate(path), sort_keys=True, separators=(",", ":"))
