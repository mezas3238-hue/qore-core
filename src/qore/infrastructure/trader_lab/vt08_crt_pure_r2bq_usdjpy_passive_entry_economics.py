"""R2-BQ USDJPY market-specific passive-entry economic replay.

R2-BN failed to create positive expectancy from small Expected-R memories.
R2-BP then established market-specific passive-entry capacity without importing
AUDUSD entry levels. R2-BQ now evaluates the frozen R2-BP family economically.

Invariants:
- exact USDJPY R2-BL high-density parent/source population;
- observed M5 fills only, within the frozen 30m horizon;
- pending order dies if the original source stop is touched before fill;
- same-M5 fill/stop ambiguity is STOP_FIRST;
- original source-candle structural stop;
- fixed 1.5R target from the actual fill;
- C3-close expiry;
- no BE/protection imported from AUDUSD;
- no automatic winner promotion.

Research only.
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bp_usdjpy_passive_entry_capacity import (
    BASE_POLICY,
    END,
    HORIZON,
    MARKET,
    START,
    YEARS,
    EntryArm,
    _fill_state,
    _level,
    _stop,
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

IDENTITY = "VT08_CRT_PURE_R2BQ_USDJPY_PASSIVE_ENTRY_ECONOMICS_001"
SCHEMA = "qore.vt08.crt_pure.r2bq_usdjpy_passive_entry_economics.v1"
TARGET_R = Decimal("1.5")
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


def _simulate(
    *,
    arm: EntryArm,
    parent: ParentCrt,
    observation: Any,
    confirmation: M15Bar,
    decision_bar: M15Bar,
    fill_at: datetime,
    level: Decimal,
    stop: Decimal,
    m5_by_time: dict[datetime, Any],
) -> PassiveTrade | None:
    bullish = parent.direction is CrtPureCandidateDirection.BULLISH
    risk = abs(level - stop)
    if risk <= 0:
        return None
    target = (
        level + TARGET_R * risk
        if bullish
        else level - TARGET_R * risk
    )

    cursor = fill_at
    last_close: Decimal | None = None
    exit_reason = "C3_CLOSE"
    exit_price: Decimal | None = None

    while cursor < parent.c3_closed_at:
        bar = m5_by_time.get(cursor)
        if bar is None:
            return None
        last_close = Decimal(bar.close_price)

        # Conservative ambiguity: stop first.
        if _stop_touched(bullish=bullish, stop=stop, bar=bar):
            exit_reason = "STOP"
            exit_price = stop
            break
        if _target_touched(bullish=bullish, target=target, bar=bar):
            exit_reason = "TARGET_FIXED_1_5R"
            exit_price = target
            break
        cursor += timedelta(minutes=5)

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
        reference_count=len(observation.group.references),
        source_opened_at=observation.group.source_candle.opened_at.isoformat(),
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
    )


def _summary(rows: tuple[PassiveTrade, ...]) -> dict[str, Any]:
    ordered = tuple(sorted(rows, key=lambda row: row.entry_opened_at))
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
        stop = _stop(parent=parent, source=source)

        for arm in EntryArm:
            diag = diagnostics[arm]
            diag["opportunities"] += 1
            level = _level(
                arm=arm,
                parent=parent,
                source=source,
                decision_bar=decision_bar,
            )
            if not _valid_risk(
                parent=parent,
                stop=stop,
                level=level,
            ):
                diag["invalid_structural_risk"] += 1
                continue

            fill_at, fill_state = _fill_state(
                arm=arm,
                parent=parent,
                level=level,
                stop=stop,
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
                observation=observation,
                confirmation=confirmation,
                decision_bar=decision_bar,
                fill_at=fill_at,
                level=level,
                stop=stop,
                m5_by_time=m5_by_time,
            )
            if trade is None:
                diag["lifecycle_unavailable"] += 1
                continue
            trades[arm].append(trade)
            diag["economic_trade"] += 1

    frozen = {
        arm: tuple(sorted(rows, key=lambda row: row.entry_opened_at))
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
        "entry_arms_frozen_from_r2bp": [arm.value for arm in EntryArm],
        "fill_horizon_minutes": int(HORIZON.total_seconds() / 60),
        "fill_resolution": "M5",
        "fill_rule": "OBSERVED_RANGE_TOUCH_ONLY",
        "pre_fill_stop_invalidation": True,
        "same_fill_bar_stop_precedence": "STOP_FIRST",
        "structural_stop": "SOURCE_CANDLE_EXTREME",
        "target": "FIXED_1_5R_FROM_ACTUAL_FILL",
        "expiry": "C3_CLOSE",
        "management": "OFF",
        "audusd_entry_arm_transferred": False,
        "audusd_protection_transferred": False,
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
    print("CRT_R2BQ_USDJPY_PASSIVE_ECONOMICS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
