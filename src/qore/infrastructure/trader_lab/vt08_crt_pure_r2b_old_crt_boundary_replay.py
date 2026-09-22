"""R2-B prior-CRT-boundary Model #1 characterization for VT08 CRT PURE.

R2-B tests a source-native old-CRTH/CRL reference family without pretending the
exact ownership geometry is canonical.  RomeoTPT explicitly teaches reactions
from old CRTH/CRL, while the exact deterministic priority among all possible old
levels remains open.

Engineering policy for this characterization:
- an old CRTH/CRL is the C1 high/low of a previously completed parent CRT;
- the level becomes eligible only after that parent CRT is causal at C3 open;
- the level is consumed on its first strict M15 breach;
- several eligible old CRT boundaries breached by one source candle deduplicate
  into one Model #1 source event;
- only the first direction-aligned source event inside the current parent C3 is
  eligible;
- no fallback, re-entry, Journey or KOD entry;
- Model #1 confirmation is body-close based;
- fill is the next contiguous M15 open;
- stop is the Model #1 source-candle extreme;
- R1 50% destination and C3-close expiry are retained as controls.

This is research-only.  It grants no certification or deployment authority.
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
    M15Bar,
    ParentCrt,
    _confirmation,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2B_MODEL1_OLD_CRT_BOUNDARY_001"
SCHEMA = "qore.vt08.crt_pure.r2b_model1_old_crt_boundary.v1"
REFERENCE_POLICY = "UNTOUCHED_PRIOR_PARENT_CRT_BOUNDARY"


class CrtBoundaryKind(StrEnum):
    OLD_CRTH = "OLD_CRTH"
    OLD_CRTL = "OLD_CRTL"


@dataclass(frozen=True, slots=True)
class CrtBoundaryLevel:
    kind: CrtBoundaryKind
    price: int
    originating_parent_c3_opened_at: datetime
    activated_at: datetime

    def __post_init__(self) -> None:
        if self.activated_at != self.originating_parent_c3_opened_at:
            raise ValueError("CRT boundary activation must equal parent causal C3 open")

    @property
    def evidence_id(self) -> str:
        return (
            f"{REFERENCE_POLICY}:{self.kind.value}:"
            f"{self.originating_parent_c3_opened_at.isoformat()}:{self.price}"
        )


@dataclass(frozen=True, slots=True)
class CrtBoundaryBreach:
    source_candle: M15Bar
    kind: CrtBoundaryKind
    references: tuple[CrtBoundaryLevel, ...]

    def __post_init__(self) -> None:
        if not self.references:
            raise ValueError("CRT boundary breach requires at least one reference")
        if any(item.kind is not self.kind for item in self.references):
            raise ValueError("CRT boundary breach reference kinds must agree")


@dataclass(frozen=True, slots=True)
class R2BTrade:
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
    source_canonical: bool = False
    promotion_forbidden_from_pnl: bool = True


def build_prior_crt_boundary_breaches(
    *,
    parents: tuple[ParentCrt, ...],
    m15: tuple[M15Bar, ...],
) -> dict[datetime, tuple[CrtBoundaryBreach, ...]]:
    """Build first-breach events from already-causal parent CRT boundaries."""

    parents_by_activation: dict[datetime, list[ParentCrt]] = {}
    for parent in parents:
        parents_by_activation.setdefault(parent.c3_opened_at, []).append(parent)

    active_highs: list[CrtBoundaryLevel] = []
    active_lows: list[CrtBoundaryLevel] = []
    grouped: dict[datetime, tuple[CrtBoundaryBreach, ...]] = {}

    for bar in sorted(m15, key=lambda item: item.opened_at):
        for parent in parents_by_activation.get(bar.opened_at, ()):
            active_highs.append(
                CrtBoundaryLevel(
                    kind=CrtBoundaryKind.OLD_CRTH,
                    price=parent.c1.high_price,
                    originating_parent_c3_opened_at=parent.c3_opened_at,
                    activated_at=parent.c3_opened_at,
                )
            )
            active_lows.append(
                CrtBoundaryLevel(
                    kind=CrtBoundaryKind.OLD_CRTL,
                    price=parent.c1.low_price,
                    originating_parent_c3_opened_at=parent.c3_opened_at,
                    activated_at=parent.c3_opened_at,
                )
            )

        breached_highs = tuple(item for item in active_highs if bar.high_price > item.price)
        breached_lows = tuple(item for item in active_lows if bar.low_price < item.price)

        if breached_highs:
            active_highs = [item for item in active_highs if item not in breached_highs]
        if breached_lows:
            active_lows = [item for item in active_lows if item not in breached_lows]

        events: list[CrtBoundaryBreach] = []
        if breached_highs and bar.up_close:
            events.append(
                CrtBoundaryBreach(
                    source_candle=bar,
                    kind=CrtBoundaryKind.OLD_CRTH,
                    references=breached_highs,
                )
            )
        if breached_lows and bar.down_close:
            events.append(
                CrtBoundaryBreach(
                    source_candle=bar,
                    kind=CrtBoundaryKind.OLD_CRTL,
                    references=breached_lows,
                )
            )
        if events:
            grouped[bar.opened_at] = tuple(events)

    return grouped


def _older_references(
    breach: CrtBoundaryBreach,
    *,
    current_parent: ParentCrt,
) -> tuple[CrtBoundaryLevel, ...]:
    return tuple(
        item
        for item in breach.references
        if item.originating_parent_c3_opened_at < current_parent.c3_opened_at
    )


def first_prior_crt_boundary_model1_trade(
    *,
    parent: ParentCrt,
    m15_by_time: dict[datetime, M15Bar],
    breaches: dict[datetime, tuple[CrtBoundaryBreach, ...]],
) -> tuple[R2BTrade | None, str]:
    """Use only the first aligned prior-CRT-boundary Model #1 source event."""

    c3_m15 = tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if parent.c3_opened_at <= opened_at < parent.c3_closed_at
    )
    if not c3_m15:
        return None, "NO_COMPLETE_M15_IN_C3"

    expected_kind = (
        CrtBoundaryKind.OLD_CRTL
        if parent.direction is CrtPureCandidateDirection.BULLISH
        else CrtBoundaryKind.OLD_CRTH
    )

    selected: CrtBoundaryBreach | None = None
    selected_refs: tuple[CrtBoundaryLevel, ...] = ()
    source_index = -1
    for index, source in enumerate(c3_m15):
        for breach in breaches.get(source.opened_at, ()):
            if breach.kind is not expected_kind:
                continue
            older = _older_references(breach, current_parent=parent)
            if not older:
                continue
            selected = breach
            selected_refs = older
            source_index = index
            break
        if selected is not None:
            break

    if selected is None:
        return None, "NO_PRIOR_CRT_BOUNDARY_MODEL1_SOURCE"

    source = c3_m15[source_index]
    confirmed = _confirmation(
        source,
        c3_m15[source_index + 1 :],
        parent.direction,
    )
    if confirmed is None:
        return None, "FIRST_PRIOR_CRT_BOUNDARY_SOURCE_NOT_CONFIRMED"

    confirmation_bar, entry_bar = confirmed
    entry = entry_bar.open_price
    target = _midpoint(parent.c1.high_price, parent.c1.low_price)

    if parent.direction is CrtPureCandidateDirection.BULLISH:
        stop = source.low_price
        if stop >= entry or target <= Decimal(entry):
            return None, "CONFIRMED_SOURCE_INVALID_RISK_GEOMETRY"
        risk = entry - stop
    else:
        stop = source.high_price
        if stop <= entry or target >= Decimal(entry):
            return None, "CONFIRMED_SOURCE_INVALID_RISK_GEOMETRY"
        risk = stop - entry

    exit_reason = "C3_CLOSE"
    exit_price = Decimal(c3_m15[-1].close_price)
    r_value: Decimal | None = None
    for bar in c3_m15:
        if bar.opened_at < entry_bar.opened_at:
            continue
        if parent.direction is CrtPureCandidateDirection.BULLISH:
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
                if parent.direction is CrtPureCandidateDirection.BULLISH
                else (Decimal(entry) - target) / Decimal(risk)
            )
            break

    if r_value is None:
        r_value = (
            (exit_price - Decimal(entry)) / Decimal(risk)
            if parent.direction is CrtPureCandidateDirection.BULLISH
            else (Decimal(entry) - exit_price) / Decimal(risk)
        )

    return (
        R2BTrade(
            schema=SCHEMA,
            identity=IDENTITY,
            market=parent.market.value,
            reference_policy=REFERENCE_POLICY,
            reference_count=len(selected_refs),
            reference_ids=tuple(item.evidence_id for item in selected_refs),
            parent_direction=parent.direction.value,
            timing_triplet=parent.triplet,
            c3_opened_at=parent.c3_opened_at.isoformat(),
            source_opened_at=source.opened_at.isoformat(),
            confirmation_opened_at=confirmation_bar.opened_at.isoformat(),
            entry_opened_at=entry_bar.opened_at.isoformat(),
            entry_price_relative=entry,
            stop_price_relative=stop,
            target_price_relative=str(target),
            exit_price_relative=str(exit_price),
            exit_reason=exit_reason,
            r_multiple=round(float(r_value), 8),
        ),
        "TRADE_CREATED",
    )


