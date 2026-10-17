"""V2 prereg: first causal M15 nested CRT anywhere in H4 C3, no same-parent rearm.

Only original M5 OHLC with preknown H4 C1/C2. Source-inspired QORE engineering
(not a Romeo-only source contract). NO sizing, PnL, fills, orders or gates PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_candidate_v1 import (
    _direction,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v1_full_h4_census import (
    H4,
    M5,
    _aggregate,
    _h4_floor,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

M15 = timedelta(minutes=15)
SCHEMA = "qore.vt08.crt_three_source_v2.full_utc_h4_development_only.v1"
POLICY_ID = "VT08_CRT_THREE_SOURCE_QORE_V2"


def _m15_at(
    m5: dict[datetime, ReplayBar], started: datetime
) -> dict[str, Any] | None:
    source = tuple(m5.get(started + i * M5) for i in range(3))
    if any(x is None for x in source):
        return None
    return _aggregate(tuple(x for x in source if x is not None))


def _earliest_nested_confirmation(
    *,
    c3_started: datetime,
    m5: dict[datetime, ReplayBar],
    parent_direction: str,
    target_twice: int,
) -> tuple[str, str, str | None, int, int]:
    """Only consume closed bars available at each next M15 clock.

    Return state, why, decision clock, checked pairs and conflicts. A missing
    prefix makes target-consumption uncertain; NEVER skip gaps to find a win.
    """
    observed: list[dict[str, Any]] = []
    prior_target_hit = False
    conflict_count = 0
    pair_count = 0
    for index in range(16):
        started = c3_started + index * M15
        bar = _m15_at(m5, started)
        if bar is None:
            return ("WAIT", "UNCERTAIN_C3_PRICE_PATH_GAP", None, pair_count, conflict_count)
        observed.append(bar)
        if parent_direction == "BULLISH":
            touched = 2 * bar["high_relative"] >= target_twice
        else:
            touched = 2 * bar["low_relative"] <= target_twice
        # A target touched at ANY time on or before the latest closed bar is
        # already consumed, even if price later returns to the entry side.
        prior_target_hit = prior_target_hit or touched
        if index < 1:
            continue
        pair_count += 1
        direction = _direction(observed[index - 1], observed[index])
        if direction is not None and direction != parent_direction:
            conflict_count += 1
            continue
        if direction != parent_direction:
            continue
        close = bar["close_relative"]
        if prior_target_hit or (
            (parent_direction == "BULLISH" and 2 * close >= target_twice)
            or (parent_direction == "BEARISH" and 2 * close <= target_twice)
        ):
            return (
                "ABSTAIN", "H4_MIDPOINT_PREVIOUSLY_TOUCHED_OR_CONSUMED",
                None, pair_count, conflict_count,
            )
        return (
            "CONCEPTUAL_CANDIDATE",
            "V2_EARLIEST_NESTED_M15_PURGE_RECLAIM_WITH_TARGET_AHEAD",
            (started + M15).isoformat(), pair_count, conflict_count,
        )
    return ("WAIT", "NO_VALID_CAUSAL_M15_MICRO_SOURCE", None, pair_count, conflict_count)


def full_utc_h4_v2_census(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if market not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("BTCUSD frozen or non-core market")
    if not bars:
        raise ValueError("missing original M5 data")
    m5: dict[datetime, ReplayBar] = {}
    starts: set[datetime] = set()
    for bar in bars:
        if bar.opened_at.tzinfo is None:
            raise ValueError("all M5 clocks must have UTC provenance")
        t = bar.opened_at.astimezone(UTC)
        if t in m5:
            raise ValueError("duplicate M5 original timestamp")
        m5[t] = bar
        starts.add(_h4_floor(t))
    h4: dict[datetime, dict[str, Any]] = {}
    for started in sorted(starts):
        samples = tuple(m5.get(started + i * M5) for i in range(48))
        if any(x is None for x in samples):
            continue
        h4[started] = _aggregate(tuple(x for x in samples if x is not None))

    outputs: list[dict[str, Any]] = []
    states = Counter[str]()
    reasons = Counter[str]()
    per_year: dict[str, Counter[str]] = defaultdict(Counter)
    total_pairs = 0
    total_conflicts = 0
    parent_candidates = 0
    for c2_started in sorted(h4):
        c1_started = c2_started - H4
        if c1_started not in h4:
            continue
        c3_started = c2_started + H4
        c1, c2 = h4[c1_started], h4[c2_started]
        direction = _direction(c1, c2)
        year = str(c3_started.year)
        status, reason, decision_at, pairs, conflicts = (
            "ABSTAIN", "H4_NO_ONE_SIDED_PURGE_RECLAIM", None, 0, 0
        )
        if direction is not None:
            parent_candidates += 1
            status, reason, decision_at, pairs, conflicts = _earliest_nested_confirmation(
                c3_started=c3_started,
                m5=m5,
                parent_direction=direction,
                target_twice=c1["high_relative"] + c1["low_relative"],
            )
        total_pairs += pairs
        total_conflicts += conflicts
        if status == "CONCEPTUAL_CANDIDATE" and decision_at is None:
            raise ValueError("a conceptual candidate must have a causal M15 time")
        record = {
            "policy_id": POLICY_ID,
            "market": market.value,
            "c3_H4_opened_at_utc": c3_started.isoformat(),
            "year_utc": year,
            "parent_direction": direction,
            "first_conceptual_decision_clock_utc": decision_at,
            "m15_admissible_pairs_examined_until_terminal": pairs,
            "opposing_micro_crt_evidence_seen": conflicts,
            "state": status,
            "why": reason,
            "source_event_id": hashlib.sha256(
                f"{market.value}|{c3_started.isoformat()}|V2".encode()
            ).hexdigest()[:20],
            "is_trade": False,
            "grants_volume_or_broker_authority": False,
            "not_fresh_oos": True,
        }
        outputs.append(record)
        states[status] += 1
        reasons[reason] += 1
        per_year[year][status] += 1
    if not outputs:
        raise ValueError("no complete H4 parent pairs")
    if len({x["c3_H4_opened_at_utc"] for x in outputs}) != len(outputs):
        raise ValueError("one parent H4 cannot generate two first admissions")
    summary = {
        "schema": SCHEMA,
        "policy_id": POLICY_ID,
        "market": market.value,
        "original_atlas_m5": len(bars),
        "complete_utc_h4": len(h4),
        "complete_h4_c1_c2_contexts": len(outputs),
        "parent_h4_eligible": parent_candidates,
        "m15_pairs_replayed_before_terminal": total_pairs,
        "opposing_micro_evidence_before_terminal": total_conflicts,
        "states": dict(sorted(states.items())),
        "terminal_reasons": dict(sorted(reasons.items())),
        "by_year_utc": {
            year: dict(sorted(v.items())) for year, v in sorted(per_year.items())
        },
        "one_conceptual_first_admission_per_parent": True,
        "sampled_using_future_C3_outcome": False,
        "replay_dev_only_not_fresh_OOS": True,
        "no_PnL": True,
        "no_sizing": True,
        "zero_orders": True,
        "methodology_certified": False,
        "global_certified": False,
    }
    return summary, tuple(outputs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=("AUDUSD", "USDJPY"))
    parser.add_argument("atlas_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.atlas_root)
    summary, ledger = full_utc_h4_v2_census(market, bars)
    summary["original_source_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "three-source-v2-h4-census-summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "three-source-v2-h4-census-ledger.jsonl").open("w") as f:
        for item in ledger:
            f.write(json.dumps(item, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in summary.items() if k != "original_source_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
