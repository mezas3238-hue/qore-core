"""R2-D alternate-entry rescue lab for VT08 CRT PURE.

This lab applies the external Level-B audit as a falsifiable hypothesis, not as
automatic source authority.  It re-evaluates ONLY R2-C parents whose first
direction-aligned Model #1 source candle never obtained the frozen Model #1
body-close confirmation.

Three entry families are tested independently:

- CISD: causal break of the opening level of the last adverse M15 delivery leg;
- FVG: first direction-aligned three-candle M15 fair-value-gap confirmation;
- OTE: first directional reaction inside a causal 62%-79% retracement zone of
  the already-observed post-source impulse.

The families never vote, OR together, or select each other by PnL.  One WAIT may
be rescued by several families and overlap is reported explicitly.  Standalone
time-based entry, Order Block and KOD are intentionally NOT machine-authorized
here because their exact trigger contracts remain source-ambiguous.

Controls stay frozen to isolate entry-family behavior:
- same scheduled H4 parent CRT and R2-C first source event;
- M15 execution;
- next contiguous M15 open fill after the alternate trigger closes;
- stop = original R2-C Model #1 source-candle extreme;
- target = frozen R1 C1 50% midpoint;
- expiry = frozen R1 C3 close;
- same-M15 ambiguity = STOP_FIRST.

Research only.  No demo/live/production/capital authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    ReplayBar,
    _midpoint,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    ParentCrt,
    ReferenceKind,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
    first_r2c_trade,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2D_WAIT_RESCUE_ENTRY_FAMILIES_001"
SCHEMA = "qore.vt08.crt_pure.r2d_wait_rescue_entry_families.v1"
WAIT_REASON = "FIRST_CLOSE_UNMITIGATED_SOURCE_NOT_CONFIRMED"


class RescueFamily(StrEnum):
    CISD = "CISD"
    FVG = "FVG"
    OTE = "OTE"


@dataclass(frozen=True, slots=True)
class RescueSignal:
    family: RescueFamily
    confirmation: M15Bar
    entry_bar: M15Bar
    detail: str


@dataclass(frozen=True, slots=True)
class RescueTrade:
    schema: str
    identity: str
    market: str
    family: str
    parent_direction: str
    timing_triplet: str
    c3_opened_at: str
    source_opened_at: str
    confirmation_opened_at: str
    entry_opened_at: str
    entry_price_relative: int
    stop_price_relative: int
    target_price_relative: str
    exit_price_relative: str
    exit_reason: str
    r_multiple: float
    trigger_detail: str
    research_only: bool = True
    candidate_certified: bool = False
    demo_eligible: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False


def _c3_m15(
    parent: ParentCrt,
    m15_by_time: dict[datetime, M15Bar],
) -> tuple[M15Bar, ...]:
    return tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if parent.c3_opened_at <= opened_at < parent.c3_closed_at
    )


def _first_aligned_source(
    *,
    parent: ParentCrt,
    c3_m15: tuple[M15Bar, ...],
    breaches: dict[datetime, tuple[BreachGroup, ...]],
) -> tuple[int, BreachGroup] | None:
    expected_kind = (
        ReferenceKind.OLD_LOW
        if parent.direction is CrtPureCandidateDirection.BULLISH
        else ReferenceKind.OLD_HIGH
    )
    for index, source in enumerate(c3_m15):
        for group in breaches.get(source.opened_at, ()):
            if group.kind is expected_kind:
                return index, group
    return None


def _next_contiguous(
    bars: tuple[M15Bar, ...],
    index: int,
) -> M15Bar | None:
    if index + 1 >= len(bars):
        return None
    current = bars[index]
    nxt = bars[index + 1]
    return nxt if nxt.opened_at == current.closed_at else None


def _cisd_signal(
    *,
    direction: CrtPureCandidateDirection,
    bars: tuple[M15Bar, ...],
    source_index: int,
) -> RescueSignal | None:
    """Engineering formalization of Level-B CISD language.

    The adverse delivery leg is the contiguous same-direction candle run ending
    at the source candle.  CISD occurs only when a later candle body closes
    through the opening price of the first candle in that leg.
    """

    source = bars[source_index]

    def adverse(bar: M15Bar) -> bool:
        return (
            bar.down_close
            if direction is CrtPureCandidateDirection.BULLISH
            else bar.up_close
        )

    if not adverse(source):
        return None

    leg_start = source_index
    while leg_start > 0:
        previous = bars[leg_start - 1]
        current = bars[leg_start]
        if previous.closed_at != current.opened_at or not adverse(previous):
            break
        leg_start -= 1

    level = bars[leg_start].open_price
    for index in range(source_index + 1, len(bars)):
        bar = bars[index]
        confirmed = (
            bar.close_price > level
            if direction is CrtPureCandidateDirection.BULLISH
            else bar.close_price < level
        )
        if not confirmed:
            continue
        entry = _next_contiguous(bars, index)
        if entry is None:
            return None
        return RescueSignal(
            family=RescueFamily.CISD,
            confirmation=bar,
            entry_bar=entry,
            detail=f"adverse_leg_open={level};leg_start={bars[leg_start].opened_at.isoformat()}",
        )
    return None


def _fvg_signal(
    *,
    direction: CrtPureCandidateDirection,
    bars: tuple[M15Bar, ...],
    source_index: int,
) -> RescueSignal | None:
    """First causal direction-aligned three-candle M15 FVG after the source."""

    for third_index in range(source_index + 2, len(bars)):
        first = bars[third_index - 2]
        second = bars[third_index - 1]
        third = bars[third_index]
        if not (
            first.closed_at == second.opened_at
            and second.closed_at == third.opened_at
        ):
            continue
        confirmed = (
            third.low_price > first.high_price
            if direction is CrtPureCandidateDirection.BULLISH
            else third.high_price < first.low_price
        )
        if not confirmed:
            continue
        entry = _next_contiguous(bars, third_index)
        if entry is None:
            return None
        return RescueSignal(
            family=RescueFamily.FVG,
            confirmation=third,
            entry_bar=entry,
            detail=(
                f"bullish_gap={first.high_price}:{third.low_price}"
                if direction is CrtPureCandidateDirection.BULLISH
                else f"bearish_gap={third.high_price}:{first.low_price}"
            ),
        )
    return None


def _ote_signal(
    *,
    direction: CrtPureCandidateDirection,
    bars: tuple[M15Bar, ...],
    source_index: int,
) -> RescueSignal | None:
    """First causal 62%-79% retracement reaction after observed displacement.

    The OTE zone for a candidate bar is computed only from favorable extremes
    that were already closed BEFORE that candidate bar.  The current bar cannot
    enlarge its own zone.
    """

    source = bars[source_index]
    if direction is CrtPureCandidateDirection.BULLISH:
        origin = Decimal(source.low_price)
        favorable: Decimal | None = None
        for index in range(source_index + 1, len(bars)):
            bar = bars[index]
            if favorable is not None and favorable > origin:
                span = favorable - origin
                zone_low = favorable - Decimal("0.79") * span
                zone_high = favorable - Decimal("0.62") * span
                overlaps = (
                    Decimal(bar.low_price) <= zone_high
                    and Decimal(bar.high_price) >= zone_low
                )
                if overlaps and bar.up_close:
                    entry = _next_contiguous(bars, index)
                    if entry is None:
                        return None
                    return RescueSignal(
                        family=RescueFamily.OTE,
                        confirmation=bar,
                        entry_bar=entry,
                        detail=(
                            f"origin={origin};impulse_extreme={favorable};"
                            f"zone={zone_low}:{zone_high}"
                        ),
                    )
            high = Decimal(bar.high_price)
            favorable = high if favorable is None else max(favorable, high)
        return None

    origin = Decimal(source.high_price)
    favorable = None
    for index in range(source_index + 1, len(bars)):
        bar = bars[index]
        if favorable is not None and favorable < origin:
            span = origin - favorable
            zone_low = favorable + Decimal("0.62") * span
            zone_high = favorable + Decimal("0.79") * span
            overlaps = (
                Decimal(bar.low_price) <= zone_high
                and Decimal(bar.high_price) >= zone_low
            )
            if overlaps and bar.down_close:
                entry = _next_contiguous(bars, index)
                if entry is None:
                    return None
                return RescueSignal(
                    family=RescueFamily.OTE,
                    confirmation=bar,
                    entry_bar=entry,
                    detail=(
                        f"origin={origin};impulse_extreme={favorable};"
                        f"zone={zone_low}:{zone_high}"
                    ),
                )
        low = Decimal(bar.low_price)
        favorable = low if favorable is None else min(favorable, low)
    return None


def _resolve_trade(
    *,
    parent: ParentCrt,
    source: M15Bar,
    signal: RescueSignal,
    c3_m15: tuple[M15Bar, ...],
) -> RescueTrade | None:
    entry = signal.entry_bar.open_price
    target = _midpoint(parent.c1.high_price, parent.c1.low_price)
    direction = parent.direction

    if direction is CrtPureCandidateDirection.BULLISH:
        stop = source.low_price
        if stop >= entry or target <= Decimal(entry):
            return None
        risk = entry - stop
    else:
        stop = source.high_price
        if stop <= entry or target >= Decimal(entry):
            return None
        risk = stop - entry

    exit_reason = "C3_CLOSE"
    exit_price = Decimal(c3_m15[-1].close_price)
    r_value: Decimal | None = None
    for bar in c3_m15:
        if bar.opened_at < signal.entry_bar.opened_at:
            continue
        if direction is CrtPureCandidateDirection.BULLISH:
            stop_hit = bar.low_price <= stop
            target_hit = Decimal(bar.high_price) >= target
        else:
            stop_hit = bar.high_price >= stop
            target_hit = Decimal(bar.low_price) <= target
        if stop_hit:
            exit_reason = "STOP"
            exit_price = Decimal(stop)
            r_value = Decimal("-1")
            break
        if target_hit:
            exit_reason = "TARGET_50"
            exit_price = target
            r_value = (
                (target - Decimal(entry)) / Decimal(risk)
                if direction is CrtPureCandidateDirection.BULLISH
                else (Decimal(entry) - target) / Decimal(risk)
            )
            break

    if r_value is None:
        r_value = (
            (exit_price - Decimal(entry)) / Decimal(risk)
            if direction is CrtPureCandidateDirection.BULLISH
            else (Decimal(entry) - exit_price) / Decimal(risk)
        )

    return RescueTrade(
        schema=SCHEMA,
        identity=IDENTITY,
        market=parent.market.value,
        family=signal.family.value,
        parent_direction=direction.value,
        timing_triplet=parent.triplet,
        c3_opened_at=parent.c3_opened_at.isoformat(),
        source_opened_at=source.opened_at.isoformat(),
        confirmation_opened_at=signal.confirmation.opened_at.isoformat(),
        entry_opened_at=signal.entry_bar.opened_at.isoformat(),
        entry_price_relative=entry,
        stop_price_relative=stop,
        target_price_relative=str(target),
        exit_price_relative=str(exit_price),
        exit_reason=exit_reason,
        r_multiple=round(float(r_value), 8),
        trigger_detail=signal.detail,
    )


def _summary(trades: tuple[RescueTrade, ...]) -> dict[str, Any]:
    ordered = tuple(sorted(trades, key=lambda item: item.entry_opened_at))
    values = tuple(item.r_multiple for item in ordered)
    positive = tuple(value for value in values if value > 0)
    negative = tuple(value for value in values if value < 0)
    gross_profit = sum(positive)
    gross_loss = -sum(negative)
    equity = 0.0
    peak = 0.0
    dd = 0.0
    losing = 0
    longest = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            losing += 1
            longest = max(longest, losing)
        else:
            losing = 0
    return {
        "trades": len(values),
        "wins": len(positive),
        "losses": len(negative),
        "flat": sum(value == 0 for value in values),
        "profit_factor": None if gross_loss == 0 else round(gross_profit / gross_loss, 8),
        "total_r": round(sum(values), 8),
        "mean_r": None if not values else round(sum(values) / len(values), 8),
        "max_drawdown_r": round(dd, 8),
        "longest_losing_streak": longest,
        "target_50_exits": sum(item.exit_reason == "TARGET_50" for item in ordered),
        "stop_exits": sum(item.exit_reason == "STOP" for item in ordered),
        "c3_close_exits": sum(item.exit_reason == "C3_CLOSE" for item in ordered),
    }


def _fold_rescue(
    trades: tuple[RescueTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[RescueTrade, ...]:
    return tuple(
        item
        for item in trades
        if start <= datetime.fromisoformat(item.entry_opened_at) < end
    )


def run_r2d(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[RescueFamily, tuple[RescueTrade, ...]], dict[str, Any]]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    rows: dict[RescueFamily, list[RescueTrade]] = {
        family: [] for family in RescueFamily
    }
    wait_parent_ids: set[str] = set()
    rescued_by_parent: dict[str, set[RescueFamily]] = {}
    invalid_geometry: dict[RescueFamily, int] = {family: 0 for family in RescueFamily}

    for parent in parents:
        trade, reason = first_r2c_trade(
            parent=parent,
            m15_by_time=m15_by_time,
            breaches=breaches,
        )
        if trade is not None or reason != WAIT_REASON:
            continue

        c3 = _c3_m15(parent, m15_by_time)
        selected = _first_aligned_source(
            parent=parent,
            c3_m15=c3,
            breaches=breaches,
        )
        if selected is None:
            raise RuntimeError("R2-D invariant: R2-C WAIT lost its first source event")
        source_index, group = selected
        source = group.source_candle
        parent_id = parent.c3_opened_at.isoformat()
        wait_parent_ids.add(parent_id)

        signals = (
            _cisd_signal(
                direction=parent.direction,
                bars=c3,
                source_index=source_index,
            ),
            _fvg_signal(
                direction=parent.direction,
                bars=c3,
                source_index=source_index,
            ),
            _ote_signal(
                direction=parent.direction,
                bars=c3,
                source_index=source_index,
            ),
        )
        for signal in signals:
            if signal is None:
                continue
            rescued = _resolve_trade(
                parent=parent,
                source=source,
                signal=signal,
                c3_m15=c3,
            )
            if rescued is None:
                invalid_geometry[signal.family] += 1
                continue
            rows[signal.family].append(rescued)
            rescued_by_parent.setdefault(parent_id, set()).add(signal.family)

    frozen = {family: tuple(items) for family, items in rows.items()}
    any_rescued = set(rescued_by_parent)
    exactly_one = sum(len(families) == 1 for families in rescued_by_parent.values())
    multiple = sum(len(families) > 1 for families in rescued_by_parent.values())
    diagnostics = {
        "parent_crt_count": len(parents),
        "r2c_wait_parent_count": len(wait_parent_ids),
        "any_family_rescued_parent_count": len(any_rescued),
        "unrescued_parent_count": len(wait_parent_ids - any_rescued),
        "exactly_one_family_parent_count": exactly_one,
        "multiple_family_overlap_parent_count": multiple,
        "invalid_risk_geometry_after_trigger": {
            family.value: invalid_geometry[family] for family in RescueFamily
        },
        "family_parent_counts": {
            family.value: len({item.c3_opened_at for item in frozen[family]})
            for family in RescueFamily
        },
    }
    return frozen, diagnostics


def build_report(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[RescueTrade, ...]]:
    per_family, diagnostics = run_r2d(market, bars)
    all_trades = tuple(
        trade for family in RescueFamily for trade in per_family[family]
    )
    report = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "hypothesis_origin": "EXTERNAL_LEVEL_B_AUDIT_APPLIED_AS_FALSIFIABLE_RESEARCH",
        "population": "R2C_FIRST_CLOSE_UNMITIGATED_SOURCE_NOT_CONFIRMED_ONLY",
        "diagnostics": diagnostics,
        "families": {
            family.value: {
                "authority": "ENGINEERING_FORMALIZATION_OF_LEVEL_B_HYPOTHESIS",
                "full_2y": _summary(per_family[family]),
                "year_1": _summary(
                    _fold_rescue(per_family[family], START, FOLD_1_END)
                ),
                "year_2": _summary(
                    _fold_rescue(per_family[family], FOLD_1_END, END_EXCLUSIVE)
                ),
            }
            for family in RescueFamily
        },
        "disabled_as_standalone_triggers": {
            "TIME_BASED": "context/stratification only; clock alone grants no entry",
            "ORDER_BLOCK": "exact deterministic source contract not closed",
            "KOD": "exact deterministic source contract not closed",
        },
        "controls": {
            "stop": "R2C_MODEL1_SOURCE_CANDLE_EXTREME",
            "target": "R1_C1_50_PERCENT_CONTROL",
            "expiry": "R1_C3_CLOSE_CONTROL",
            "same_m15_ambiguity": "STOP_FIRST",
            "fill": "NEXT_CONTIGUOUS_M15_OPEN_AFTER_TRIGGER_CLOSE",
            "family_combination": "NONE; arms evaluated independently",
        },
        "research_only": True,
        "candidate_certified": False,
        "promotion_forbidden_from_single_lab_pnl": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return report, all_trades


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    bars = load_two_year_m5(market)
    report, trades = build_report(market, bars)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for item in trades:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
    print("CRT_R2D_WAIT_RESCUE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
