"""R2 Model #1 old-level ambiguity lab for VT08 CRT PURE.

This lab does NOT promote a reference-selection rule.  It evaluates two causal,
pre-declared engineering interpretations of RomeoTPT's qualitative "old high /
old low" language:

- confirmed untouched M15 swing pivots, strength 1;
- confirmed untouched M15 swing pivots, strength 2.

Every reference is created only after its right-side confirmation candles close.
It remains active until the first strict breach.  If one source candle breaches
multiple active references, those references are deduplicated into one Model #1
source event because the source candle, confirmation boundary and structural stop
are identical.

Economic characterization is event-level research only.  It keeps the frozen R1
50% destination and C3-close expiry while replacing entry/stop with Model #1:
confirmation body close -> next M15 open, stop beyond source candle extreme.
No policy may be promoted by selecting whichever PnL is better.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    AggregatedCandle,
    ReplayBar,
    _aggregate,
    _days,
    _midpoint,
    _segment,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_btcusd_schedule_aware_replay import (
    _session_segment,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_ctrader_market_calendar import (
    load_btcusd_ctrader_calendar,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
    candidate_direction_from_turtle_soup,
    classify_range_outcome,
)
from qore.infrastructure.traders.crt_pure_timing_policy import (
    NY,
    utc_triplet_windows_for_local_date,
)

IDENTITY = "VT08_CRT_PURE_R2_MODEL1_REFERENCE_AMBIGUITY_LAB_001"
SCHEMA = "qore.vt08.crt_pure.r2_model1_reference_ambiguity_lab.v1"
M15 = timedelta(minutes=15)


class ReferencePolicy(IntEnum):
    UNTOUCHED_SWING_STRENGTH_1 = 1
    UNTOUCHED_SWING_STRENGTH_2 = 2


class ReferenceKind(StrEnum):
    OLD_HIGH = "OLD_HIGH"
    OLD_LOW = "OLD_LOW"


@dataclass(frozen=True, slots=True)
class M15Bar:
    opened_at: datetime
    open_price: int
    high_price: int
    low_price: int
    close_price: int

    @property
    def closed_at(self) -> datetime:
        return self.opened_at + M15

    @property
    def up_close(self) -> bool:
        return self.close_price > self.open_price

    @property
    def down_close(self) -> bool:
        return self.close_price < self.open_price


@dataclass(frozen=True, slots=True)
class OldLevel:
    kind: ReferenceKind
    price: int
    pivot_opened_at: datetime
    confirmed_at: datetime
    policy: ReferencePolicy

    @property
    def evidence_id(self) -> str:
        return (
            f"{self.policy.name}:{self.kind.value}:"
            f"{self.pivot_opened_at.astimezone(UTC).isoformat()}:{self.price}"
        )


@dataclass(frozen=True, slots=True)
class BreachGroup:
    source_candle: M15Bar
    kind: ReferenceKind
    policy: ReferencePolicy
    references: tuple[OldLevel, ...]

    def __post_init__(self) -> None:
        if not self.references:
            raise ValueError("breach group requires at least one old level")
        if any(item.kind is not self.kind for item in self.references):
            raise ValueError("breach group reference kinds must agree")
        if any(item.policy is not self.policy for item in self.references):
            raise ValueError("breach group policies must agree")


@dataclass(frozen=True, slots=True)
class ParentCrt:
    market: CrtPureMarket
    direction: CrtPureCandidateDirection
    triplet: str
    c3_opened_at: datetime
    c3_closed_at: datetime
    c1: AggregatedCandle
    c2: AggregatedCandle
    c3_m5: tuple[ReplayBar, ...]


@dataclass(frozen=True, slots=True)
class Model1LabTrade:
    schema: str
    identity: str
    market: str
    reference_policy: str
    reference_count: int
    reference_ids: tuple[str, ...]
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
    research_only: bool = True
    promotion_forbidden_from_lab_pnl: bool = True


def aggregate_complete_m15(bars: tuple[ReplayBar, ...]) -> tuple[M15Bar, ...]:
    by_time = {bar.opened_at: bar for bar in bars}
    result: list[M15Bar] = []
    for opened_at in sorted(by_time):
        if opened_at.second or opened_at.microsecond or opened_at.minute % 15:
            continue
        rows = tuple(by_time.get(opened_at + timedelta(minutes=offset)) for offset in (0, 5, 10))
        if any(item is None for item in rows):
            continue
        first, second, third = rows
        assert first is not None and second is not None and third is not None
        result.append(
            M15Bar(
                opened_at=opened_at,
                open_price=first.open_price,
                high_price=max(first.high_price, second.high_price, third.high_price),
                low_price=min(first.low_price, second.low_price, third.low_price),
                close_price=third.close_price,
            )
        )
    return tuple(result)


def _contiguous(window: tuple[M15Bar, ...]) -> bool:
    return all(right.opened_at - left.opened_at == M15 for left, right in zip(window[:-1], window[1:]))


def _confirmed_pivot(
    bars: tuple[M15Bar, ...],
    confirmation_index: int,
    policy: ReferencePolicy,
) -> tuple[OldLevel, ...]:
    strength = int(policy)
    center = confirmation_index - strength
    left = center - strength
    if left < 0:
        return ()
    window = bars[left : confirmation_index + 1]
    if len(window) != (2 * strength) + 1 or not _contiguous(window):
        return ()
    pivot = bars[center]
    neighbors = tuple(item for index, item in enumerate(window) if index != strength)
    rows: list[OldLevel] = []
    if all(pivot.high_price > item.high_price for item in neighbors):
        rows.append(
            OldLevel(
                kind=ReferenceKind.OLD_HIGH,
                price=pivot.high_price,
                pivot_opened_at=pivot.opened_at,
                confirmed_at=bars[confirmation_index].closed_at,
                policy=policy,
            )
        )
    if all(pivot.low_price < item.low_price for item in neighbors):
        rows.append(
            OldLevel(
                kind=ReferenceKind.OLD_LOW,
                price=pivot.low_price,
                pivot_opened_at=pivot.opened_at,
                confirmed_at=bars[confirmation_index].closed_at,
                policy=policy,
            )
        )
    return tuple(rows)


def build_first_breach_groups(
    bars: tuple[M15Bar, ...],
    policy: ReferencePolicy,
) -> dict[datetime, tuple[BreachGroup, ...]]:
    """Return first-breach events; references are consumed on any strict breach."""

    active_highs: list[OldLevel] = []
    active_lows: list[OldLevel] = []
    grouped: dict[datetime, tuple[BreachGroup, ...]] = {}

    for index, bar in enumerate(bars):
        breached_highs = tuple(item for item in active_highs if bar.high_price > item.price)
        breached_lows = tuple(item for item in active_lows if bar.low_price < item.price)
        if breached_highs:
            active_highs = [item for item in active_highs if item not in breached_highs]
        if breached_lows:
            active_lows = [item for item in active_lows if item not in breached_lows]

        events: list[BreachGroup] = []
        if breached_highs and bar.up_close:
            events.append(
                BreachGroup(
                    source_candle=bar,
                    kind=ReferenceKind.OLD_HIGH,
                    policy=policy,
                    references=breached_highs,
                )
            )
        if breached_lows and bar.down_close:
            events.append(
                BreachGroup(
                    source_candle=bar,
                    kind=ReferenceKind.OLD_LOW,
                    policy=policy,
                    references=breached_lows,
                )
            )
        if events:
            grouped[bar.opened_at] = tuple(events)

        for level in _confirmed_pivot(bars, index, policy):
            if level.kind is ReferenceKind.OLD_HIGH:
                active_highs.append(level)
            else:
                active_lows.append(level)

    return grouped


def _parent_direction(c1: AggregatedCandle, c2: AggregatedCandle) -> CrtPureCandidateDirection | None:
    outcome = classify_range_outcome(
        reference_high=float(c1.high_price),
        reference_low=float(c1.low_price),
        observed_high=float(c2.high_price),
        observed_low=float(c2.low_price),
        observed_close=float(c2.close_price),
    )
    if outcome.value != "TURTLE_SOUP":
        return None
    return candidate_direction_from_turtle_soup(
        reference_high=float(c1.high_price),
        reference_low=float(c1.low_price),
        observed_high=float(c2.high_price),
        observed_low=float(c2.low_price),
        observed_close=float(c2.close_price),
    )


def build_parent_crts(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[ParentCrt, ...]:
    by_time = {bar.opened_at: bar for bar in bars}
    calendar = load_btcusd_ctrader_calendar() if market is CrtPureMarket.BTCUSD else None
    start_day = (START - timedelta(days=1)).astimezone(NY).date()
    end_day = END_EXCLUSIVE.astimezone(NY).date()
    result: list[ParentCrt] = []

    for day in _days(start_day, end_day):
        local_noon = datetime(day.year, day.month, day.day, 12, tzinfo=NY)
        for timing_index, window in enumerate(
            utc_triplet_windows_for_local_date(market, local_noon)
        ):
            if not START <= window.candle_3_open < END_EXCLUSIVE:
                continue
            if calendar is None:
                c1_m5 = _segment(by_time, window.candle_1_open, window.candle_2_open)
                c2_m5 = _segment(by_time, window.candle_2_open, window.candle_3_open)
                c3_m5 = _segment(by_time, window.candle_3_open, window.window_close)
            else:
                c1_m5, _, _, _ = _session_segment(
                    by_time, window.candle_1_open, window.candle_2_open, calendar
                )
                c2_m5, _, _, _ = _session_segment(
                    by_time, window.candle_2_open, window.candle_3_open, calendar
                )
                c3_m5, _, _, _ = _session_segment(
                    by_time, window.candle_3_open, window.window_close, calendar
                )
            if c1_m5 is None or c2_m5 is None or c3_m5 is None:
                continue
            c1 = _aggregate(c1_m5, window.candle_1_open, window.candle_2_open)
            c2 = _aggregate(c2_m5, window.candle_2_open, window.candle_3_open)
            direction = _parent_direction(c1, c2)
            if direction is None:
                continue
            result.append(
                ParentCrt(
                    market=market,
                    direction=direction,
                    triplet=str(timing_index + 1),
                    c3_opened_at=window.candle_3_open,
                    c3_closed_at=window.window_close,
                    c1=c1,
                    c2=c2,
                    c3_m5=c3_m5,
                )
            )
    return tuple(result)


def _confirmation(
    source: M15Bar,
    subsequent: tuple[M15Bar, ...],
    direction: CrtPureCandidateDirection,
) -> tuple[M15Bar, M15Bar] | None:
    for index, bar in enumerate(subsequent):
        confirmed = (
            bar.close_price > source.open_price
            if direction is CrtPureCandidateDirection.BULLISH
            else bar.close_price < source.open_price
        )
        if not confirmed:
            continue
        if index + 1 >= len(subsequent):
            return None
        next_bar = subsequent[index + 1]
        if next_bar.opened_at != bar.closed_at:
            return None
        return bar, next_bar
    return None


def _resolve_trade(
    *,
    parent: ParentCrt,
    group: BreachGroup,
    confirmation: M15Bar,
    entry_bar: M15Bar,
    c3_m15: tuple[M15Bar, ...],
) -> Model1LabTrade | None:
    entry = entry_bar.open_price
    target = _midpoint(parent.c1.high_price, parent.c1.low_price)
    direction = parent.direction
    if direction is CrtPureCandidateDirection.BULLISH:
        stop = group.source_candle.low_price
        if stop >= entry or target <= Decimal(entry):
            return None
        risk = entry - stop
    else:
        stop = group.source_candle.high_price
        if stop <= entry or target >= Decimal(entry):
            return None
        risk = stop - entry

    exit_reason = "C3_CLOSE"
    exit_price = Decimal(c3_m15[-1].close_price)
    r_value: Decimal | None = None
    for bar in c3_m15:
        if bar.opened_at < entry_bar.opened_at:
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

    return Model1LabTrade(
        schema=SCHEMA,
        identity=IDENTITY,
        market=parent.market.value,
        reference_policy=group.policy.name,
        reference_count=len(group.references),
        reference_ids=tuple(item.evidence_id for item in group.references),
        parent_direction=direction.value,
        timing_triplet=parent.triplet,
        c3_opened_at=parent.c3_opened_at.isoformat(),
        source_opened_at=group.source_candle.opened_at.isoformat(),
        confirmation_opened_at=confirmation.opened_at.isoformat(),
        entry_opened_at=entry_bar.opened_at.isoformat(),
        entry_price_relative=entry,
        stop_price_relative=stop,
        target_price_relative=str(target),
        exit_price_relative=str(exit_price),
        exit_reason=exit_reason,
        r_multiple=round(float(r_value), 8),
    )


def run_policy(
    *,
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
    parents: tuple[ParentCrt, ...],
    policy: ReferencePolicy,
) -> tuple[Model1LabTrade, ...]:
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_first_breach_groups(m15, policy)
    trades: list[Model1LabTrade] = []

    for parent in parents:
        c3_m15 = tuple(
            m15_by_time[opened_at]
            for opened_at in sorted(m15_by_time)
            if parent.c3_opened_at <= opened_at < parent.c3_closed_at
        )
        if not c3_m15:
            continue
        for source_index, source in enumerate(c3_m15):
            groups = breaches.get(source.opened_at, ())
            expected_kind = (
                ReferenceKind.OLD_LOW
                if parent.direction is CrtPureCandidateDirection.BULLISH
                else ReferenceKind.OLD_HIGH
            )
            for group in groups:
                if group.kind is not expected_kind:
                    continue
                confirmed = _confirmation(
                    source,
                    c3_m15[source_index + 1 :],
                    parent.direction,
                )
                if confirmed is None:
                    continue
                confirmation_bar, entry_bar = confirmed
                trade = _resolve_trade(
                    parent=parent,
                    group=group,
                    confirmation=confirmation_bar,
                    entry_bar=entry_bar,
                    c3_m15=c3_m15,
                )
                if trade is not None:
                    trades.append(trade)
    return tuple(trades)


def _summary(trades: tuple[Model1LabTrade, ...]) -> dict[str, Any]:
    values = tuple(item.r_multiple for item in sorted(trades, key=lambda item: item.entry_opened_at))
    positive = tuple(item for item in values if item > 0)
    negative = tuple(item for item in values if item < 0)
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
        "flat": sum(item == 0 for item in values),
        "profit_factor": None if gross_loss == 0 else round(gross_profit / gross_loss, 8),
        "total_r": round(sum(values), 8),
        "mean_r": None if not values else round(sum(values) / len(values), 8),
        "max_drawdown_r": round(dd, 8),
        "longest_losing_streak": longest,
        "target_50_exits": sum(item.exit_reason == "TARGET_50" for item in trades),
        "stop_exits": sum(item.exit_reason == "STOP" for item in trades),
        "c3_close_exits": sum(item.exit_reason == "C3_CLOSE" for item in trades),
        "multi_reference_source_events": sum(item.reference_count > 1 for item in trades),
    }


def _fold(
    trades: tuple[Model1LabTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[Model1LabTrade, ...]:
    return tuple(
        item
        for item in trades
        if start <= datetime.fromisoformat(item.entry_opened_at) < end
    )


def build_report(market: CrtPureMarket, bars: tuple[ReplayBar, ...]) -> tuple[dict[str, Any], tuple[Model1LabTrade, ...]]:
    parents = build_parent_crts(market, bars)
    all_trades: list[Model1LabTrade] = []
    policies: dict[str, Any] = {}
    for policy in ReferencePolicy:
        trades = run_policy(market=market, bars=bars, parents=parents, policy=policy)
        all_trades.extend(trades)
        policies[policy.name] = {
            "definition": (
                "confirmed untouched M15 swing pivot; consumed on first strict breach; "
                f"swing strength={int(policy)}"
            ),
            "source_authority": "ENGINEERING_AMBIGUITY_POLICY",
            "full_2y": _summary(trades),
            "year_1": _summary(_fold(trades, START, FOLD_1_END)),
            "year_2": _summary(_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        }

    report = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "parent_crt_count": len(parents),
        "source_contract": {
            "parent": "scheduled H4 CRT / Turtle Soup",
            "execution": "H4 CRT -> M15 Model #1",
            "old_level_language": "old high / old low",
            "confirmation": "body close beyond specific Model #1 source candle",
            "stop": "Model #1 source candle extreme",
        },
        "lab_invariants": {
            "old_level_priority_from_romeo": "UNRESOLVED",
            "reference_policy_promotion_from_pnl": False,
            "references_must_be_confirmed_before_breach": True,
            "references_consumed_on_first_strict_breach": True,
            "same_source_candle_multiple_references_deduplicated": True,
            "target": "R1 50 percent midpoint retained to isolate entry-family behavior",
            "expiry": "R1 C3 close retained",
            "same_m15_ambiguity": "STOP_FIRST",
        },
        "policies": policies,
        "research_only": True,
        "candidate_certified": False,
        "r2_ready": False,
        "promotion_forbidden_from_lab_pnl": True,
    }
    return report, tuple(all_trades)


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
        for row in trades:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    print("CRT_MODEL1_REFERENCE_LAB_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
