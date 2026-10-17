"""R2-C close-unmitigated old-level characterization for VT08 CRT PURE.

R2-C is an engineering ablation over R2-A.  It changes exactly one reference
semantic:

R2-A:
    an old M15 swing level is consumed on the first strict wick breach.

R2-C:
    an old M15 swing level remains structurally valid until a candle BODY CLOSES
    beyond it.  Before that close-mitigation, the first direction-compatible
    wick raid may become a Model #1 source event.

Everything else stays frozen to R2-A:
- scheduled H4 parent CRT;
- M15 execution;
- swing-strength-1 reference discovery;
- only the first direction-aligned Model #1 source event per parent C3;
- no fallback / re-entry / Journey / KOD;
- body-close Model #1 confirmation;
- next contiguous M15 open engineering fill;
- source-candle structural stop;
- R1 C1 50% midpoint target;
- R1 C3-close expiry;
- same-M15 STOP_FIRST.

This is research-only QORE engineering.  No claim of RomeoTPT source authority
is made for the close-unmitigated policy.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    ReplayBar,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    BreachGroup,
    M15Bar,
    Model1LabTrade,
    OldLevel,
    ParentCrt,
    ReferenceKind,
    ReferencePolicy,
    _confirmation,
    _confirmed_pivot,
    _fold,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2C_CLOSE_UNMITIGATED_MODEL1_001"
SCHEMA = "qore.vt08.crt_pure.r2c_close_unmitigated_model1.v1"
REFERENCE_POLICY = ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1


def build_close_unmitigated_breach_groups(
    bars: tuple[M15Bar, ...],
) -> dict[datetime, tuple[BreachGroup, ...]]:
    """Build first qualifying raids while invalidating levels only on body close.

    A level is added only after its pivot is causally confirmed.  It is removed
    when a closed M15 finishes beyond the level.  A wick-only raid does not
    structurally mitigate the level.  The first direction-compatible raid emits
    one research event and retires that reference from this ablation so repeated
    raids cannot manufacture density.
    """

    active_highs: list[OldLevel] = []
    active_lows: list[OldLevel] = []
    grouped: dict[datetime, tuple[BreachGroup, ...]] = {}

    for index, bar in enumerate(bars):
        # Eligibility is evaluated from information available before this candle
        # closes.  Therefore this candle may itself become the first Model #1
        # raid even when its close also mitigates the old level.  A prior close
        # beyond the level would already have removed it on an earlier iteration.
        raided_highs = tuple(
            item for item in active_highs if bar.high_price > item.price
        )
        raided_lows = tuple(
            item for item in active_lows if bar.low_price < item.price
        )

        events: list[BreachGroup] = []
        event_highs: tuple[OldLevel, ...] = ()
        event_lows: tuple[OldLevel, ...] = ()
        if raided_highs and bar.up_close:
            event_highs = raided_highs
            events.append(
                BreachGroup(
                    source_candle=bar,
                    kind=ReferenceKind.OLD_HIGH,
                    policy=REFERENCE_POLICY,
                    references=event_highs,
                )
            )

        if raided_lows and bar.down_close:
            event_lows = raided_lows
            events.append(
                BreachGroup(
                    source_candle=bar,
                    kind=ReferenceKind.OLD_LOW,
                    policy=REFERENCE_POLICY,
                    references=event_lows,
                )
            )

        if events:
            grouped[bar.opened_at] = tuple(events)

        close_broken_highs = tuple(
            item for item in active_highs if bar.close_price > item.price
        )
        close_broken_lows = tuple(
            item for item in active_lows if bar.close_price < item.price
        )
        retired_highs = set(event_highs) | set(close_broken_highs)
        retired_lows = set(event_lows) | set(close_broken_lows)
        if retired_highs:
            active_highs = [item for item in active_highs if item not in retired_highs]
        if retired_lows:
            active_lows = [item for item in active_lows if item not in retired_lows]

        for level in _confirmed_pivot(bars, index, REFERENCE_POLICY):
            if level.kind is ReferenceKind.OLD_HIGH:
                active_highs.append(level)
            else:
                active_lows.append(level)

    return grouped


def first_r2c_trade(
    *,
    parent: ParentCrt,
    m15_by_time: dict[datetime, M15Bar],
    breaches: dict[datetime, tuple[BreachGroup, ...]],
) -> tuple[Model1LabTrade | None, str]:
    """Use only the first aligned R2-C Model #1 source inside the parent C3."""

    c3_m15 = tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if parent.c3_opened_at <= opened_at < parent.c3_closed_at
    )
    if not c3_m15:
        return None, "NO_COMPLETE_M15_IN_C3"

    expected_kind = (
        ReferenceKind.OLD_LOW
        if parent.direction is CrtPureCandidateDirection.BULLISH
        else ReferenceKind.OLD_HIGH
    )

    selected: BreachGroup | None = None
    source_index = -1
    for index, source in enumerate(c3_m15):
        for group in breaches.get(source.opened_at, ()):
            if group.kind is expected_kind:
                selected = group
                source_index = index
                break
        if selected is not None:
            break

    if selected is None:
        return None, "NO_DIRECTION_ALIGNED_CLOSE_UNMITIGATED_SOURCE"

    source = c3_m15[source_index]
    confirmed = _confirmation(
        source,
        c3_m15[source_index + 1 :],
        parent.direction,
    )
    if confirmed is None:
        return None, "FIRST_CLOSE_UNMITIGATED_SOURCE_NOT_CONFIRMED"

    confirmation_bar, entry_bar = confirmed
    trade = _resolve_trade(
        parent=parent,
        group=selected,
        confirmation=confirmation_bar,
        entry_bar=entry_bar,
        c3_m15=c3_m15,
    )
    if trade is None:
        return None, "CONFIRMED_SOURCE_INVALID_RISK_GEOMETRY"

    return (
        replace(
            trade,
            schema=SCHEMA,
            identity=IDENTITY,
            reference_policy="CLOSE_UNMITIGATED_SWING_STRENGTH_1",
        ),
        "TRADE_CREATED",
    )