def _trade_summary(trades: tuple[R2BTrade, ...]) -> dict[str, Any]:
    values = tuple(
        item.r_multiple
        for item in sorted(trades, key=lambda item: item.entry_opened_at)
    )
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
        "target_50_exits": sum(item.exit_reason == "TARGET_50" for item in trades),
        "stop_exits": sum(item.exit_reason == "STOP" for item in trades),
        "c3_close_exits": sum(item.exit_reason == "C3_CLOSE" for item in trades),
        "multi_reference_source_events": sum(item.reference_count > 1 for item in trades),
    }


def _trade_fold(
    trades: tuple[R2BTrade, ...],
    start: datetime,
    end: datetime,
) -> tuple[R2BTrade, ...]:
    return tuple(
        item
        for item in trades
        if start <= datetime.fromisoformat(item.entry_opened_at) < end
    )


def run_r2b(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[tuple[R2BTrade, ...], dict[str, int], int]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_prior_crt_boundary_breaches(parents=parents, m15=m15)

    counters: dict[str, int] = {}
    trades: list[R2BTrade] = []
    for parent in parents:
        trade, reason = first_prior_crt_boundary_model1_trade(
            parent=parent,
            m15_by_time=m15_by_time,
            breaches=breaches,
        )
        counters[reason] = counters.get(reason, 0) + 1
        if trade is not None:
            trades.append(trade)

    if len({item.c3_opened_at for item in trades}) != len(trades):
        raise RuntimeError("R2-B invariant violation: more than one trade per parent CRT")
    return tuple(trades), counters, len(parents)


def build_report(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[R2BTrade, ...]]:
    trades, counters, parent_count = run_r2b(market, bars)
    report = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "parent_crt_count": parent_count,
        "reference_policy": REFERENCE_POLICY,
        "reference_family": "OLD_CRTH_CRL",
        "reference_family_source_authority": "ROMEO_PRIMARY_SOURCE_NATIVE",
        "ownership_geometry_authority": "ENGINEERING_CHARACTERIZATION",
        "source_canonical": False,
        "event_counters": counters,
        "full_2y": _trade_summary(trades),
        "year_1": _trade_summary(_trade_fold(trades, START, FOLD_1_END)),
        "year_2": _trade_summary(_trade_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        "target_policy": "R1_C1_50_PERCENT_CONTROL",
        "expiry_policy": "R1_C3_CLOSE_CONTROL",
        "same_m15_ambiguity": "STOP_FIRST",
        "single_source_event_per_parent": True,
        "later_source_fallback_allowed": False,
        "journey_reentry_allowed": False,
        "research_only": True,
        "candidate_certified": False,
        "promotion_forbidden_from_pnl": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return report, trades


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
    print("CRT_R2B_OLD_CRT_BOUNDARY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
