"""Frozen experimental Classic re-entry replay for Turtle Soup R6."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from turtle_soup_r5_economics import POLICIES, Trade, bar_stop, metrics, policy_report, replay
from turtle_soup_r5_replay_core import (
    MARKETS,
    OOS_START,
    Bar,
    Evaluation,
    Fill,
    Market,
    State,
    process_bar,
    process_ticks,
    run_census,
)

R6_IDENTITY = "turtle-soup-candidate-r6-reentry-exp1"
BASE_POLICY = "C_TRAIL1_H3"


def serialize(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    if isinstance(value, Counter):
        return dict(value)
    raise TypeError(f"cannot serialize {type(value)!r}")


def digest(value: object) -> str:
    raw = json.dumps(
        value,
        default=serialize,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    return sha256(raw).hexdigest()


def locate_m15(path: tuple[Bar, ...], when: datetime) -> int | None:
    for index, bar in enumerate(path):
        if bar.opened_at <= when < bar.closed_at:
            return index
    return None


def locate_attempt1_stop(
    market: Market,
    result: Evaluation,
    source_index: int,
) -> tuple[int, int, tuple[Bar, ...]] | None:
    if result.fill is None or result.context is None:
        raise ValueError("R6 requires deterministic R5 fill")
    first = replay(market, result, source_index, BASE_POLICY)
    if first.exit_reason not in {"stop", "gap-stop"} or first.exit_at is None:
        return None
    if first.holding_bars == 0:
        path = result.context[0]
        if not isinstance(path, tuple):
            raise ValueError("invalid R5 path context")
        index = locate_m15(path, first.exit_at)
        if index is None:
            raise AssertionError("could not locate Day-1 stop M15")
        return 0, index, path
    if first.holding_bars != 1:
        return None
    day2_index = source_index + 1
    if day2_index >= len(market.d1):
        return None
    day2 = market.d1[day2_index]
    if day2.opened_at >= OOS_START:
        return None
    path = market.m15_session(day2)
    if path is None:
        return None
    for index, bar in enumerate(path):
        price, reason = bar_stop(result.fill.side, result.fill.stop, bar)
        if price is not None and reason is not None:
            return 1, index, path
    raise AssertionError("R5 Day-2 stop did not reproduce on M15")


def make_fill(
    original: Fill,
    session: Bar,
    resolution: str,
    fill_data: tuple[Decimal, Decimal, datetime, str],
) -> Fill:
    return Fill(
        original.side,
        fill_data[0],
        original.trigger,
        fill_data[1],
        fill_data[2],
        session.opened_at,
        resolution,
    )


def refine_m15(
    market: Market,
    session: Bar,
    path: tuple[Bar, ...],
    m15_index: int,
    original: Fill,
    state: State,
) -> tuple[str, State, Evaluation | None]:
    m15 = path[m15_index]
    subbars = market.m1_subbars(session.opened_at, m15)
    if subbars is None:
        return "reentry-ambiguous", state, None
    local = State(state.swept, state.extreme)
    for m1_index, m1 in enumerate(subbars):
        status, next_state, fill_data = process_bar(
            m1,
            original.side,
            original.trigger,
            original.trigger,
            local,
            market.tick_size,
        )
        if status == "continue":
            local = next_state
            continue
        if status == "fill" and fill_data is not None:
            fill = make_fill(original, session, "M1:R6", fill_data)
            context = (path, m15_index, m15, fill_data[3], subbars, m1_index, m1)
            return (
                "fill",
                next_state,
                Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context),
            )
        if status != "ambiguous":
            raise AssertionError(f"unexpected M1 status {status}")
        target = market.ticks.get((m1.opened_at, original.side))
        if target is None:
            return "reentry-ambiguous", local, None
        wave, record = target
        tick_status, tick_state, tick_fill = process_ticks(
            m1,
            record,
            original.side,
            original.trigger,
            original.trigger,
            local,
            market.tick_size,
        )
        if tick_status == "continue":
            local = tick_state
            continue
        if tick_status == "fill" and tick_fill is not None:
            fill = make_fill(original, session, f"TICK:R6:{wave}", tick_fill)
            context = (path, m15_index, m15, tick_fill[3], subbars, m1_index, m1, record)
            return (
                "fill",
                tick_state,
                Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context),
            )
        return f"reentry-tick-{tick_status}", local, None
    return "continue", local, None


def search_path(
    market: Market,
    session: Bar,
    path: tuple[Bar, ...],
    original: Fill,
    state: State,
    start_index: int,
) -> tuple[str, State, Evaluation | None]:
    current = State(state.swept, state.extreme)
    for m15_index, bar in enumerate(path[start_index:], start=start_index):
        status, next_state, fill_data = process_bar(
            bar,
            original.side,
            original.trigger,
            original.trigger,
            current,
            market.tick_size,
        )
        if status == "continue":
            current = next_state
            continue
        if status == "fill" and fill_data is not None:
            fill = make_fill(original, session, "M15:R6", fill_data)
            context = (path, m15_index, bar, fill_data[3])
            return (
                "fill",
                next_state,
                Evaluation(market.symbol, session.opened_at, original.side, "fill", fill, context),
            )
        if status == "ambiguous":
            refined_status, refined_state, evaluation = refine_m15(
                market, session, path, m15_index, original, current
            )
            if refined_status == "continue":
                current = refined_state
                continue
            return refined_status, refined_state, evaluation
        raise AssertionError(f"unexpected M15 status {status}")
    return "continue", current, None


def resolve_reentry(
    market: Market,
    result: Evaluation,
    source_index: int,
) -> tuple[str, Evaluation | None, int | None, int | None]:
    if result.fill is None:
        raise ValueError("R6 requires R5 source fill")
    located = locate_attempt1_stop(market, result, source_index)
    if located is None:
        return "not-eligible-no-day1-day2-stop", None, None, None
    day_offset, stop_m15_index, path = located
    session_index = source_index + day_offset
    session = market.d1[session_index]
    stop_bar = path[stop_m15_index]

    # Frozen conservative addendum: the M15 containing the stop is never reused
    # for re-entry.  Its adverse extreme is, however, part of the re-entry stop.
    extreme = stop_bar.low if result.fill.side == "long" else stop_bar.high
    state = State(True, extreme)
    status, state, evaluation = search_path(
        market,
        session,
        path,
        result.fill,
        state,
        stop_m15_index + 1,
    )
    if status == "fill":
        return status, evaluation, session_index, day_offset
    if status != "continue":
        return status, None, None, day_offset
    if day_offset == 1:
        return "expired", None, None, day_offset

    day2_index = source_index + 1
    if day2_index >= len(market.d1):
        return "reentry-data-unavailable", None, None, day_offset
    day2 = market.d1[day2_index]
    if day2.opened_at >= OOS_START:
        return "reentry-oos-embargo", None, None, day_offset
    day2_path = market.m15_session(day2)
    if day2_path is None:
        return "reentry-data-unavailable", None, None, day_offset
    status, _, evaluation = search_path(
        market,
        day2,
        day2_path,
        result.fill,
        state,
        0,
    )
    if status == "fill":
        return status, evaluation, day2_index, day_offset
    if status == "continue":
        return "expired", None, None, day_offset
    return status, None, None, day_offset


def build_report(root: Path, software_sha: str) -> tuple[dict[str, object], dict[str, list[Trade]]]:
    markets = {symbol: Market(root, symbol) for symbol in MARKETS}
    evaluations, fills = run_census(markets, True)
    if len(fills) != 290:
        raise AssertionError(f"R5 source fill census drifted: {len(fills)}")
    unresolved_base = Counter(
        item.status for item in evaluations if item.status.startswith("tick-")
    )
    if unresolved_base:
        raise AssertionError(f"R5 causal base drifted: {unresolved_base}")

    resolved_rows: list[tuple[Evaluation, Market, int, str, Evaluation | None, int | None]] = []
    census: Counter[str] = Counter()
    stop_days: Counter[str] = Counter()
    for evaluation, market, source_index in fills:
        status, reentry, reentry_source_index, stop_day = resolve_reentry(
            market, evaluation, source_index
        )
        census[status] += 1
        if stop_day is not None:
            stop_days[f"day{stop_day + 1}"] += 1
        resolved_rows.append(
            (evaluation, market, source_index, status, reentry, reentry_source_index)
        )

    policies: dict[str, object] = {}
    trades_by_policy: dict[str, list[Trade]] = {}
    for policy in POLICIES:
        first: list[Trade] = []
        second: list[Trade] = []
        for evaluation, market, source_index, _, reentry, reentry_source_index in resolved_rows:
            first.append(replay(market, evaluation, source_index, policy))
            if reentry is not None and reentry_source_index is not None:
                second.append(replay(market, reentry, reentry_source_index, policy))
        attempts = first + second
        trades_by_policy[policy] = attempts
        policy_data = policy_report(attempts)
        policy_data["attempt1"] = metrics(first)
        policy_data["attempt2"] = metrics(second)
        policy_data["reentry_fills"] = len(second)
        policies[policy] = policy_data

    passing = [
        policy
        for policy, data in policies.items()
        if isinstance(data, dict) and data.get("passes_advancement_gate") is True
    ]
    verdict = (
        "R6_DEVELOPMENT_GATE_PASS" if passing else "R6_REENTRY_EXPERIMENT_REJECTED"
    )
    report: dict[str, object] = {
        "schema": "qore.trader_lab.turtle_soup_candidate_r6.experimental_reentry.v1",
        "research_identity_root": "turtle-soup-candidate-r1",
        "research_round_identity": R6_IDENTITY,
        "canonical_trader_code": "CODE_UNASSIGNED",
        "source_adjudication": "R6_REENTRY_SOURCE_UNDERDETERMINED",
        "reentry_provenance": "QORE_EXPERIMENTAL_REENTRY",
        "same_stop_container_policy": "SKIP_TO_NEXT_M15_FAIL_CLOSED",
        "software_sha": software_sha,
        "fresh_oos_consumed": False,
        "fresh_oos_authorized": False,
        "fresh_oos_embargo_start": OOS_START,
        "r5_source_fills": len(fills),
        "reentry_resolution_census": census,
        "eligible_stop_day_census": stop_days,
        "policies": policies,
        "passing_policies": passing,
        "candidate_freeze": None,
        "final_verdict": verdict,
    }
    report["report_digest_sha256"] = digest(report)
    return report, trades_by_policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    args = parser.parse_args()
    report, trades = build_report(args.input_root, args.software_sha)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, default=serialize, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.trades.write_text(
        json.dumps(
            {policy: [asdict(trade) for trade in rows] for policy, rows in trades.items()},
            default=serialize,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "final_verdict": report["final_verdict"],
                "passing_policies": report["passing_policies"],
                "reentry_resolution_census": report["reentry_resolution_census"],
                "report_digest_sha256": report["report_digest_sha256"],
            },
            default=serialize,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
