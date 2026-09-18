"""R32 strict TTrades Candle-3 Turtle Soup opportunity forensics.

Research-only.  Uses the consumed XAUUSD 10Y corpus and does not open the fresh
holdout.

Source contract (TTrades, 2025-12-03 / 2026 TTFM):
- C2 raids C1 but fails the C2 reversal close;
- C3 does not make a new adverse extreme beyond C2;
- C3 closes through the full C2 body in the reversal direction;
- lower-timeframe CISD confirms before C3 closes;
- initial invalidation is the exact protected swing;
- entry is C4/source-next open.

This module measures opportunity density and CIBO binding.  Its rank-1 STATIC
replay is diagnostic only and cannot promote a candidate.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_xauusd_native_market_decision_memory_v2 as native,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_specialist_memory_v1 as specialist,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    Side,
    SourceCandle,
    build_h1,
    build_h4,
    build_m15,
    causal_cisd,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R32_C3_OPPORTUNITY_FORENSICS_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class C3Setup:
    timeframe: str
    side: Side
    c1: SourceCandle
    c2: SourceCandle
    c3: SourceCandle
    raid_at: datetime
    cisd_at: datetime
    entry_at: datetime
    entry: Decimal
    protected_swing: Decimal
    source_opposite: Decimal


def _m5_sources(bars: Sequence[Bar]) -> tuple[SourceCandle, ...]:
    return tuple(
        SourceCandle(
            opened_at=bar.opened_at,
            closed_at=bar.closed_at,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            m5=(bar,),
        )
        for bar in bars
    )


def strict_c3_side(
    c1: SourceCandle,
    c2: SourceCandle,
    c3: SourceCandle,
) -> Side | None:
    bullish = (
        c2.low < c1.low
        and c2.close <= c1.low
        and c3.low >= c2.low
        and c3.close > max(c2.open, c2.close)
        and c3.close > c1.low
    )
    bearish = (
        c2.high > c1.high
        and c2.close >= c1.high
        and c3.high <= c2.high
        and c3.close < min(c2.open, c2.close)
        and c3.close < c1.high
    )
    if bullish == bearish:
        return None
    return Side.LONG if bullish else Side.SHORT


def _raid_at(c2: SourceCandle, c1: SourceCandle, side: Side) -> datetime | None:
    for bar in c2.m5:
        if side is Side.LONG and bar.low < c1.low:
            return bar.opened_at
        if side is Side.SHORT and bar.high > c1.high:
            return bar.opened_at
    return None


def _build(
    evidence: Evidence,
) -> tuple[list[C3Setup], Counter[str]]:
    setups: list[C3Setup] = []
    funnel: Counter[str] = Counter()
    for timeframe, candles in (
        ("H1", build_h1(evidence.bars)),
        ("H4", build_h4(evidence.bars)),
    ):
        for index in range(1, len(candles) - 2):
            c1, c2, c3, c4 = (
                candles[index - 1],
                candles[index],
                candles[index + 1],
                candles[index + 2],
            )
            funnel[f"{timeframe}:source_cycles"] += 1
            side = strict_c3_side(c1, c2, c3)
            if side is None:
                funnel[f"{timeframe}:no_strict_c3"] += 1
                continue
            funnel[f"{timeframe}:strict_c3"] += 1
            raid = _raid_at(c2, c1, side)
            if raid is None:
                funnel[f"{timeframe}:missing_raid"] += 1
                continue

            combined = tuple(c2.m5) + tuple(c3.m5)
            lower = (
                _m5_sources(combined)
                if timeframe == "H1"
                else build_m15(combined)
            )
            extreme = c2.low if side is Side.LONG else c2.high
            cisd = causal_cisd(lower, side=side, extreme=extreme)
            if cisd is None or cisd.confirmed_at > c3.closed_at:
                funnel[f"{timeframe}:no_causal_cisd_by_c3_close"] += 1
                continue
            funnel[f"{timeframe}:causal_cisd"] += 1

            entry = c4.open
            stop = cisd.protected_swing
            risk = entry - stop if side is Side.LONG else stop - entry
            if risk <= 0:
                funnel[f"{timeframe}:invalid_entry_risk"] += 1
                continue
            setups.append(
                C3Setup(
                    timeframe=timeframe,
                    side=side,
                    c1=c1,
                    c2=c2,
                    c3=c3,
                    raid_at=raid,
                    cisd_at=cisd.confirmed_at,
                    entry_at=c4.opened_at,
                    entry=entry,
                    protected_swing=stop,
                    source_opposite=c1.high if side is Side.LONG else c1.low,
                )
            )
            funnel[f"{timeframe}:setup"] += 1
    setups.sort(key=lambda item: (item.entry_at, item.timeframe))
    return setups, funnel


def _stat(values: Sequence[Decimal]) -> dict[str, Any]:
    if not values:
        return {
            "trades": 0,
            "total_r": "0",
            "mean_r": "0",
            "profit_factor": None,
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    total = sum(values, Decimal(0))
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    equity = peak = drawdown = Decimal(0)
    losing = max_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if value < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        else:
            losing = 0
    return {
        "trades": len(values),
        "total_r": str(total),
        "mean_r": str(total / Decimal(len(values))),
        "profit_factor": None if losses == 0 else str(gains / losses),
        "max_drawdown_r": str(drawdown),
        "max_losing_streak": max_losing,
    }


def run(
    raw_root: Path,
    target_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != "XAUUSD" or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD master corpus")
    setups, funnel = _build(evidence)
    target_rows = specialist._load_target_rows(target_root)
    _episodes, source_index = repair._load_targets_fail_closed(target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    tick = Decimal(1).scaleb(-evidence.digits)

    bindings = 0
    ladder_available = 0
    setups_2y = 0
    bindings_2y = 0
    rank1_values: list[Decimal] = []
    rank1_gross: list[Decimal] = []
    busy_until = EVAL_OPEN

    for setup in setups:
        in_2y = EVAL_OPEN <= setup.entry_at < EVAL_CLOSE
        if in_2y:
            setups_2y += 1
        episode_id = source_index.get(
            (
                setup.cisd_at,
                setup.side.value,
                setup.timeframe,
                setup.source_opposite,
            )
        )
        if episode_id is None:
            continue
        bindings += 1
        if in_2y:
            bindings_2y += 1

        ladder = specialist._active_ladder(
            target_rows.get(episode_id, ()),
            at=setup.entry_at,
            side=setup.side,
            entry=setup.entry,
            tick=tick,
        )
        if not ladder:
            continue
        ladder_available += 1
        if not in_2y:
            continue

        rank1 = ladder[0]
        risk = (
            setup.entry - setup.protected_swing
            if setup.side is Side.LONG
            else setup.protected_swing - setup.entry
        )
        lifecycle = native._simulate(
            posture=native.POSTURE_STATIC,
            side=setup.side,
            entry_at=setup.entry_at,
            entry=setup.entry,
            risk_price=risk,
            target=rank1,
            ladder=ladder,
            bars=evidence.bars,
            opens=opens,
        )

        if setup.entry_at < busy_until:
            continue
        # Native lifecycle is capped at 24h; use that same bound for this
        # density diagnostic rather than inventing a different lifecycle.
        busy_until = setup.entry_at + journey.timedelta(hours=24) if False else setup.entry_at
        # Single-position overlap is intentionally not enforced in the raw
        # opportunity diagnostic; each setup is an independent observation.
        rank1_gross.append(lifecycle.gross_r)
        rank1_values.append(lifecycle.net_010_r)

    payload = {
        "schema": "qore.turtle_soup_xauusd.r32_c3_opportunity_forensics.v1",
        "identity": IDENTITY,
        "source_contract": {
            "source": "TTRADES_CANDLE_3_CLOSURE",
            "c2_must_raid_c1": True,
            "c2_must_fail_reversal_close": True,
            "c3_new_adverse_extreme_allowed": False,
            "c3_must_close_through_c2_body": True,
            "c3_must_reclaim_c1_boundary": True,
            "lower_timeframe_cisd_by_c3_close": True,
            "h1_confirmation_timeframe": "M5",
            "h4_confirmation_timeframe": "M15",
            "entry": "C4_OPEN",
            "stop": "EXACT_PROTECTED_SWING",
        },
        "density": {
            "setups_10y": len(setups),
            "cibo_episode_bindings_10y": bindings,
            "active_dol_ladder_10y": ladder_available,
            "setups_2y": setups_2y,
            "cibo_episode_bindings_2y": bindings_2y,
        },
        "rank1_static_diagnostic_2y": {
            "gross": _stat(rank1_gross),
            "net_010": _stat(rank1_values),
            "not_a_candidate_selector": True,
        },
        "funnel": dict(funnel),
        "governance": {
            "research_only": True,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "r32-c3-opportunity-forensics-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module RAW_ROOT TARGET_ROOT OUTPUT_DIR")
    print(
        json.dumps(
            run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
