"""Source-inspired QORE V3: a third closed M15 candle confirms micro CRT.

The rule's complete semantics are QORE engineering, NOT any author's verbatim
model. The V3 protocol was preregistered under docs/research before replay.
No trades, PnL, sizing, broker connections, or economic certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
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
from qore.infrastructure.trader_lab.vt08_crt_three_source_v2_full_h4_census import (
    M15,
    _m15_at,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

POLICY_ID = "VT08_CRT_THREE_SOURCE_QORE_V3_CSD_THIRD_CANDLE"
SCHEMA = "qore.vt08.crt_three_source.v3.third_candle_development.v1"


def _confirmed_micro(
    reference: dict[str, Any],
    source: dict[str, Any],
    confirmation: dict[str, Any],
    parent_direction: str,
) -> bool:
    if _direction(reference, source) != parent_direction:
        return False
    source_open = source["open_relative"]
    source_close = source["close_relative"]
    confirmed_close = confirmation["close_relative"]
    if parent_direction == "BULLISH":
        return bool(source_close < source_open and confirmed_close > source_open)
    if parent_direction == "BEARISH":
        return bool(source_close > source_open and confirmed_close < source_open)
    raise ValueError("unexpected parent direction")


def _first_confirmed_c3(
    c3_start: datetime,
    m5: dict[datetime, ReplayBar],
    parent_direction: str,
    target_twice: int,
) -> tuple[str, str, str | None, int, int, str | None]:
    """Deterministic oldest eligible M15 triple, with no future after decision."""
    observed: list[dict[str, Any]] = []
    pairs = 0
    opposed = 0
    consumed = False
    for index in range(16):
        bar_started = c3_start + index * M15
        bar = _m15_at(m5, bar_started)
        if bar is None:
            return (
                "WAIT_DATA_GAP", "M15_PREFIX_GAP_FAIL_CLOSED", None, pairs, opposed, None
            )
        observed.append(bar)
        consumed = consumed or (
            2 * bar["high_relative"] >= target_twice
            if parent_direction == "BULLISH"
            else 2 * bar["low_relative"] <= target_twice
        )
        if consumed:
            return (
                "ABSTAIN_TARGET_CONSUMED", "H4_C1_MIDPOINT_ALREADY_WICK_TOUCHED",
                None, pairs, opposed, None,
            )
        if index < 2:
            continue
        pairs += 1
        ref, source, confirmation = observed[index - 2 : index + 1]
        micro_direction = _direction(ref, source)
        if micro_direction is not None and micro_direction != parent_direction:
            opposed += 1
            continue
        if not _confirmed_micro(ref, source, confirmation, parent_direction):
            continue
        # An explicit structural hypothesis: source sweep wick cannot have
        # been invalidated by the confirmation before the decision even exists.
        if parent_direction == "BULLISH":
            invalid = confirmation["low_relative"] <= source["low_relative"]
            no_room = 2 * confirmation["close_relative"] >= target_twice
            invalidation = source["low_relative"]
        else:
            invalid = confirmation["high_relative"] >= source["high_relative"]
            no_room = 2 * confirmation["close_relative"] <= target_twice
            invalidation = source["high_relative"]
        if invalid or no_room:
            return (
                "ABSTAIN_THESIS_INVALIDATED",
                "SOURCE_WICK_RETOUCHED_OR_NO_DESTINATION_AHEAD", None,
                pairs, opposed, None,
            )
        close_clock = bar_started + M15
        if close_clock == c3_start + H4:
            return (
                "EXPIRED_AT_H4_C3_CLOSE", "THIRD_CANDLE_CONFIRMED_AT_H4_CLOSE",
                None, pairs, opposed, None,
            )
        if close_clock > c3_start + H4:
            raise ValueError("M15 decision clock outside H4 C3")
        return (
            "CONCEPTUAL_CANDIDATE_V3", "H4_PURGE_THEN_M15_SOURCE_AND_BODY_CONFIRM",
            close_clock.isoformat(), pairs, opposed, str(invalidation),
        )
    return (
        "WAIT_M15", "NO_CONFIRMED_THIRD_M15_CANDLE_DURING_C3",
        None, pairs, opposed, None,
    )


def full_utc_h4_v3_census(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Complete causal H4 census. Every valid parent is represented once."""
    if market not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("BTCUSD frozen")
    if not bars:
        raise ValueError("missing original M5 Atlas source")
    m5: dict[datetime, ReplayBar] = {}
    starts: set[datetime] = set()
    for bar in bars:
        if bar.opened_at.tzinfo is None:
            raise ValueError("UTC provenance missing from M5 source")
        t = bar.opened_at.astimezone(UTC)
        if t in m5:
            raise ValueError("duplicate original M5 time")
        m5[t] = bar
        starts.add(_h4_floor(t))
    h4: dict[datetime, dict[str, Any]] = {}
    for opened in sorted(starts):
        samples = tuple(m5.get(opened + i * M5) for i in range(48))
        if any(s is None for s in samples):
            continue
        h4[opened] = _aggregate(tuple(s for s in samples if s is not None))
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    by_year: dict[str, Counter[str]] = defaultdict(Counter)
    parent_purges = 0
    total_checked = 0
    opposed_total = 0
    for c2_start in sorted(h4):
        c1_start = c2_start - H4
        if c1_start not in h4:
            continue
        c3_start = c2_start + H4
        c1, c2 = h4[c1_start], h4[c2_start]
        parent_direction = _direction(c1, c2)
        status, why, decision_at, examined, opposing, invalidation = (
            "ABSTAIN_H4", "H4_C2_DID_NOT_ONE_SIDE_SWEEP_RECLAIM",
            None, 0, 0, None,
        )
        if parent_direction is not None:
            parent_purges += 1
            status, why, decision_at, examined, opposing, invalidation = (
                _first_confirmed_c3(
                    c3_start,
                    m5,
                    parent_direction,
                    c1["high_relative"] + c1["low_relative"],
                )
            )
        if (status == "CONCEPTUAL_CANDIDATE_V3") != (decision_at is not None):
            raise ValueError("invalid conceptual V3 decision-clock invariant")
        total_checked += examined
        opposed_total += opposing
        identity = f"{market.value}|{c3_start.isoformat()}|V3_THIRD_CANDLE"
        year = str(c3_start.year)
        row = {
            "schema": SCHEMA,
            "policy_id": POLICY_ID,
            "market": market.value,
            "source_event_id": hashlib.sha256(identity.encode()).hexdigest()[:20],
            "c3_H4_opened_at_utc": c3_start.isoformat(),
            "year_utc": year,
            "parent_direction": parent_direction,
            "decision_clock_utc": decision_at,
            "m15_confirmed_triples_checked": examined,
            "opposing_micro_patterns": opposing,
            "structural_invalidation_price_if_candidate": invalidation,
            "conceptual_state": status,
            "why": why,
            "source_authority_adjudicated": False,
            "independent_method_review_complete": False,
            "not_a_trade": True,
            "no_sizing_or_capital_authority": True,
            "prior_dev_sample_not_fresh_holdout": True,
        }
        rows.append(row)
        counts[status] += 1
        reasons[why] += 1
        by_year[year][status] += 1
    if not rows or len({r["source_event_id"] for r in rows}) != len(rows):
        raise ValueError("empty or duplicate H4 contexts")
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "policy_id": POLICY_ID,
        "market": market.value,
        "original_m5_rows": len(bars),
        "complete_h4": len(h4),
        "complete_h4_c1_c2_contexts": len(rows),
        "h4_purge_reclaim_contexts": parent_purges,
        "m15_triples_causally_examined": total_checked,
        "opposing_micro_patterns_before_terminal": opposed_total,
        "state_counts": dict(sorted(counts.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "by_year_utc": {k: dict(sorted(v.items())) for k, v in sorted(by_year.items())},
        "conceptual_only_no_pnl": True,
        "sizing_used": False,
        "not_fresh_holdout": True,
        "any_source_rule_GM1_PASS": False,
        "cognitive_GM3_PASS": False,
        "GLOBAL_CERTIFIED": False,
    }
    return manifest, tuple(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=("AUDUSD", "USDJPY"))
    parser.add_argument("atlas_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    data, provenance = load_atlas_vt08_m5(market, args.atlas_root)
    manifest, ledger = full_utc_h4_v3_census(market, data)
    manifest["original_atlas_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "three-source-v3-third-candle-summary.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "three-source-v3-third-candle-ledger.jsonl").open("w") as fh:
        for row in ledger:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in manifest.items() if k != "original_atlas_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
