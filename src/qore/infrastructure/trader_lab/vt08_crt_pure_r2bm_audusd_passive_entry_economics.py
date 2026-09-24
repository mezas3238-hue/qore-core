"""R2-BM AUDUSD passive-entry economic replay.

Extends R2-BK's frozen passive-entry arms into economic replay without changing
CRT signal generation, competition, structural stop, fixed 1.5R target, C3
expiry, or BE_CLOSE_075 management.

Important causal rules:
- passive fills require an observed M5 range touch within the frozen 30m horizon;
- a structural stop touched on an earlier M5 before the passive fill invalidates
  the pending order;
- if stop and target are both reachable inside the same M15 after fill,
  STOP_FIRST is applied, preserving the frozen CRT ambiguity contract;
- no synthetic fills and no fill after the horizon;
- BE_CLOSE_075 is armed only by a completed M15 close observed after fill and
  becomes effective on the next M15 bar.

Research only. No arm is promoted automatically.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ValidationWindow,
    _rolling_parents,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bk_audusd_passive_entry_capacity import (
    BASE_POLICY,
    END,
    HORIZON,
    MARKET,
    START,
    YEARS,
    EntryArm,
    _level,
    _valid_risk,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2BM_AUDUSD_PASSIVE_ENTRY_ECONOMICS_001"
SCHEMA = "qore.vt08.crt_pure.r2bm_audusd_passive_entry_economics.v1"
TARGET_R = Decimal("1.5")
BE_TRIGGER_R = Decimal("0.75")
COST_STRESS_R: tuple[float, ...] = (0.02, 0.05)


@dataclass(frozen=True, slots=True)
class PassiveTrade:
    arm: str
    parent_direction: str
    timing_triplet: str
    reference_count: int
    source_opened_at: str
    confirmation_opened_at: str
    decision_opened_at: str
    entry_opened_at: str
    entry_price_relative: str
    stop_price_relative: str
    target_price_relative: str
    exit_price_relative: str
    exit_reason: str
    r_multiple: float
    fill_delay_minutes: int
    protection_armed: bool


def _r_at_price(
    *,
    bullish: bool,
    entry: Decimal,
    risk: Decimal,
    price: Decimal,
) -> Decimal:
    if bullish:
        return (price - entry) / risk
    return (entry - price) / risk


def _stop_touched(
    *,
    bullish: bool,
    stop: Decimal,
    bar: Any,
) -> bool:
    if bullish:
        return Decimal(bar.low_price) <= stop
    return Decimal(bar.high_price) >= stop


def _target_touched(
    *,
    bullish: bool,
    target: Decimal,
    bar: Any,
) -> bool:
    if bullish:
        return Decimal(bar.high_price) >= target
    return Decimal(bar.low_price) <= target


def _m15_exit(
    *,
    bullish: bool,
    current_stop: Decimal,
    target: Decimal,
    bars: tuple[Any, ...],
) -> tuple[str, Decimal] | None:
    stop_hit = any(
        _stop_touched(
            bullish=bullish,
            stop=current_stop,
            bar=bar,
        )
        for bar in bars
    )
    target_hit = any(
        _target_touched(
            bullish=bullish,
            target=target,
            bar=bar,
        )
        for bar in bars
    )
    if stop_hit:
        return "STOP", current_stop
    if target_hit:
        return "TARGET_FIXED_1_5R", target
    return None


def _find_fill(
    *,
    arm: EntryArm,
    level: Decimal,
    stop: Decimal,
    bullish: bool,
    decision_at: datetime,
    c3_closed_at: datetime,
    m5_by_time: dict[datetime, Any],
) -> tuple[datetime | None, str]:
    if arm is EntryArm.NEXT_OPEN_CONTROL:
        return decision_at, "CONTROL"

    end = min(decision_at + HORIZON, c3_closed_at)
    cursor = decision_at
    while cursor < end:
        bar = m5_by_time.get(cursor)
        if bar is None:
            return None, "MISSING_M5"
        level_touched = Decimal(bar.low_price) <= level <= Decimal(bar.high_price)
        stop_touched = _stop_touched(
            bullish=bullish,
            stop=stop,
            bar=bar,
        )
        if level_touched:
            return cursor, (
                "FILL_AND_STOP_SAME_M5"
                if stop_touched
                else "FILL"
            )
        if stop_touched:
            return None, "STOP_INVALIDATED_BEFORE_FILL"
        cursor += timedelta(minutes=5)
    return None, "NO_FILL_WITHIN_30M"


def _simulate(
    *,
    arm: EntryArm,
    parent: ParentCrt,
    source: M15Bar,
    confirmation: M15Bar,
    decision_bar: M15Bar,
    fill_at: datetime,
    level: Decimal,
    m5_by_time: dict[datetime, Any],
) -> PassiveTrade | None:
    bullish = parent.direction is CrtPureCandidateDirection.BULLISH
    stop = Decimal(
        source.low_price if bullish else source.high_price
    )
    risk = abs(level - stop)
    if risk <= 0:
        return None
    target = (
        level + TARGET_R * risk
        if bullish
        else level - TARGET_R * risk
    )

    current_stop = stop
    protection_armed = False
    exit_reason = "C3_CLOSE"
    exit_price: Decimal | None = None
    last_close: Decimal | None = None
    bucket_start = fill_at.replace(
        minute=(fill_at.minute // 15) * 15,
        second=0,
        microsecond=0,
    )

    while bucket_start < parent.c3_closed_at:
        bucket_end = min(
            bucket_start + timedelta(minutes=15),
            parent.c3_closed_at,
        )
        cursor = max(fill_at, bucket_start)
        bucket: list[Any] = []
        while cursor < bucket_end:
            bar = m5_by_time.get(cursor)
            if bar is None:
                return None
            bucket.append(bar)
            cursor += timedelta(minutes=5)

        if bucket:
            last_close = Decimal(bucket[-1].close_price)
            outcome = _m15_exit(
                bullish=bullish,
                current_stop=current_stop,
                target=target,
                bars=tuple(bucket),
            )
            if outcome is not None:
                exit_reason, exit_price = outcome
                break

            close_r = _r_at_price(
                bullish=bullish,
                entry=level,
                risk=risk,
                price=last_close,
            )
            if close_r >= BE_TRIGGER_R and current_stop != level:
                current_stop = (
                    max(current_stop, level)
                    if bullish
                    else min(current_stop, level)
                )
                protection_armed = current_stop == level

        bucket_start += timedelta(minutes=15)

    if exit_price is None:
        if last_close is None:
            return None
        exit_price = last_close

    exit_r = _r_at_price(
        bullish=bullish,
        entry=level,
        risk=risk,
        price=exit_price,
    )
    if exit_reason == "TARGET_FIXED_1_5R":
        exit_r = TARGET_R

    return PassiveTrade(
        arm=arm.value,
        parent_direction=parent.direction.value,
        timing_triplet=parent.triplet,
        reference_count=0,
        source_opened_at=source.opened_at.isoformat(),
        confirmation_opened_at=confirmation.opened_at.isoformat(),
        decision_opened_at=decision_bar.opened_at.isoformat(),
        entry_opened_at=fill_at.isoformat(),
        entry_price_relative=str(level),
        stop_price_relative=str(stop),
        target_price_relative=str(target),
        exit_price_relative=str(exit_price),
        exit_reason=exit_reason,
        r_multiple=round(float(exit_r), 8),
        fill_delay_minutes=int(
            (fill_at - decision_bar.opened_at).total_seconds() / 60
        ),
        protection_armed=protection_armed,
    )

def _summary(rows: tuple[PassiveTrade, ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(rows, key=lambda row: row.entry_opened_at)
    )
    values = tuple(row.r_multiple for row in ordered)
    positive = tuple(value for value in values if value > 0)
    negative = tuple(value for value in values if value < 0)
    gross_profit = sum(positive)
    gross_loss = -sum(negative)
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    losing = 0
    longest = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
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
        "profit_factor": (
            None if gross_loss == 0 else round(gross_profit / gross_loss, 8)
        ),
        "total_r": round(sum(values), 8),
        "mean_r": (
            None if not values else round(sum(values) / len(values), 8)
        ),
        "max_drawdown_r": round(max_drawdown, 8),
        "longest_losing_streak": longest,
        "full_stop_count": sum(
            row.exit_reason == "STOP"
            and abs(row.r_multiple + 1.0) <= 1e-9
            for row in ordered
        ),
        "target_exits": sum(
            row.exit_reason == "TARGET_FIXED_1_5R" for row in ordered
        ),
        "c3_close_exits": sum(
            row.exit_reason == "C3_CLOSE" for row in ordered
        ),
        "protected_trades": sum(row.protection_armed for row in ordered),
    }


def _stress(
    rows: tuple[PassiveTrade, ...],
    cost_r: float,
) -> dict[str, Any]:
    values = tuple(row.r_multiple - cost_r for row in rows)
    positive = tuple(value for value in values if value > 0)
    negative = tuple(value for value in values if value < 0)
    gross_profit = sum(positive)
    gross_loss = -sum(negative)
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    losing = 0
    longest = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value < 0:
            losing += 1
            longest = max(longest, losing)
        else:
            losing = 0
    return {
        "trades": len(values),
        "profit_factor": (
            None if gross_loss == 0 else round(gross_profit / gross_loss, 8)
        ),
        "total_r": round(sum(values), 8),
        "mean_r": (
            None if not values else round(sum(values) / len(values), 8)
        ),
        "max_drawdown_r": round(max_drawdown, 8),
        "longest_losing_streak": longest,
        "cost_r_per_trade": cost_r,
    }


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    rows: tuple[PassiveTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[PassiveTrade, ...]:
    return tuple(
        row
        for row in rows
        if start <= datetime.fromisoformat(row.entry_opened_at) < end
    )


def _temporal(rows: tuple[PassiveTrade, ...]) -> dict[str, Any]:
    annual = {
        f"{year}_{year + 1}": _summary(
            _slice(rows, _year_start(year), _year_start(year + 1))
        )
        for year in range(START.year, END.year)
    }
    rolling_2y = {
        f"{year}_{year + 2}": _summary(
            _slice(rows, _year_start(year), _year_start(year + 2))
        )
        for year in range(START.year, END.year - 1)
    }
    return {
        "annual": annual,
        "rolling_2y": rolling_2y,
        "positive_annual_windows": sum(
            float(item["total_r"]) > 0 for item in annual.values()
        ),
        "annual_window_count": len(annual),
        "positive_rolling_2y_windows": sum(
            float(item["total_r"]) > 0 for item in rolling_2y.values()
        ),
        "rolling_2y_window_count": len(rolling_2y),
    }


def run_replay() -> tuple[
    dict[EntryArm, tuple[PassiveTrade, ...]],
    dict[str, Any],
]:
    window = ValidationWindow(market=MARKET, start=START, end=END)
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    m5_by_time = {bar.opened_at: bar for bar in bars}
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    trades: dict[EntryArm, list[PassiveTrade]] = {
        arm: [] for arm in EntryArm
    }
    diagnostics: dict[EntryArm, Counter[str]] = {
        arm: Counter() for arm in EntryArm
    }

    for parent in parents:
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if selected is None:
            continue

        observation, confirmation, decision_bar = selected
        source = observation.group.source_candle
        bullish = parent.direction is CrtPureCandidateDirection.BULLISH
        stop = Decimal(
            source.low_price if bullish else source.high_price
        )

        for arm in EntryArm:
            diag = diagnostics[arm]
            diag["opportunities"] += 1
            level = _level(
                arm=arm,
                source=source,
                confirmation=confirmation,
                entry_bar=decision_bar,
            )
            if not _valid_risk(
                parent=parent,
                source=source,
                entry=level,
            ):
                diag["invalid_structural_risk"] += 1
                continue

            fill_at, fill_state = _find_fill(
                arm=arm,
                level=level,
                stop=stop,
                bullish=bullish,
                decision_at=decision_bar.opened_at,
                c3_closed_at=parent.c3_closed_at,
                m5_by_time=m5_by_time,
            )
            diag[fill_state] += 1
            if fill_at is None:
                continue

            trade = _simulate(
                arm=arm,
                parent=parent,
                source=source,
                confirmation=confirmation,
                decision_bar=decision_bar,
                fill_at=fill_at,
                level=level,
                m5_by_time=m5_by_time,
            )
            if trade is None:
                diag["lifecycle_unavailable"] += 1
                continue

            trade = PassiveTrade(
                **{
                    **asdict(trade),
                    "reference_count": len(observation.group.references),
                }
            )
            trades[arm].append(trade)
            diag["economic_trade"] += 1

    frozen = {
        arm: tuple(
            sorted(rows, key=lambda row: row.entry_opened_at)
        )
        for arm, rows in trades.items()
    }

    arms: dict[str, Any] = {}
    for arm in EntryArm:
        rows = frozen[arm]
        arms[arm.value] = {
            "diagnostics": dict(diagnostics[arm]),
            "economics": _summary(rows),
            "trades_per_year": round(len(rows) / YEARS, 8),
            "temporal": _temporal(rows),
            "cost_stress": {
                f"COST_{cost:.2f}R": _stress(rows, cost)
                for cost in COST_STRESS_R
            },
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": YEARS,
        "base_policy": BASE_POLICY.value,
        "entry_arms_frozen_from_r2bk": [arm.value for arm in EntryArm],
        "fill_horizon_minutes": int(HORIZON.total_seconds() / 60),
        "fill_resolution": "M5",
        "fill_rule": "OBSERVED_RANGE_TOUCH_ONLY",
        "pre_fill_stop_invalidation": True,
        "same_fill_bar_stop_precedence": "STOP_FIRST",
        "same_m15_stop_target_ambiguity": "STOP_FIRST",
        "structural_stop": "SOURCE_CANDLE_EXTREME",
        "target": "FIXED_1_5R_FROM_ACTUAL_FILL",
        "expiry": "C3_CLOSE",
        "management": "BE_CLOSE_075_AFTER_COMPLETED_M15_CLOSE",
        "cost_stress_r": list(COST_STRESS_R),
        "arms": arms,
        "automatic_winner_ranking": False,
        "entry_arm_promoted": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    arms, report = run_replay()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for arm in EntryArm:
            for trade in arms[arm]:
                handle.write(
                    json.dumps(asdict(trade), sort_keys=True) + "\n"
                )
    print("CRT_R2BM_PASSIVE_ECONOMICS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
