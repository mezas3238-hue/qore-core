"""Consumed-only VT-31 R8 post-quality fill/censor attrition forensics.

Uses the already-rejected R8 rule-set and already-consumed R5/R6/R8 evidence.
The purpose is diagnostic only: preserve exact simulator semantics while
classifying why a quality-eligible setup does or does not become a resolved
trade. No fresh evidence is opened and no candidate is approved here.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_r5_candidate as r5
import vt31_r8_sparse_reference_forensics as sparse

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

MARKETS = ("NAS100", "SP500", "US30")
POLICIES = ("strict60", "gap03", "gap05", "gap10")


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _diagnose_simulation(
    day_bars: tuple[object, ...], signal_index: int, setup: object
) -> tuple[dict[str, object] | None, str]:
    """Mirror frozen R8/R5 simulation and expose its fail-closed terminal reason."""
    side = getattr(setup, "side").value
    entry = cast(Decimal, getattr(setup, "entry"))
    initial_stop = cast(Decimal, getattr(setup, "stop"))
    risk = abs(entry - initial_stop)
    if risk <= 0:
        return None, "invalid-risk"
    target = (
        entry + r5.TARGET_R * risk
        if side == "long"
        else entry - r5.TARGET_R * risk
    )

    fill_index: int | None = None
    for index in range(signal_index + 1, len(day_bars)):
        bar = day_bars[index]
        if _wall(getattr(bar, "opened_at")) >= (11, 0, 0):
            break
        if index > signal_index + 1 and getattr(bar, "opened_at") != getattr(
            day_bars[index - 1], "closed_at"
        ):
            return None, "pending-data-gap"
        if r5._touch(bar, entry):
            fill_index = index
            break
    if fill_index is None:
        return None, "pending-no-fill-before-11"

    first = day_bars[fill_index]
    first_stop = (
        _d(cast(float, getattr(first, "low"))) <= initial_stop
        if side == "long"
        else _d(cast(float, getattr(first, "high"))) >= initial_stop
    )
    first_target = (
        _d(cast(float, getattr(first, "high"))) >= target
        if side == "long"
        else _d(cast(float, getattr(first, "low"))) <= target
    )
    if first_stop or first_target:
        return None, "fill-bar-path-ambiguous"

    current_stop = initial_stop
    previous = first
    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        local = getattr(bar, "opened_at").astimezone(r5.NY)
        if local.hour * 60 + local.minute >= 16 * 60:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return None, "post-fill-data-gap"
        previous = bar
        hit_stop = (
            _d(cast(float, getattr(bar, "low"))) <= current_stop
            if side == "long"
            else _d(cast(float, getattr(bar, "high"))) >= current_stop
        )
        hit_target = (
            _d(cast(float, getattr(bar, "high"))) >= target
            if side == "long"
            else _d(cast(float, getattr(bar, "low"))) <= target
        )
        if hit_stop and hit_target:
            return None, "later-same-bar-stop-target-ambiguous"
        if hit_stop:
            trade = r5._simulate(day_bars, signal_index, setup)
            return trade, "resolved-protected-stop"
        if hit_target:
            trade = r5._simulate(day_bars, signal_index, setup)
            return trade, "resolved-fixed-2r-target"
        current_stop = r5._new_protected_stop(
            day_bars,
            index,
            side,
            current_stop,
            _d(cast(float, getattr(bar, "close"))),
        )

    trade = r5._simulate(day_bars, signal_index, setup)
    if trade is None:
        return None, "lifecycle-unresolved-censored"
    return trade, "resolved-16-00-lifecycle"


def _run_market(path: Path, market: str) -> dict[str, object]:
    series, _, _, _, _, provider = load_market_evidence(path)
    by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)

    counters = {policy: Counter() for policy in POLICIES}
    side_reasons: dict[str, dict[str, Counter[str]]] = {
        policy: {"long": Counter(), "short": Counter()} for policy in POLICIES
    }
    resolved: dict[str, list[dict[str, object]]] = {
        policy: [] for policy in POLICIES
    }

    for local_day in sorted(by_day):
        day_bars = tuple(by_day[local_day])
        reference = sparse._reference_bars(day_bars)
        indexed_session = tuple(
            (index, bar)
            for index, bar in enumerate(day_bars)
            if (10, 0, 0) <= _wall(getattr(bar, "opened_at")) < (11, 0, 0)
        )
        if len(indexed_session) != 60 or not reference:
            continue

        qualifying = [
            policy for policy in POLICIES if sparse._policy_accepts(reference, policy)
        ]
        if not qualifying:
            continue
        for policy in qualifying:
            counters[policy]["reference-admitted"] += 1

        ref_high = max(_d(cast(float, getattr(item, "high"))) for item in reference)
        ref_low = min(_d(cast(float, getattr(item, "low"))) for item in reference)
        ref_width = ref_high - ref_low
        if ref_width <= 0:
            for policy in qualifying:
                counters[policy]["invalid-reference"] += 1
            continue

        prefix = list(reference)
        selected: object | None = None
        selected_index: int | None = None
        first_base = False
        quality_pass = False
        for global_index, bar in indexed_session:
            prefix.append(bar)
            candidate, _ = sparse._evaluate_sparse(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
                bars=tuple(prefix),
                variant=r5.BASE_VARIANT,
            )
            if candidate is None:
                continue
            first_base = True
            if not sparse._quality_sparse(tuple(prefix), candidate, ref_width):
                break
            quality_pass = True
            selected = candidate
            selected_index = global_index
            break

        for policy in qualifying:
            if first_base:
                counters[policy]["first-base-candidate"] += 1
            if quality_pass:
                counters[policy]["quality-pass"] += 1

        if selected is None or selected_index is None:
            continue

        trade, reason = _diagnose_simulation(day_bars, selected_index, selected)
        frozen = r5._simulate(day_bars, selected_index, selected)
        if (trade is None) != (frozen is None):
            raise AssertionError("diagnostic simulator parity failure")
        if trade is not None and frozen is not None:
            if trade["r_multiple"] != frozen["r_multiple"] or trade["exit_reason"] != frozen["exit_reason"]:
                raise AssertionError("diagnostic simulator resolved-trade mismatch")
            trade = dict(trade)
            trade["market"] = market

        side = getattr(selected, "side").value
        for policy in qualifying:
            counters[policy][reason] += 1
            side_reasons[policy][side][reason] += 1
            if trade is not None:
                resolved[policy].append(dict(trade))

    return {
        "market": market,
        "provider": provider,
        "bar_count": len(series),
        "first_opened_at": series[0].opened_at.astimezone(UTC).isoformat(),
        "last_closed_at": series[-1].closed_at.astimezone(UTC).isoformat(),
        "counters": {
            policy: dict(sorted(counter.items()))
            for policy, counter in counters.items()
        },
        "side_reasons": {
            policy: {
                side: dict(sorted(counter.items()))
                for side, counter in sides.items()
            }
            for policy, sides in side_reasons.items()
        },
        "resolved_trades": resolved,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 9:
        print(
            "usage: script R5_NAS R5_SP R5_US R6_NAS R6_SP R6_US "
            "R8_NAS R8_SP R8_US"
        )
        return 2

    partitions = {
        "r5": dict(zip(MARKETS, map(Path, args[0:3]), strict=True)),
        "r6": dict(zip(MARKETS, map(Path, args[3:6]), strict=True)),
        "r8_fresh": dict(zip(MARKETS, map(Path, args[6:9]), strict=True)),
    }
    report: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_r8_fill_attrition_forensics.v1",
        "research_only": True,
        "opens_new_evidence": False,
        "candidate_status": "R8_REJECTED_FRESH_CONSUMED",
        "policies": list(POLICIES),
        "partitions": {},
    }

    for partition, paths in partitions.items():
        block: dict[str, object] = {}
        for market, path in paths.items():
            block[market] = _run_market(path, market)
        cast(dict[str, object], report["partitions"])[partition] = block

    Path("vt31-r8-fill-attrition-forensics.json").write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    )

    compact: dict[str, object] = {}
    for partition, markets in cast(
        dict[str, dict[str, dict[str, object]]], report["partitions"]
    ).items():
        pblock: dict[str, object] = {}
        for policy in POLICIES:
            aggregate = Counter()
            per_market: dict[str, object] = {}
            for market in MARKETS:
                counters = cast(
                    dict[str, dict[str, int]], markets[market]["counters"]
                )[policy]
                aggregate.update(counters)
                per_market[market] = counters
            pblock[policy] = {
                "aggregate": dict(sorted(aggregate.items())),
                "markets": per_market,
            }
        compact[partition] = pblock

    Path("vt31-r8-fill-attrition-summary.json").write_text(
        json.dumps(compact, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(compact, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
