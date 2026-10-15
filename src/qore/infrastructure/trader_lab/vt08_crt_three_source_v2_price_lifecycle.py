"""Frozen V2 hypotheses -> causal price-only DOL/invalidation observation.

PRE-REGISTERED BEFORE OUTCOMES:
docs/research/VT08_CRT_THREE_SOURCE_V2_LIFECYCLE_PREREG_2026-10-15.md

Never a trade simulation: no broker orders, bid/ask fills, lots, sizing, PnL,
returns, stop-loss orders, equity, or profitability certification.
Same-M5 DOL plus invalidation is conservatively INVALIDATION_FIRST_AMBIGUOUS.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v1_full_h4_census import (
    H4,
    M5,
    _aggregate,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v2_full_h4_census import (
    M15,
    _m15_at,
    full_utc_h4_v2_census,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SCHEMA = "qore.vt08.crt_three_source_v2.price_only_lifecycle.dev.v1"
SOURCE_POLICY = "VT08_CRT_THREE_SOURCE_QORE_V2"


def observe_price_only_path(
    *,
    direction: str,
    decision_at: datetime,
    c3_open: datetime,
    invalidation_relative: int,
    target_double_relative: int,
    m5: dict[datetime, ReplayBar],
) -> tuple[str, str | None, int]:
    """Return outcome, first-hit time, examined M5 count, with NO fill inference."""
    if direction not in ("BULLISH", "BEARISH"):
        raise ValueError("invalid CRT direction")
    if decision_at.tzinfo is None or c3_open.tzinfo is None:
        raise ValueError("all decision clocks must have an explicit timezone")
    if decision_at <= c3_open or decision_at > c3_open + H4:
        raise ValueError("decision cannot precede or exceed H4 C3")
    # V2's 16th M15 pair can be confirmed exactly at H4 C3 close.
    # No post-decision C3 price path exists, so it is terminal without
    # an executable or hypothetical price fill. Do NOT peek into next H4.
    if decision_at == c3_open + H4:
        return "EXPIRED_AT_C3_CLOSE_NO_POST_DECISION_WINDOW", None, 0
    if (decision_at - c3_open).total_seconds() % 300:
        raise ValueError("decision clock must align with source M5")
    if type(invalidation_relative) is not int or type(target_double_relative) is not int:
        raise ValueError("structural price levels require original integer coordinates")
    if (
        (direction == "BULLISH" and 2 * invalidation_relative >= target_double_relative)
        or (
            direction == "BEARISH"
            and 2 * invalidation_relative <= target_double_relative
        )
    ):
        return "UNKNOWN_BARRIER_GEOMETRY_INVALID", None, 0
    first = m5.get(decision_at.astimezone(UTC))
    if first is None:
        return "UNKNOWN_MISSING_ENTRY_OPEN_PRICE", None, 0
    entry = first.open_price
    if (
        (direction == "BULLISH" and (
            entry <= invalidation_relative or 2 * entry >= target_double_relative
        ))
        or
        (direction == "BEARISH" and (
            entry >= invalidation_relative or 2 * entry <= target_double_relative
        ))
    ):
        return "UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER", None, 0

    examined = 0
    event_clock = decision_at.astimezone(UTC)
    c3_end = (c3_open + H4).astimezone(UTC)
    while event_clock < c3_end:
        candle = m5.get(event_clock)
        if candle is None:
            return "UNKNOWN_MISSING_M5_BEFORE_TERMINAL", None, examined
        if candle.opened_at.astimezone(UTC) != event_clock:
            raise ValueError("source M5 timestamp contradicts index")
        if not (
            candle.low_price
            <= min(candle.open_price, candle.close_price)
            <= max(candle.open_price, candle.close_price)
            <= candle.high_price
        ):
            raise ValueError("invalid original source M5 OHLC geometry")
        examined += 1
        if direction == "BULLISH":
            touched_invalidation = candle.low_price <= invalidation_relative
            touched_destination = 2 * candle.high_price >= target_double_relative
        else:
            touched_invalidation = candle.high_price >= invalidation_relative
            touched_destination = 2 * candle.low_price <= target_double_relative
        if touched_invalidation and touched_destination:
            return "INVALIDATION_FIRST_AMBIGUOUS_SAME_M5", event_clock.isoformat(), examined
        if touched_invalidation:
            return "INVALIDATION_FIRST", event_clock.isoformat(), examined
        if touched_destination:
            return "DESTINATION_FIRST", event_clock.isoformat(), examined
        event_clock += M5
    return "EXPIRED_WITHOUT_TOUCH", None, examined


def evaluate_frozen_v2_lifecycle(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Reproduce frozen V2 source events; observe subsequent prices only afterward."""
    source_manifest, source_events = full_utc_h4_v2_census(market, bars)
    m5 = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    if len(m5) != len(bars):
        raise ValueError("duplicate M5 time prohibited")
    expected_count = source_manifest["states"].get("CONCEPTUAL_CANDIDATE", 0)
    events = tuple(
        event for event in source_events
        if event["state"] == "CONCEPTUAL_CANDIDATE"
    )
    if len(events) != expected_count:
        raise ValueError("frozen V2 candidate reconciliation failed")
    observations: list[dict[str, Any]] = []
    outcome_counts: Counter[str] = Counter()
    yearly: dict[str, Counter[str]] = defaultdict(Counter)
    keys: set[str] = set()
    for event in events:
        if event["policy_id"] != SOURCE_POLICY:
            raise ValueError("source V2 version mismatch")
        if event["is_trade"] or event["grants_volume_or_broker_authority"]:
            raise ValueError("false trade authority attached to frozen V2 event")
        event_id = event["source_event_id"]
        if event_id in keys:
            raise ValueError("duplicated frozen source hypothesis")
        keys.add(event_id)
        c3_open = datetime.fromisoformat(event["c3_H4_opened_at_utc"])
        decision_at = datetime.fromisoformat(
            event["first_conceptual_decision_clock_utc"]
        )
        c1_start = c3_open - 2 * H4
        parent_bars = tuple(m5.get(c1_start + i * M5) for i in range(48))
        if any(bar is None for bar in parent_bars):
            raise ValueError("missing frozen parent H4 C1")
        c1 = _aggregate(tuple(bar for bar in parent_bars if bar is not None))
        m15_c2 = _m15_at(m5, decision_at - M15)
        if m15_c2 is None:
            raise ValueError("missing frozen last M15 source bar")
        direction = event["parent_direction"]
        if direction not in ("BULLISH", "BEARISH"):
            raise ValueError("frozen V2 direction invalid")
        invalidation = (
            m15_c2["low_relative"]
            if direction == "BULLISH" else m15_c2["high_relative"]
        )
        target_double = c1["low_relative"] + c1["high_relative"]
        outcome, when, observed_bars = observe_price_only_path(
            direction=direction,
            decision_at=decision_at,
            c3_open=c3_open,
            invalidation_relative=invalidation,
            target_double_relative=target_double,
            m5=m5,
        )
        observation = {
            "market": market.value,
            "source_policy_id": SOURCE_POLICY,
            "source_event_id": event_id,
            "source_decision_at_utc": decision_at.isoformat(),
            "H4_c3_utc": c3_open.isoformat(),
            "year_utc": str(c3_open.year),
            "direction": direction,
            "hypothesis_invalidation_relative": invalidation,
            "hypothesis_target_twice_relative": target_double,
            "price_path_outcome_only": outcome,
            "first_touch_m5_opened_at_utc": when,
            "m5_bars_observed_after_decision": observed_bars,
            "not_a_trade": True,
            "no_PnL": True,
            "no_sizing": True,
            "not_fresh_OOS": True,
        }
        observations.append(observation)
        outcome_counts[outcome] += 1
        yearly[str(c3_open.year)][outcome] += 1

    manifest = {
        "schema": SCHEMA,
        "source_policy_id": SOURCE_POLICY,
        "market": market.value,
        "original_m5_bars": len(bars),
        "frozen_source_h4_contexts": source_manifest["complete_h4_c1_c2_contexts"],
        "v2_candidates_original": expected_count,
        "price_path_events_reconciled": len(observations),
        "outcomes": dict(sorted(outcome_counts.items())),
        "yearly_outcomes": {
            year: dict(sorted(counts.items())) for year, counts in sorted(yearly.items())
        },
        "missing_fills_and_costs": True,
        "no_PnL": True,
        "no_sizing": True,
        "not_fresh_OOS": True,
        "GM1_PASS": False,
        "GM2_PASS": False,
        "GM3_PASS": False,
        "GM4_PASS": False,
        "GM5_ISSUED": False,
        "GLOBAL_CERTIFIED": False,
    }
    return manifest, tuple(observations)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("market", choices=("AUDUSD", "USDJPY"))
    ap.add_argument("atlas_root", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    market = CrtPureMarket(args.market)
    bars, source_provenance = load_atlas_vt08_m5(market, args.atlas_root)
    manifest, ledger = evaluate_frozen_v2_lifecycle(market, bars)
    manifest["original_source_provenance"] = source_provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "v2-price-lifecycle-summary.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "v2-price-lifecycle-ledger.jsonl").open("w") as f:
        for row in ledger:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in manifest.items() if k != "original_source_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