def run_r2c(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[tuple[Model1LabTrade, ...], dict[str, int], int]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    counters: dict[str, int] = {}
    trades: list[Model1LabTrade] = []
    for parent in parents:
        trade, reason = first_r2c_trade(
            parent=parent,
            m15_by_time=m15_by_time,
            breaches=breaches,
        )
        counters[reason] = counters.get(reason, 0) + 1
        if trade is not None:
            trades.append(trade)

    if len({item.c3_opened_at for item in trades}) != len(trades):
        raise RuntimeError("R2-C invariant violation: more than one trade per parent CRT")
    return tuple(trades), counters, len(parents)


def build_report(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[Model1LabTrade, ...]]:
    trades, counters, parent_count = run_r2c(market, bars)
    report = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "parent_crt_count": parent_count,
        "ablation_against": "VT08_CRT_PURE_R2A_MODEL1_MINIMAL_REFERENCE_001",
        "single_changed_dimension": "OLD_LEVEL_MITIGATION_SEMANTICS",
        "reference_policy": "CLOSE_UNMITIGATED_SWING_STRENGTH_1",
        "reference_policy_authority": "QORE_ENGINEERING_HYPOTHESIS",
        "close_beyond_level_invalidates_reference": True,
        "wick_only_raid_invalidates_reference": False,
        "same_reference_multiple_raid_entries_allowed": False,
        "event_counters": counters,
        "full_2y": _summary(trades),
        "year_1": _summary(_fold(trades, START, FOLD_1_END)),
        "year_2": _summary(_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        "target_policy": "R1_C1_50_PERCENT_CONTROL",
        "expiry_policy": "R1_C3_CLOSE_CONTROL",
        "same_m15_ambiguity": "STOP_FIRST",
        "single_source_event_per_parent": True,
        "later_source_fallback_allowed": False,
        "journey_reentry_allowed": False,
        "research_only": True,
        "candidate_certified": False,
        "promotion_forbidden_from_single_ablation_pnl": True,
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
    print("CRT_R2C_CLOSE_UNMITIGATED_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
